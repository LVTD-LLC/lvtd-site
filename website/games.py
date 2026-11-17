import re
from functools import cache

import requests
from django.conf import settings
from django.core.cache import cache as catalogue_cache
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import get_resolver
from django.views.decorators.http import require_safe


@cache
def site_prefixes():
    """Reserve every top-level Django route, including nested URL includes."""
    prefixes = {"static", "media"}
    pending = list(get_resolver().url_patterns)
    while pending:
        pattern = pending.pop()
        prefix = str(pattern.pattern).partition("/")[0]
        if prefix:
            prefixes.add(prefix)
        elif hasattr(pattern, "url_patterns"):
            pending.extend(pattern.url_patterns)
    return prefixes


def catalogue():
    games = catalogue_cache.get("arcade-catalogue")
    if games is not None:
        return games
    try:
        response = requests.get(settings.GAMES_MANIFEST_URL, timeout=(1, 2))
        response.raise_for_status()
        games = {}
        for game in response.json():
            slug = game["slug"]
            if not re.fullmatch(r"[a-z][a-z0-9-]*", slug) or slug in site_prefixes():
                continue
            games[slug] = game
        catalogue_cache.set("arcade-last-release", games, timeout=86400)
    except (requests.RequestException, ValueError, TypeError, KeyError):
        games = catalogue_cache.get("arcade-last-release")
        # Bound retries during a deployment, even on a cold worker.
        catalogue_cache.set("arcade-catalogue", games or {}, timeout=5)
        return games or {}
    catalogue_cache.set("arcade-catalogue", games, timeout=30)
    return games


@require_safe
def games_index(request):
    games = catalogue()
    return render(
        request,
        "website/games.html",
        {"games": games.values()},
        status=200 if games else 503,
    )


class GameRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        slug, slash, rest = path[1:].partition("/")
        game_api = path.startswith(("/api/jess/", "/api/life/", "/api/corporate-bs/"))
        if (slug == "games" and rest) or game_api:
            return self.forward()
        if (
            slug not in site_prefixes()
            and re.fullmatch(r"[a-z][a-z0-9-]*", slug)
            and slug in catalogue()
        ):
            if not slash:
                return HttpResponsePermanentRedirect(
                    request.get_full_path(force_append_slash=True),
                    preserve_request=True,
                )
            return self.forward()
        return self.get_response(request)

    @staticmethod
    def forward():
        # A named Nginx location preserves the original URI, method and body.
        return HttpResponse(headers={"X-Accel-Redirect": "@lvtd_games"})
