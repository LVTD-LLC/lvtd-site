from django.urls import path

from website import views

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("", views.HomePageView.as_view(), name="home"),
    path("blog/", views.BlogListView.as_view(), name="blog-list"),
    path("blog/<slug:slug>/", views.BlogDetailView.as_view(), name="blog-detail"),
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
