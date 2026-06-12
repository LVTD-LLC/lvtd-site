from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest, HttpResponsePermanentRedirect


class HttpResponsePermanentRedirectPreserveMethod(HttpResponsePermanentRedirect):
    status_code = 308


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if not settings.CANONICAL_HOST_REDIRECT_ENABLED:
            return self.get_response(request)

        canonical = urlsplit(settings.SITE_URL)
        canonical_host = canonical.netloc.lower().rstrip(".")
        current_host = self._current_host(request)
        current_scheme = request.scheme

        if current_host != canonical_host or current_scheme != canonical.scheme:
            return HttpResponsePermanentRedirectPreserveMethod(
                f"{canonical.scheme}://{canonical.netloc}{request.get_full_path()}"
            )

        return self.get_response(request)

    @staticmethod
    def _current_host(request: HttpRequest) -> str:
        host = request.META.get("HTTP_HOST")
        if not host:
            server_name = request.META.get("SERVER_NAME", "")
            server_port = request.META.get("SERVER_PORT", "")
            host = f"{server_name}:{server_port}" if server_port else server_name
        return host.lower().rstrip(".")
