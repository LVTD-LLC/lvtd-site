from __future__ import annotations

import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_q",
    "website",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "website.context_processors.seo",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

TESTING = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in " ".join(sys.argv)
STATICFILES_BACKEND = "whitenoise.storage.CompressedManifestStaticFilesStorage"
if DEBUG or TESTING:
    STATICFILES_BACKEND = "django.contrib.staticfiles.storage.StaticFilesStorage"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": STATICFILES_BACKEND},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SITE_URL = os.getenv("SITE_URL", "https://lvtd.dev").rstrip("/")

Q_CLUSTER = {
    "name": "lvtd",
    "workers": 2,
    "timeout": 60,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

MVP_DEPOSIT_CHECKOUT_URL = os.getenv("MVP_DEPOSIT_CHECKOUT_URL", "")
MVP_FINAL_PRICE = os.getenv("MVP_FINAL_PRICE", "$5,000")
MVP_DEPOSIT_AMOUNT = os.getenv("MVP_DEPOSIT_AMOUNT", "$100")
HOSTED_OPENCLAW_DEPOSIT_PRICE_ID = os.getenv(
    "HOSTED_OPENCLAW_DEPOSIT_PRICE_ID", "price_1T4NnYCsYtv9LQsDQKID7uRq"
)

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_CONTEXT_ACCOUNT = os.getenv("STRIPE_CONTEXT_ACCOUNT", "")
STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID = os.getenv("STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID", "")
STRIPE_MVP_DEPOSIT_FALLBACK_AMOUNT = int(
    os.getenv("STRIPE_MVP_DEPOSIT_FALLBACK_AMOUNT", "10000")
)

MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "")
MAILGUN_FROM_EMAIL = os.getenv("MAILGUN_FROM_EMAIL", "")
MAILGUN_REPLY_TO_EMAIL = os.getenv("MAILGUN_REPLY_TO_EMAIL", "")
