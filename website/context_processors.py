from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def seo(request: HttpRequest) -> dict[str, str]:
    site_url = settings.SITE_URL
    return {
        "site_url": site_url,
        "canonical_url": f"{site_url}{request.path}",
    }
