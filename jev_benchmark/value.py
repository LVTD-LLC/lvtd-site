"""Versioned, explicit preference/cost tradeoff; never an accuracy estimate."""

import math
from decimal import Decimal

VALUE_METHOD = {
    "version": "value-v1",
    "quality_weight": 0.7,
    "affordability_weight": 0.3,
    "reference_elo": 1500,
    "elo_scale": 400,
    "reference_cost_usd": "0.01",
    "formula": "100 * (0.7 / (1 + 10**((1500-Elo)/400)) + 0.3 / (1 + cost_usd/0.01))",
    "scope": (
        "Complete round robins with known successful-answer costs only. "
        "Overall cost is the question-weighted mean cost per answer."
    ),
    "caveat": (
        "An experimental preference tradeoff, not accuracy, ROI, or a "
        "universal value measure. Free-tier prices may be temporary. "
        "Excludes retries and judge charges."
    ),
}


def value_score(rating, cost):
    if rating is None or cost is None:
        return None
    quality = 1 / (1 + 10 ** ((1500 - rating) / 400))
    affordability = 1 / (1 + float(cost) / 0.01)
    return 100 * (0.7 * quality + 0.3 * affordability)


def decorate(rows):
    for row in rows:
        cost = row.get("mean_cost_usd", row["cost_usd"])
        row["value_score"] = (
            value_score(row["rating"], cost) if row["complete"] else None
        )
        row["display_cost_usd"] = cost
    for field in ("rating", "value_score"):
        values = [r[field] for r in rows if r[field] is not None]
        lo, hi = (min(values), max(values)) if values else (0, 0)
        for row in rows:
            value = row[field]
            row[field + "_heat"] = (
                round(8 + 22 * (value - lo) / (hi - lo), 1)
                if value is not None and hi > lo
                else 0
            )
    return rows


def scatter(rows):
    eligible = [r for r in rows if r["value_score"] is not None]
    if not eligible:
        return {"points": [], "ticks": []}
    max_cost = max(float(r["display_cost_usd"]) for r in eligible)
    log_max = math.log10(1 + max_cost / 0.001) or 1
    low = math.floor(min(r["rating"] for r in eligible) / 100) * 100 - 50
    high = math.ceil(max(r["rating"] for r in eligible) / 100) * 100 + 50
    points = []
    for row in eligible:
        cost = row["display_cost_usd"]
        frontier = not any(
            other["rating"] >= row["rating"]
            and other["display_cost_usd"] <= cost
            and (other["rating"] > row["rating"] or other["display_cost_usd"] < cost)
            for other in eligible
        )
        points.append(
            {
                "name": row["model"].name,
                "x": round(65 + 680 * math.log10(1 + float(cost) / 0.001) / log_max, 2),
                "y": round(315 - 260 * (row["rating"] - low) / (high - low), 2),
                "rating": row["rating"],
                "cost": cost,
                "frontier": frontier,
            }
        )
    costs = [Decimal(0), Decimal(".001"), Decimal(".01"), Decimal(".1"), Decimal("1")]
    return {
        "points": points,
        "ticks": [
            {
                "x": round(65 + 680 * math.log10(1 + float(c) / 0.001) / log_max, 2),
                "label": str(c),
            }
            for c in costs
            if c <= max_cost
        ],
        "low": low,
        "high": high,
    }
