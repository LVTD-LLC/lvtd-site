"""Provider-reported USD only. Unknown is never treated as free."""

from decimal import Decimal, InvalidOperation


def reported_cost(response):
    try:
        value = response["usage"]["cost"]
        if isinstance(value, bool) or value is None:
            return None
        cost = Decimal(str(value))
        return cost if cost.is_finite() and cost >= 0 else None
    except (KeyError, TypeError, InvalidOperation, ValueError):
        return None


def cost_summary(answers):
    answers = list(answers)
    known = [c for a in answers if (c := reported_cost(a.response)) is not None]
    return {
        "cost_usd": sum(known, Decimal(0)) if known else None,
        "cost_known": len(known),
        "cost_count": len(answers),
    }
