from django.urls import path

from website import views

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
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
