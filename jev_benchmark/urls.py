from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("jev-benchmark", views.index, name="jev-benchmark"),
    path(
        "jev-benchmark/",
        RedirectView.as_view(pattern_name="jev-benchmark", permanent=True),
    ),
    path(
        "jev-benchamrk",
        RedirectView.as_view(pattern_name="jev-benchmark", permanent=True),
    ),
    path(
        "jev-benchamrk/",
        RedirectView.as_view(pattern_name="jev-benchmark", permanent=True),
    ),
    path("jev-benchmark/<slug:slug>", views.detail, name="jev-question"),
]
