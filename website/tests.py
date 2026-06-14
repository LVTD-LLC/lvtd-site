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
        HOSTED_OPENCLAW_DEPOSIT_AMOUNT="$125",
    )
    def test_homepage_loads(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LVTD, LLC")
        self.assertContains(
            response, "Working software for founders with no team to spare."
        )
        self.assertContains(response, "Agency as a service")
        self.assertContains(response, "Hire the same system that ships the projects.")
        self.assertContains(response, "MVP done for you")
        self.assertContains(response, "Pay a $100 deposit")
        self.assertContains(response, "$5,000")
        self.assertContains(response, "Reserve MVP build")
        self.assertContains(response, "Reserve OpenClaw setup")
        self.assertContains(response, "Selected work")
        self.assertContains(response, "Proof that ships.")
        self.assertContains(response, "Active projects")
        self.assertContains(response, "Archived projects")
        self.assertContains(
            response, "Send the problem you want off your plate."
        )

        for project_name in (
            "FileBridge",
            "PGSandbox MCP",
            "Skills",
            "Djass",
            "Awesome",
            "Ask HN Digest",
            "PageFresh",
            "Talent Leads",
            "Built with Django",
            "LevReview",
            "Tech Job Alerts",
            "Is it Keto",
            "OSIG",
            "StatusHen",
            "TuxSEO",
        ):
            self.assertContains(response, project_name)

        self.assertNotContains(response, "Cleanapp")
        self.assertContains(response, "https://github.com/LVTD-LLC")
        self.assertContains(response, "https://github.com/LVTD-LLC/tuxseo")
        self.assertNotContains(response, "https://statushen.com")
        self.assertNotContains(response, "https://isitketo.org")

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

    def test_homepage_has_legal_links(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(response, reverse("terms-of-service"))
        self.assertContains(response, reverse("privacy-policy"))
        self.assertContains(response, "Terms")
        self.assertContains(response, "Privacy")

    @override_settings(SITE_URL="https://lvtd.test")
    def test_homepage_has_shared_seo_metadata(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(
            response,
            '<link rel="canonical" href="https://lvtd.test/" />',
            html=True,
        )
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'property="og:image"')
        self.assertContains(response, 'name="twitter:image"')
        self.assertContains(response, 'rel="icon"')
        self.assertContains(response, 'name="twitter:card"')
        self.assertContains(response, 'type="application/ld+json"')
        self.assertContains(response, '"logo": "https://lvtd.test/static/')


class CanonicalRedirectTests(TestCase):
    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
    )
    def test_redirects_www_to_canonical_host(self) -> None:
        client = Client()
        response = client.get(
            "/blog/?utm_source=test",
            HTTP_HOST="www.lvtd.test",
            secure=True,
        )

        self.assertEqual(response.status_code, 308)
        self.assertEqual(
            response["Location"], "https://lvtd.test/blog/?utm_source=test"
        )

    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
    )
    def test_redirects_http_to_canonical_scheme(self) -> None:
        client = Client()
        response = client.get("/", HTTP_HOST="lvtd.test")

        self.assertEqual(response.status_code, 308)
        self.assertEqual(response["Location"], "https://lvtd.test/")

    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
        ALLOWED_HOSTS=["lvtd.test", "testserver"],
    )
    def test_allows_canonical_host_and_scheme(self) -> None:
        client = Client()
        response = client.get("/", HTTP_HOST="lvtd.test", secure=True)

        self.assertEqual(response.status_code, 200)

    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
        ALLOWED_HOSTS=["lvtd.test", "testserver"],
    )
    def test_allows_canonical_host_with_default_port(self) -> None:
        client = Client()
        response = client.get("/", HTTP_HOST="lvtd.test:443", secure=True)

        self.assertEqual(response.status_code, 200)

    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
        ALLOWED_HOSTS=["lvtd.test", "testserver"],
    )
    def test_allows_wsgi_fallback_with_default_port(self) -> None:
        client = Client()
        response = client.get(
            "/",
            secure=True,
            SERVER_NAME="lvtd.test",
            SERVER_PORT="443",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(
        SITE_URL="https://lvtd.test",
        CANONICAL_HOST_REDIRECT_ENABLED=True,
    )
    def test_redirects_malformed_host_port_to_canonical_url(self) -> None:
        client = Client()
        response = client.get(
            "/?utm_source=test",
            HTTP_HOST="lvtd.test:notaport",
            secure=True,
        )

        self.assertEqual(response.status_code, 308)
        self.assertEqual(response["Location"], "https://lvtd.test/?utm_source=test")


class CrawlEndpointTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_robots_txt_allows_public_site_and_points_to_sitemap(self) -> None:
        client = Client()
        response = client.get(reverse("robots"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        content = response.content.decode()
        self.assertIn("User-agent: *", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Disallow: /admin/", content)
        self.assertIn("Disallow: /api/", content)
        self.assertIn("Sitemap: https://lvtd.test/sitemap.xml", content)

    @override_settings(SITE_URL="https://lvtd.test", SITE_LASTMOD="2026-06-12")
    def test_sitemap_includes_public_indexable_urls_only(self) -> None:
        published_post = BlogPost.objects.create(
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

        client = Client()
        response = client.get(reverse("sitemap"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        content = response.content.decode()
        self.assertTrue(content.startswith("<?xml version='1.0' encoding='utf-8'?>"))
        self.assertIn("<loc>https://lvtd.test/</loc>", content)
        self.assertIn("<lastmod>2026-06-12</lastmod>", content)
        self.assertIn("<loc>https://lvtd.test/blog/</loc>", content)
        self.assertIn("<loc>https://lvtd.test/services/hosted-openclaw/</loc>", content)
        self.assertIn("<loc>https://lvtd.test/tos/</loc>", content)
        self.assertIn("<loc>https://lvtd.test/privacy/</loc>", content)
        self.assertIn(
            f"<loc>https://lvtd.test/blog/{published_post.slug}/</loc>", content
        )
        self.assertIn("<lastmod>", content)
        self.assertNotIn("draft-post", content)
        self.assertNotIn("checkout", content)
        self.assertNotIn("api/stripe", content)


class LegalPagesTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_terms_of_service_page_loads(self) -> None:
        client = Client()
        response = client.get(reverse("terms-of-service"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terms of Service")
        self.assertContains(response, "Last updated")
        self.assertContains(response, "Deposits, Payments, and Refunds")
        self.assertContains(response, "Work Product and Intellectual Property")
        self.assertContains(response, '"@type": "WebPage"')
        self.assertContains(
            response,
            '<link rel="canonical" href="https://lvtd.test/tos/" />',
            html=True,
        )

    @override_settings(SITE_URL="https://lvtd.test")
    def test_privacy_policy_page_loads(self) -> None:
        client = Client()
        response = client.get(reverse("privacy-policy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy Policy")
        self.assertContains(response, "Last updated")
        self.assertContains(response, "Plausible Analytics")
        self.assertContains(response, "Mailgun")
        self.assertContains(response, '"@type": "WebPage"')
        self.assertContains(
            response,
            '<link rel="canonical" href="https://lvtd.test/privacy/" />',
            html=True,
        )


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
        self.assertContains(response, '"@type": "Article"')

    def test_blog_detail_404_for_draft_post(self) -> None:
        client = Client()
        response = client.get(reverse("blog-detail", kwargs={"slug": "draft-post"}))

        self.assertEqual(response.status_code, 404)


class HostedOpenClawPagesTests(TestCase):
    @override_settings(HOSTED_OPENCLAW_DEPOSIT_AMOUNT="$150")
    def test_learn_more_page_loads(self) -> None:
        client = Client()
        response = client.get(reverse("hosted-openclaw-learn-more"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hosted OpenClaw Service")
        self.assertContains(
            response, "Private OpenClaw, deployed and operated for your workflows."
        )
        self.assertContains(response, "Best fit")
        self.assertContains(response, "Frequently asked questions")
        self.assertContains(response, "$150 deposit")
        self.assertContains(response, "Reserve OpenClaw setup")
        self.assertContains(response, '"@type": "Service"')
        self.assertContains(response, '"@type": "FAQPage"')


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
