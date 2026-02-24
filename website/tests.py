from django.test import Client, TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_homepage_loads(self) -> None:
        client = Client()
        response = client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LVTD")
        self.assertContains(response, "Projects")
