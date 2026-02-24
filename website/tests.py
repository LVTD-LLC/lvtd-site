from django.test import Client, TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_homepage_loads(self) -> None:
        client = Client()
        response = client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LVTD, LLC")
        self.assertContains(response, "Selected products I’ve built")
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
