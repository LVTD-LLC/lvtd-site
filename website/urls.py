from django.urls import path

from website.views import HomePageView, StripeWebhookView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("api/stripe/webhook", StripeWebhookView.as_view(), name="stripe-webhook"),
]
