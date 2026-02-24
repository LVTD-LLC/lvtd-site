import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse


class HomePageTests(TestCase):
    @override_settings(
        MVP_DEPOSIT_CHECKOUT_URL="https://example.com/pay",
        MVP_DEPOSIT_AMOUNT="$100",
        MVP_FINAL_PRICE="$5,000",
    )
    def test_homepage_loads(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LVTD, LLC")
        self.assertContains(response, "MVP done-for-you")
        self.assertContains(response, "Pay a $100 deposit")
        self.assertContains(response, "$5,000")
        self.assertContains(response, "Pay $100 deposit")
        self.assertContains(response, "Selected products I’ve built")
        self.assertContains(response, "Need a builder who can ship?")

        for project_name in (
            "Talent Leads",
            "Built with Django",
            "LevReview",
            "Tech Job Alerts",
            "Is it Keto",
            "OSIG",
            "StatusHen",
            "TuxSEO",
            "Cleanapp",
        ):
            self.assertContains(response, project_name)


class StripeWebhookTests(TestCase):
    def _post_webhook(self, payload: dict) -> int:
        client = Client()
        response = client.post(
            reverse("stripe-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        return response.status_code

    @override_settings(
        STRIPE_API_KEY="sk_test",
        STRIPE_CONTEXT_ACCOUNT="",
        STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID="plink_123",
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
        MAILGUN_REPLY_TO_EMAIL="reply@example.com",
        MVP_FINAL_PRICE="$5,000",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_sends_email_once(
        self, mock_retrieve: Mock, mock_post: Mock
    ) -> None:
        session = {
            "payment_link": "plink_123",
            "customer_details": {"email": "buyer@example.com"},
        }
        mock_retrieve.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data={"object": session},
        )
        mock_post.return_value = SimpleNamespace(status_code=200)

        status_code = self._post_webhook({"id": "evt_1"})
        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 1)

        status_code = self._post_webhook({"id": "evt_1"})
        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 1)

    @override_settings(
        STRIPE_API_KEY="sk_test",
        STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID="plink_123",
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_ignores_non_matching_payment_link(
        self, mock_retrieve: Mock, mock_post: Mock
    ) -> None:
        session = {
            "payment_link": "plink_other",
            "customer_details": {"email": "buyer@example.com"},
        }
        mock_retrieve.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data={"object": session},
        )
        mock_post.return_value = SimpleNamespace(status_code=200)

        status_code = self._post_webhook({"id": "evt_2"})
        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 0)

    @override_settings(
        STRIPE_API_KEY="sk_test",
        STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID="",
        STRIPE_MVP_DEPOSIT_FALLBACK_AMOUNT=10000,
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_fallback_amount_matches(
        self, mock_retrieve: Mock, mock_post: Mock
    ) -> None:
        session = {
            "amount_total": 10000,
            "currency": "usd",
            "customer_email": "buyer@example.com",
        }
        mock_retrieve.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data={"object": session},
        )
        mock_post.return_value = SimpleNamespace(status_code=200)

        status_code = self._post_webhook({"id": "evt_3"})
        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 1)
