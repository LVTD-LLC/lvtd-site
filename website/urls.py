from django.urls import path
from django.views.generic import RedirectView

from website import views

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("", views.HomePageView.as_view(), name="home"),
    path("ai-steering", views.AISteeringView.as_view(), name="ai-steering"),
    path(
        "ai-steering/",
        RedirectView.as_view(
            pattern_name="ai-steering", permanent=True, query_string=True
        ),
    ),
    path("blog/", views.BlogListView.as_view(), name="blog-list"),
    path("blog/<slug:slug>/", views.BlogDetailView.as_view(), name="blog-detail"),
    path("tos/", views.TermsOfServiceView.as_view(), name="terms-of-service"),
    path("privacy/", views.PrivacyPolicyView.as_view(), name="privacy-policy"),
    path(
        "services/hosted-openclaw/",
        views.HostedOpenClawLearnMoreView.as_view(),
        name="hosted-openclaw-learn-more",
    ),
    path(
        "services/hosted-openclaw/checkout/",
        views.hosted_openclaw_checkout,
        name="hosted-openclaw-checkout",
    ),
    path(
        "api/stripe/webhook",
        views.StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
]
