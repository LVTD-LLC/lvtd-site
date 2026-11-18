import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import stripe
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.html import escape

from website.models import BlogPost


class HomePageTests(TestCase):
    @patch("website.views.catalogue")
    def test_homepage_shows_work_and_released_games(self, catalogue: Mock) -> None:
        catalogue.return_value = {"demo": {"title": "Demo game", "slug": "demo"}}
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'href="/demo/"')
        for name in (
            "ShipRust",
            "TastefulKit",
            "Drape",
            "Jev Benchmark",
            "AI Steering",
        ):
            self.assertContains(response, name)
        for route in ("projects", "games", "research", "blog-list"):
            self.assertContains(response, f'href="{reverse(route)}"')
        self.assertNotContains(response, "deposit")
        self.assertNotContains(response, "OpenClaw")
        self.assertNotContains(response, "buy.stripe.com")

    @patch("website.views.catalogue", return_value={})
    def test_homepage_still_works_without_the_arcade(self, catalogue: Mock) -> None:
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Browse the arcade")
        self.assertContains(response, "Drape")

    def test_homepage_has_legal_links(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertContains(response, reverse("terms-of-service"))
        self.assertContains(response, reverse("privacy-policy"))
        self.assertContains(response, "Terms")
        self.assertContains(response, "Privacy")

    def test_shared_navigation_marks_current_section(self) -> None:
        for route, label in (
            ("projects", "Projects"),
            ("research", "Research"),
            ("blog-list", "Blog"),
        ):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, 'aria-label="Primary navigation"')
                self.assertContains(response, f'aria-current="page">{label}</a>')
                self.assertContains(response, "prefers-color-scheme: dark")
                self.assertContains(response, 'href="#main-content"')

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
    def test_projects_catalog(self):
        response = self.client.get(reverse("projects"))
        self.assertContains(response, "Projects &amp; apps")
        self.assertNotContains(response, "archive")
        self.assertNotContains(response, "ReviewGate")
        self.assertNotContains(response, "Jev Benchmark")
        self.assertContains(response, 'href="#client-work"')
        client_projects = response.context["client_entries"]
        self.assertIn("Meliora Advisory", [entry["name"] for entry in client_projects])
        self.assertContains(response, "LVTD does not own or operate the business.")
        self.assertNotContains(response, "https://meliora-advisory.com/")
        self.assertNotContains(response, "https://github.com/LVTD-LLC/pgsandbox")

    @override_settings(SITE_URL="https://lvtd.test")
    def test_each_listed_project_has_a_unique_profile_and_outbound_links(self):
        index = self.client.get(reverse("projects"))
        entries = index.context["active_entries"] + index.context["client_entries"]
        self.assertEqual(len(entries), len({entry["slug"] for entry in entries}))
        sitemap = self.client.get(reverse("sitemap"))
        for entry in entries:
            with self.subTest(project=entry["name"]):
                url = reverse("project-detail", args=[entry["slug"]])
                self.assertContains(index, f'href="{url}"', count=1)
                self.assertContains(sitemap, f"<loc>https://lvtd.test{url}</loc>")
                detail = self.client.get(url)
                self.assertContains(detail, entry["name"])
                self.assertEqual(
                    detail.context["project"]["overview"], entry["overview"]
                )
                self.assertContains(detail, escape(entry["overview"]))
                self.assertContains(
                    detail, f'rel="canonical" href="https://lvtd.test{url}"'
                )
                self.assertContains(detail, 'aria-current="location">Projects</a>')
                for link in entry["links"]:
                    target = link.get("url") or reverse(link["route"])
                    self.assertContains(detail, f'href="{escape(target)}"')

    def test_featured_projects_open_their_profiles(self):
        page = self.client.get(reverse("home"))
        for slug in ("shiprust", "tastefulkit", "drape"):
            self.assertContains(page, f'href="/projects/{slug}/"')
        self.assertNotContains(page, "https://shiprust.com/")

    def test_unlisted_project_profiles_return_404(self):
        for slug in ("unknown-project", "archive", "reviewgate", "jev-benchmark"):
            self.assertEqual(self.client.get(f"/projects/{slug}/").status_code, 404)


class ResearchPageTests(TestCase):
    @override_settings(SITE_URL="https://lvtd.test")
    def test_research_catalog(self) -> None:
        response = self.client.get(reverse("research"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="directory"', count=1)
        self.assertContains(response, ">Jev Benchmark</a>")
        self.assertContains(response, ">AI Steering</a>")
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
        self.assertNotIn("hosted-openclaw", content)
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


class RetiredOfferTests(TestCase):
    def test_offer_and_checkout_are_removed(self):
        self.assertEqual(self.client.get("/services/hosted-openclaw/").status_code, 404)
        self.assertEqual(
            self.client.post("/services/hosted-openclaw/checkout/").status_code, 404
        )
        self.assertNotContains(self.client.get("/blog/what-lvtd-builds/"), "OpenClaw")


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
