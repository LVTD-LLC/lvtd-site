from __future__ import annotations

import json
from xml.etree import ElementTree

import requests
import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView, View

from website.models import BlogPost, StripeWebhookEvent


def _absolute_url(path: str) -> str:
    return f"{settings.SITE_URL}{path}"


def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /services/hosted-openclaw/checkout/",
        f"Sitemap: {_absolute_url(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def sitemap_xml(request: HttpRequest) -> HttpResponse:
    urlset = ElementTree.Element(
        "urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    )

    static_urls = [
        (reverse("home"), settings.SITE_LASTMOD, "weekly", "1.0"),
        (reverse("blog-list"), settings.SITE_LASTMOD, "weekly", "0.7"),
        (
            reverse("hosted-openclaw-learn-more"),
            settings.SITE_LASTMOD,
            "monthly",
            "0.8",
        ),
        (reverse("terms-of-service"), settings.SITE_LASTMOD, "yearly", "0.3"),
        (reverse("privacy-policy"), settings.SITE_LASTMOD, "yearly", "0.3"),
    ]
    for path, lastmod, changefreq, priority in static_urls:
        url = ElementTree.SubElement(urlset, "url")
        ElementTree.SubElement(url, "loc").text = _absolute_url(path)
        ElementTree.SubElement(url, "lastmod").text = lastmod
        ElementTree.SubElement(url, "changefreq").text = changefreq
        ElementTree.SubElement(url, "priority").text = priority

    for post in BlogPost.objects.filter(is_published=True):
        url = ElementTree.SubElement(urlset, "url")
        ElementTree.SubElement(url, "loc").text = _absolute_url(
            reverse("blog-detail", kwargs={"slug": post.slug})
        )
        ElementTree.SubElement(url, "lastmod").text = post.updated_at.date().isoformat()
        ElementTree.SubElement(url, "changefreq").text = "monthly"
        ElementTree.SubElement(url, "priority").text = "0.6"

    xml_bytes = ElementTree.tostring(urlset, encoding="utf-8", xml_declaration=True)
    return HttpResponse(xml_bytes, content_type="application/xml")


class HomePageView(TemplateView):
    template_name = "website/home.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["mvp_deposit_checkout_url"] = settings.MVP_DEPOSIT_CHECKOUT_URL
        context["mvp_deposit_amount"] = settings.MVP_DEPOSIT_AMOUNT
        context["mvp_final_price"] = settings.MVP_FINAL_PRICE
        context["hosted_openclaw_deposit_amount"] = (
            settings.HOSTED_OPENCLAW_DEPOSIT_AMOUNT
        )
        context["latest_blog_posts"] = BlogPost.objects.filter(is_published=True)[:3]
        return context


class BlogListView(ListView):
    template_name = "website/blog_list.html"
    context_object_name = "posts"

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)


class BlogDetailView(DetailView):
    template_name = "website/blog_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)


class HostedOpenClawLearnMoreView(TemplateView):
    template_name = "website/hosted_openclaw.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["hosted_openclaw_deposit_amount"] = (
            settings.HOSTED_OPENCLAW_DEPOSIT_AMOUNT
        )
        return context


class TermsOfServiceView(TemplateView):
    template_name = "website/terms.html"


class PrivacyPolicyView(TemplateView):
    template_name = "website/privacy.html"


@require_POST
def hosted_openclaw_checkout(request: HttpRequest) -> HttpResponse:
    if not settings.STRIPE_API_KEY or not settings.HOSTED_OPENCLAW_DEPOSIT_PRICE_ID:
        return HttpResponse("Stripe is not configured for checkout yet.", status=503)

    stripe.api_key = settings.STRIPE_API_KEY

    success_url = (
        request.build_absolute_uri(reverse("home"))
        + "?hosted_openclaw_checkout=success"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("home")) + "?hosted_openclaw_checkout=cancel"
    )

    stripe_kwargs: dict[str, str] = {}
    if settings.STRIPE_CONTEXT_ACCOUNT:
        stripe_kwargs["stripe_account"] = settings.STRIPE_CONTEXT_ACCOUNT

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {"price": settings.HOSTED_OPENCLAW_DEPOSIT_PRICE_ID, "quantity": 1}
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_creation="always",
            metadata={"flow": "hosted_openclaw_deposit"},
            **stripe_kwargs,
        )
    except Exception:
        return HttpResponse("Unable to start Stripe Checkout right now.", status=503)

    return redirect(session.url, code=303)


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

        if self._is_hosted_openclaw_deposit_session(session):
            customer_email = self._extract_customer_email(session)
            if not customer_email:
                return JsonResponse({"error": "missing_customer_email"}, status=400)

            if not self._send_hosted_openclaw_followup(customer_email):
                return JsonResponse({"error": "email_failed"}, status=502)

            StripeWebhookEvent.objects.create(event_id=event_id)
            return JsonResponse({"status": "sent"})

        if self._is_mvp_deposit_session(session):
            customer_email = self._extract_customer_email(session)
            if not customer_email:
                return JsonResponse({"error": "missing_customer_email"}, status=400)

            if not self._send_mvp_followup(customer_email):
                return JsonResponse({"error": "email_failed"}, status=502)

            StripeWebhookEvent.objects.create(event_id=event_id)
            return JsonResponse({"status": "sent"})

        StripeWebhookEvent.objects.create(event_id=event_id)
        return JsonResponse({"status": "ignored"})

    @staticmethod
    def _extract_customer_email(session: dict) -> str | None:
        return (session.get("customer_details") or {}).get("email") or session.get(
            "customer_email"
        )

    @staticmethod
    def _is_hosted_openclaw_deposit_session(session: dict) -> bool:
        metadata = session.get("metadata") or {}
        return metadata.get("flow") == "hosted_openclaw_deposit"

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

    @classmethod
    def _send_mvp_followup(cls, customer_email: str) -> bool:
        subject = "Thanks for choosing the MVP done-for-you service"
        body = (
            "Thanks for choosing the MVP done-for-you service! "
            "Reply with your project details, goals, and any timelines. "
            f"The final service price is {settings.MVP_FINAL_PRICE}."
        )
        return cls._send_mailgun_email(customer_email, subject, body)

    @classmethod
    def _send_hosted_openclaw_followup(cls, customer_email: str) -> bool:
        subject = "Thanks for your Hosted OpenClaw deposit"
        body = (
            "Thanks for your payment. Let's now discuss what exactly you want to "
            "achieve so we can get it as fast as possible.\n\n"
            "Reply with a short overview of your goals, timelines, and any existing "
            "infrastructure we should integrate with."
        )
        return cls._send_mailgun_email(customer_email, subject, body)

    @staticmethod
    def _send_mailgun_email(customer_email: str, subject: str, body: str) -> bool:
        if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
            return False
        if not settings.MAILGUN_FROM_EMAIL:
            return False

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
