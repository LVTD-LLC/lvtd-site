from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase


class GamesTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        fetch = patch("website.games.requests.get").start()
        self.addCleanup(patch.stopall)
        fetch.return_value.json.return_value = [
            {"slug": slug, "title": slug, "logo": "/logos/demo.svg"}
            for slug in ("new-game", "blog")
        ]

    def test_release_updates_catalogue_and_dispatch(self):
        page = self.client.get("/games/")
        self.assertContains(page, 'href="/new-game/"')
        self.assertNotContains(page, 'data-game="blog"')
        self.assertEqual(self.client.get("/new-game?q=1")["Location"], "/new-game/?q=1")
        for url in ("/new-game/", "/new-game/assets/main.js", "/games/logos/demo.svg"):
            self.assertEqual(self.client.get(url)["X-Accel-Redirect"], "@lvtd_games")
        self.assertEqual(
            self.client.post("/api/jess/move")["X-Accel-Redirect"], "@lvtd_games"
        )
        self.assertEqual(self.client.get("/unknown-game/").status_code, 404)
        self.assertNotIn("X-Accel-Redirect", self.client.get("/api/stripe/webhook"))
