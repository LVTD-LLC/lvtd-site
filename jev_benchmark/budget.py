"""Conservative credit reservations, not fictional billed costs."""

from decimal import Decimal

import requests
from django.conf import settings

from .clients import ProviderError
from .models import BudgetState


def get_data(path, key):
    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/" + path,
            headers={"Authorization": "Bearer " + key},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["data"]
    except (requests.RequestException, ValueError, KeyError):
        raise ProviderError(
            "OpenRouter budget preflight unavailable; generation paused", kind="budget"
        ) from None


class CreditBudget:
    def __init__(self):
        key = settings.OPENROUTER_JEVBENCHMARK_AI_API_KEY
        account = get_data("credits", key)
        info = get_data("key", key)
        self.usage = Decimal(str(info["usage"]))
        remaining = Decimal(str(account["total_credits"])) - Decimal(
            str(account["total_usage"])
        )
        if info.get("limit_remaining") is not None:
            remaining = min(remaining, Decimal(str(info["limit_remaining"])))
        self.limit = Decimal(str(settings.JEV_SPEND_ALERT_USD))
        self.spent = Decimal(0)
        self.threshold_blocked = False
        self.available = max(Decimal(0), min(remaining, self.limit - self.usage))
        self.prices = {row["id"]: row["pricing"] for row in get_data("models", key)}
        BudgetState.objects.update_or_create(
            pk=1,
            defaults={
                "openrouter_usage": self.usage,
                "available_credit": remaining,
                "alert": (
                    f"SPEND ALERT: OpenRouter benchmark spend ${self.usage:.2f}: "
                    "generation paused near $20."
                )
                if self.usage >= self.limit
                else "",
            },
        )

    def estimate(self, model, question, tokens):
        prices = self.prices.get(model.openrouter_id) or self.prices.get(
            model.openrouter_id.removesuffix(":nitro")
        )
        if prices is None:
            return None
        try:
            # UTF-8 bytes + envelope allowance is deliberately conservative.
            estimate = (
                Decimal(str(prices["prompt"])) * (len(question.prompt.encode()) + 1024)
                + Decimal(str(prices["completion"])) * tokens
                + Decimal(str(prices.get("request", 0)))
            ) * Decimal("1.25")
            return estimate if estimate.is_finite() and estimate >= 0 else None
        except (ValueError, ArithmeticError):
            return None

    def fits(self, estimate, reserved):
        if (
            estimate is not None
            and estimate + reserved > self.limit - self.usage - self.spent
        ):
            self.threshold_blocked = True
        return estimate is not None and estimate + reserved <= self.available

    def settle(self, actual, estimate):
        # Unknown billed cost retains the reservation rather than assuming zero.
        charged = actual if actual is not None else estimate
        self.spent += charged
        self.available = max(Decimal(0), self.available - charged)
