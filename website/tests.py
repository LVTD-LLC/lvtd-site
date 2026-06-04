import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from website.models import BlogPost


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
        self.assertContains(response, "Product engineering for founders")
        self.assertContains(response, "Shipped work")
        self.assertContains(response, "Real products, not portfolio theater.")
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

    def test_homepage_has_hosted_openclaw_actions(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(response, reverse("hosted-openclaw-checkout"))
        self.assertContains(response, reverse("hosted-openclaw-learn-more"))

    def test_homepage_has_blog_link(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(response, reverse("blog-list"))
        self.assertContains(response, "Read notes")


class BlogPagesTests(TestCase):
    def setUp(self) -> None:
        self.published_post = BlogPost.objects.create(
            title="Shipping with confidence",
            slug="shipping-with-confidence",
            summary="How we ship faster with fewer incidents.",
            body="This is the post body.",
        )
        BlogPost.objects.create(
            title="Draft post",
            slug="draft-post",
            summary="This is still in draft.",
            body="Draft body.",
            is_published=False,
        )

    def test_blog_index_lists_published_posts_only(self) -> None:
        client = Client()
        response = client.get(reverse("blog-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shipping with confidence")
        self.assertNotContains(response, "Draft post")
        self.assertContains(
            response,
            reverse("blog-detail", kwargs={"slug": self.published_post.slug}),
        )

    def test_blog_detail_loads_for_published_post(self) -> None:
        client = Client()
        response = client.get(
            reverse("blog-detail", kwargs={"slug": self.published_post.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shipping with confidence")
        self.assertContains(response, "How we ship faster with fewer incidents.")
        self.assertContains(response, "This is the post body.")

    def test_blog_detail_404_for_draft_post(self) -> None:
        client = Client()
        response = client.get(reverse("blog-detail", kwargs={"slug": "draft-post"}))

        self.assertEqual(response.status_code, 404)


class HostedOpenClawPagesTests(TestCase):
    def test_learn_more_page_loads(self) -> None:
        client = Client()
        response = client.get(reverse("hosted-openclaw-learn-more"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hosted OpenClaw Service")


class HostedOpenClawCheckoutTests(TestCase):
    @override_settings(
        STRIPE_API_KEY="sk_test",
        HOSTED_OPENCLAW_DEPOSIT_PRICE_ID="price_test_123",
        STRIPE_CONTEXT_ACCOUNT="",
    )
    @patch("website.views.stripe.checkout.Session.create")
    def test_checkout_redirects_to_stripe(self, mock_create: Mock) -> None:
        mock_create.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/c/test"
        )

        client = Client()
        response = client.post(reverse("hosted-openclaw-checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.stripe.com/c/test")
        self.assertEqual(mock_create.call_count, 1)

        kwargs = mock_create.call_args.kwargs
        self.assertEqual(kwargs["line_items"][0]["price"], "price_test_123")
        self.assertEqual(kwargs["metadata"]["flow"], "hosted_openclaw_deposit")


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
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
        MAILGUN_REPLY_TO_EMAIL="reply@example.com",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_sends_hosted_openclaw_followup(
        self, mock_retrieve: Mock, mock_post: Mock
    ) -> None:
        session = {
            "metadata": {"flow": "hosted_openclaw_deposit"},
            "customer_details": {"email": "payer@example.com"},
        }
        mock_retrieve.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data={"object": session},
        )
        mock_post.return_value = SimpleNamespace(status_code=200)

        status_code = self._post_webhook({"id": "evt_hosted_1"})
        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(
            mock_post.call_args.kwargs["data"]["subject"],
            "Thanks for your Hosted OpenClaw deposit",
        )
        self.assertIn(
            "Let's now discuss what exactly you want to achieve",
            mock_post.call_args.kwargs["data"]["text"],
        )

        status_code = self._post_webhook({"id": "evt_hosted_1"})
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
