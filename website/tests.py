import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import stripe
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
        self.assertContains(response, "From idea to credible software.")
        self.assertContains(response, "One builder. One complete first release.")
        self.assertContains(response, "A focused MVP, done for you.")
        self.assertContains(response, "Reserve implementation with a $100 deposit.")
        self.assertContains(response, "$5,000")
        self.assertContains(response, "Reserve your MVP")
        self.assertContains(response, "Reserve OpenClaw setup")
        self.assertContains(response, reverse("projects"))
        self.assertNotContains(response, 'class="project-card')
        self.assertNotContains(response, 'href="#work"')
        self.assertContains(response, "Have an MVP in mind?")
        self.assertNotContains(response, "data-uidotsh-pick")
        self.assertNotContains(response, "data-uidotsh-option")
        self.assertNotContains(response, "https://ui.sh/ui-picker.js")

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

    def test_shared_shell_has_no_header_and_uses_system_theme(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(response, "prefers-color-scheme: dark")
        self.assertNotContains(response, "<header")
        self.assertNotContains(response, 'aria-label="Homepage"')
        self.assertNotContains(response, 'aria-label="Primary navigation"')
        self.assertNotContains(response, 'id="theme-toggle"')
        self.assertNotContains(response, "localStorage")
        self.assertNotContains(response, 'class="mobile-menu"')
        self.assertNotContains(response, "Start a build")

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


class ProjectsPageTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_projects_catalog(self) -> None:
        response = self.client.get(reverse("projects"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "<strong>ReviewGate</strong>", count=1)
        self.assertContains(response, "<table", count=3)
        self.assertContains(response, "<img", count=24)
        self.assertContains(
            response,
            '<link rel="canonical" href="https://lvtd.test/projects/" />',
            html=True,
        )
        content = response.content.decode()
        self.assertLess(content.index('id="active"'), content.index('id="archive"'))
        for project_name in (
            "ShipRust",
            "Rowset",
            "PGSandbox",
            "ReviewGate",
            "CiteGuild",
            "Djass",
            "Browse Awesome",
            "Ask HN Digest",
            "Staleaway",
            "Talent Leads",
            "Built with Django",
            "LevReview",
            "Tech Job Alerts",
            "Is It Keto",
            "TastefulKit",
            "nitpick",
            "Built with Rust",
            "Built with Bend",
            "LVTD Games",
            "rasulkireev.com",
            "Meliora Advisory",
            "OSIG",
            "StatusHen",
            "TuxSEO",
        ):
            self.assertContains(response, project_name)

        active, remaining = content.split('id="active"', 1)[1].split(
            'id="client-work"', 1
        )
        client_work, archived = remaining.split('id="archive"', 1)
        self.assertIn("<strong>Meliora Advisory</strong>", client_work)
        self.assertNotIn("<strong>Meliora Advisory</strong>", active)
        self.assertNotIn("<strong>Meliora Advisory</strong>", archived)
        self.assertIn("https://meliora-advisory.com/", client_work)
        self.assertIn("Website build only", client_work)
        self.assertContains(response, 'href="#client-work"')
        for name in (
            "Ask HN Digest",
            "LevReview",
            "ReviewGate",
            "Talent Leads",
            "Tech Job Alerts",
        ):
            self.assertNotIn(f"<strong>{name}</strong>", active)
            self.assertIn(f"<strong>{name}</strong>", archived)
        self.assertIn("<strong>Is It Keto</strong>", active)
        self.assertNotIn(": Website", archived)
        self.assertNotContains(response, "gettalentleads.com")
        self.assertNotContains(response, "gettjalerts.com")
        self.assertContains(response, "https://browseawesome.com/")
        self.assertNotContains(response, "https://awesome.lvtd.dev/")
        self.assertNotContains(response, "<strong>AI Steering</strong>")
        self.assertNotContains(response, "<strong>Jev Benchmark</strong>")
        self.assertContains(response, reverse("research"))
        self.assertContains(response, "https://citeguild.com/")
        self.assertNotContains(response, "https://citeguild.app/")
        self.assertNotContains(response, "https://skills.lvtd.dev")
        self.assertContains(response, "https://pgsandbox.dev/")
        self.assertNotContains(response, "https://pgsandbox-mcp.lvtd.dev/")
        self.assertContains(response, "https://github.com/LVTD-LLC/pgsandbox")
        self.assertContains(response, "https://github.com/rasulkireev/apw")
        self.assertContains(response, "Website build only", count=2)
        self.assertContains(response, "LVTD does not own or operate the business.")
        self.assertNotContains(response, "FileBridge")
        self.assertNotContains(response, "https://filebridge.lvtd.dev")
        self.assertNotContains(response, "Cleanapp")
        self.assertContains(response, "https://github.com/LVTD-LLC")
        self.assertContains(response, "https://github.com/LVTD-LLC/TuxSEO")
        self.assertContains(response, "https://github.com/LVTD-LLC/osig")
        self.assertContains(response, "https://github.com/LVTD-LLC/reviewgate")
        self.assertNotContains(response, "https://osig.app?ref=lvtd.dev")
        self.assertNotContains(response, "https://statushen.com")
        self.assertContains(response, "https://isitketo.org/")


class ResearchPageTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_research_catalog(self) -> None:
        response = self.client.get(reverse("research"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table", count=1)
        self.assertContains(response, '<th scope="row">', count=2)
        self.assertNotContains(response, "<img")
        self.assertContains(response, "<strong>Jev Benchmark</strong>")
        self.assertContains(response, "<strong>AI Steering</strong>")
        self.assertContains(response, f'href="{reverse("jev-benchmark")}"')
        self.assertContains(response, f'href="{reverse("ai-steering")}"')
        self.assertContains(response, "https://github.com/LVTD-LLC/ai-steering")
        self.assertContains(response, "https://github.com/LVTD-LLC/lvtd-site")
        self.assertContains(response, "https://lvtd.test/research/")
        self.assertContains(self.client.get(reverse("home")), reverse("research"))
        self.assertContains(
            self.client.get(reverse("sitemap")),
            "<loc>https://lvtd.test/research/</loc>",
        )


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
        self.assertIn("<loc>https://lvtd.test/projects/</loc>", content)
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
        self.assertEqual(kwargs["metadata"]["price_id"], "price_test_123")


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
        mock_retrieve.return_value = stripe.Event.construct_from(
            {
                "id": "evt_1",
                "type": "checkout.session.completed",
                "data": {"object": session},
            },
            "sk_test",
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
        HOSTED_OPENCLAW_DEPOSIT_PRICE_ID="price_hosted_openclaw",
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
            "metadata": {
                "flow": "hosted_openclaw_deposit",
                "price_id": "price_hosted_openclaw",
            },
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
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_does_not_fallback_to_matching_amount(
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
        self.assertEqual(mock_post.call_count, 0)

    @override_settings(
        STRIPE_API_KEY="sk_test",
        HOSTED_OPENCLAW_DEPOSIT_PRICE_ID="price_hosted_openclaw",
        MAILGUN_API_KEY="mg_key",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_FROM_EMAIL="hello@example.com",
    )
    @patch("website.views.requests.post")
    @patch("website.views.stripe.Event.retrieve")
    def test_webhook_ignores_hosted_flow_with_wrong_price(
        self, mock_retrieve: Mock, mock_post: Mock
    ) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data={
                "object": {
                    "metadata": {
                        "flow": "hosted_openclaw_deposit",
                        "price_id": "price_another_product",
                    },
                    "customer_details": {"email": "buyer@example.com"},
                }
            },
        )

        status_code = self._post_webhook({"id": "evt_wrong_hosted_price"})

        self.assertEqual(status_code, 200)
        self.assertEqual(mock_post.call_count, 0)


class AISteeringTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_catalog_preserves_guides_links_and_installation(self):
        response = self.client.get(reverse("ai-steering"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="https://lvtd.test/ai-steering"')
        self.assertContains(response, '"@type":"CollectionPage"')
        sections = response.context["catalog"]["sections"]
        self.assertEqual(sum(len(s["resources"]) for s in sections), 11)
        for section in sections:
            for resource in section["resources"]:
                self.assertContains(response, f'id="{resource["slug"]}"')
                self.assertContains(response, resource["name"])
                for link in resource["usefulResources"] + resource["greatExamples"]:
                    self.assertContains(response, link["href"])
        self.assertContains(response, "npx skills add LVTD-LLC/ai-steering")
        self.assertContains(response, "gh skill install LVTD-LLC/ai-steering")
        self.assertNotContains(response, "https://ai-steering.lvtd.dev")

    def test_slash_variant_redirects_to_canonical_path(self):
        self.assertRedirects(
            self.client.get("/ai-steering/?ref=old"),
            "/ai-steering?ref=old",
            status_code=301,
        )

    @override_settings(SITE_URL="https://lvtd.test")
    def test_catalog_is_discoverable(self):
        self.assertContains(self.client.get(reverse("research")), 'href="/ai-steering"')
        self.assertContains(
            self.client.get(reverse("sitemap")),
            "<loc>https://lvtd.test/ai-steering</loc>",
        )


class JevArticleTests(TestCase):
    def test_seeded_article_is_discoverable_and_uses_trusted_markup(self):
        post = BlogPost.objects.get(slug="jev-ai-model-benchmark")
        url = reverse("blog-detail", kwargs={"slug": post.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "website/articles/jev_ai_model_benchmark.html"
        )
        self.assertContains(response, '<figure class="jev-chart">')
        self.assertNotContains(response, post.body)
        for source in ("home", "blog-list", "sitemap", "jev-benchmark"):
            self.assertContains(self.client.get(reverse(source)), url)
        post.is_published = False
        post.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_plain_text_blog_body_remains_escaped(self):
        post = BlogPost.objects.create(
            title="Plain text",
            slug="plain-text",
            summary="Summary",
            body='<script>alert("unsafe")</script>',
        )
        response = self.client.get(reverse("blog-detail", kwargs={"slug": post.slug}))
        self.assertNotContains(response, post.body)
        self.assertContains(response, "&lt;script&gt;")

    def test_repo_article_admin_rejects_body_and_slug_edits(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from website.admin import BlogPostAdmin

        post = BlogPost.objects.get(slug="jev-ai-model-benchmark")
        original_body, original_slug = post.body, post.slug
        admin = BlogPostAdmin(BlogPost, AdminSite())
        request = RequestFactory().get("/admin/")
        form_class = admin.get_form(request, post)
        self.assertNotIn("body", form_class.base_fields)
        self.assertNotIn("slug", form_class.base_fields)
        self.assertEqual(admin.get_prepopulated_fields(request, post), {})
        self.assertIn("pull request", admin.article_source(post))
        form = form_class(
            data={
                "title": post.title,
                "summary": post.summary,
                "published_at_0": "2026-09-28",
                "published_at_1": "16:30:00",
                "is_published": "on",
                "body": "Forged edit",
                "slug": "changed",
            },
            instance=post,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        post.refresh_from_db()
        self.assertEqual(post.body, original_body)
        self.assertEqual(post.slug, original_slug)
        ordinary = BlogPost(title="Other", slug="other", body="Editable")
        self.assertIn("body", admin.get_form(request, ordinary).base_fields)

    def test_updated_article_has_dedicated_social_image(self):
        response = self.client.get("/blog/jev-ai-model-benchmark/")
        self.assertContains(response, "2,436 comparisons")
        self.assertContains(
            response, 'name="twitter:card" content="summary_large_image"'
        )
        self.assertContains(
            response, "images/blog/jev-ai-model-benchmark-og.png", count=2
        )
        self.assertContains(response, 'property="og:image"', count=1)
        self.assertContains(response, 'name="twitter:image"', count=1)
        self.assertContains(response, "18:59 UTC")
        self.assertContains(
            self.client.get("/"), 'name="twitter:card" content="summary"'
        )
        self.assertNotContains(self.client.get("/"), "jev-ai-model-benchmark-og.png")

    def test_reader_rewrite_metadata_preserves_independent_edits(self):
        from importlib import import_module
        from types import SimpleNamespace

        from django.apps import apps

        migration = import_module("website.migrations.0006_jev_reader_first")
        editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))
        post = BlogPost.objects.get(slug=migration.SLUG)
        post.title = "An independently edited title"
        post.summary = migration.OLD_SUMMARY
        post.save()
        migration.rewrite_metadata(apps, editor)
        post.refresh_from_db()
        self.assertEqual(post.title, "An independently edited title")
        self.assertEqual(post.summary, migration.NEW_SUMMARY)
        post.title = migration.OLD_TITLE
        post.summary = "An independently edited summary"
        post.save()
        migration.rewrite_metadata(apps, editor)
        post.refresh_from_db()
        self.assertEqual(post.title, migration.NEW_TITLE)
        self.assertEqual(post.summary, "An independently edited summary")
        migration.reverse_metadata(apps, editor)
        post.refresh_from_db()
        self.assertEqual(post.title, migration.OLD_TITLE)
        self.assertEqual(post.summary, "An independently edited summary")
