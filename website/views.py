from __future__ import annotations

import json

import requests
import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from website.models import StripeWebhookEvent


class HomePageView(TemplateView):
    template_name = "website/home.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["mvp_deposit_checkout_url"] = settings.MVP_DEPOSIT_CHECKOUT_URL
        context["mvp_deposit_amount"] = settings.MVP_DEPOSIT_AMOUNT
        context["mvp_final_price"] = settings.MVP_FINAL_PRICE
        return context


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "invalid_payload"}, status=400)

        event_id = payload.get("id")
        if not event_id:
            return JsonResponse({"error": "missing_event_id"}, status=400)

        if StripeWebhookEvent.objects.filter(event_id=event_id).exists():
            return JsonResponse({"status": "already_processed"})

        if not settings.STRIPE_API_KEY:
            return JsonResponse({"error": "stripe_not_configured"}, status=500)

        stripe.api_key = settings.STRIPE_API_KEY
        stripe_account = settings.STRIPE_CONTEXT_ACCOUNT or None

        try:
            event = stripe.Event.retrieve(event_id, stripe_account=stripe_account)
        except Exception:
            return JsonResponse({"error": "stripe_event_fetch_failed"}, status=400)

        if event.type != "checkout.session.completed":
            StripeWebhookEvent.objects.create(event_id=event_id)
            return JsonResponse({"status": "ignored"})

        session = event.data.get("object", {})
        if not self._is_mvp_deposit_session(session):
            StripeWebhookEvent.objects.create(event_id=event_id)
            return JsonResponse({"status": "ignored"})

        customer_email = (session.get("customer_details") or {}).get(
            "email"
        ) or session.get("customer_email")
        if not customer_email:
            return JsonResponse({"error": "missing_customer_email"}, status=400)

        if not self._send_mailgun_followup(customer_email):
            return JsonResponse({"error": "email_failed"}, status=502)

        StripeWebhookEvent.objects.create(event_id=event_id)
        return JsonResponse({"status": "sent"})

    @staticmethod
    def _is_mvp_deposit_session(session: dict) -> bool:
        payment_link_id = settings.STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID
        if payment_link_id:
            return session.get("payment_link") == payment_link_id

        amount_total = session.get("amount_total")
        currency = (session.get("currency") or "").lower()
        return (
            amount_total == settings.STRIPE_MVP_DEPOSIT_FALLBACK_AMOUNT
            and currency == "usd"
        )

    @staticmethod
    def _send_mailgun_followup(customer_email: str) -> bool:
        if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
            return False
        if not settings.MAILGUN_FROM_EMAIL:
            return False

        subject = "Thanks for choosing the MVP done-for-you service"
        body = (
            "Thanks for choosing the MVP done-for-you service! "
            "Reply with your project details, goals, and any timelines. "
            f"The final service price is {settings.MVP_FINAL_PRICE}."
        )

        response = requests.post(
            f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
            auth=("api", settings.MAILGUN_API_KEY),
            data={
                "from": settings.MAILGUN_FROM_EMAIL,
                "to": [customer_email],
                "subject": subject,
                "text": body,
                "h:Reply-To": settings.MAILGUN_REPLY_TO_EMAIL
                or settings.MAILGUN_FROM_EMAIL,
            },
            timeout=10,
        )

        return response.status_code < 300
