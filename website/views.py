from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "website/home.html"
