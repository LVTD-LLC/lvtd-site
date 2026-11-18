# Tech

## Scope

This file is the technical source of truth for agents working in `lvtd-site`.

## Stack

- Python 3.12.
- Django 6.0.2.
- `uv` for Python dependency management and command execution.
- Tailwind CSS 4 through `@tailwindcss/cli`.
- Node 20 in CI.
- SQLite by default locally, PostgreSQL through `DATABASE_URL` in deployed
  environments.
- WhiteNoise for static file serving.
- Gunicorn for production web serving.
- django-q2 for optional background workers.
- Stripe for legacy webhook-driven deposit follow-up.
- Mailgun for outbound follow-up emails.
- Plausible for analytics script loading in the base template.
- CapRover for deployment.

## Important Files

- `pyproject.toml`: Python dependencies, Ruff, and pytest config.
- `package.json`: Tailwind build and watch scripts.
- `config/settings.py`: environment-driven Django settings.
- `config/urls.py`: root URL includes `website.urls`.
- `website/views.py`: page views, sitemap/robots, legacy Stripe webhook, and
  Mailgun sending.
- `website/models.py`: `BlogPost` and `StripeWebhookEvent`.
- `website/templates/website/`: Django templates for the public site.
- `assets/css/app.css`: Tailwind input and source design system.
- `static/css/app.css`: generated CSS output used by Django.
- `.github/workflows/ci.yml`: CI checks.
- `.github/workflows/deploy.yml`: CapRover deployment.

## Commands

Install:

```bash
uv sync --extra dev
npm install --include=dev
```

Run locally:

```bash
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py runserver
```

Optional worker:

```bash
uv run python manage.py qcluster
```

CSS:

```bash
npm run build:css
npm run watch:css
```

Validation:

```bash
uv run ruff format --check
uv run ruff check
uv run python manage.py check
uv run pytest
```

## Environment

Required production settings come from environment variables. Important groups:

- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `DATABASE_URL`.
- Historical deposit fulfillment: `MVP_FINAL_PRICE`, `STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID`,
  and `HOSTED_OPENCLAW_DEPOSIT_PRICE_ID` identify or describe past purchases.
- Stripe: `STRIPE_API_KEY`, `STRIPE_CONTEXT_ACCOUNT`.
- Mailgun: `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_FROM_EMAIL`,
  `MAILGUN_REPLY_TO_EMAIL`.

Do not hard-code production secrets or customer data.

## Backend Conventions

- Keep views small and explicit. This project currently favors class-based
  template/list/detail views plus simple function views for endpoints.
- Keep public pages in the `website` app unless the repo grows enough to justify
  another app.
- Use Django settings for environment-dependent values.
- Preserve webhook idempotency by recording processed Stripe event ids in
  `StripeWebhookEvent`.
- For external requests, keep timeouts explicit.
- When adding models, add migrations and tests.

## Frontend Conventions

- Templates are server-rendered Django templates.
- Tailwind utility classes are used in templates, while reusable component styles
  and tokens live in `assets/css/app.css`.
- Build CSS with `npm run build:css` after changing template classes or
  `assets/css/app.css`.
- Do not hand-edit `static/css/app.css` for source changes. It is generated from
  `assets/css/app.css`.
- Keep theme behavior in `base.html` consistent with the light/dark tokens.

## SEO And Public Endpoints

- Canonical URLs and sitemap URLs use `SITE_URL`.
- `robots.txt` should continue to disallow `/admin/`, `/api/`, and checkout-only
  paths.
- Sitemap output should include public indexable pages and published blog posts
  only.
- Page-specific structured data should remain valid JSON-LD.

## Testing Guidance

- Add tests for page rendering, URLs, SEO metadata, and copy that drives key
  offers.
- Add tests for payment, webhook, Mailgun, sitemap, and robots behavior whenever
  those paths change.
- Use mocks for Stripe and Mailgun. Do not hit real external services in tests.

## Games on the main domain

The Django /games/ page reads the games app's deployed registry through
GAMES_MANIFEST_URL. Each worker refreshes its copy every 30 seconds and keeps
the previous release during short outages. The routing middleware reserves
Django's top-level URL namespaces and selects the internal Nginx location in
ops/games-location.conf for registered games, their shared assets, and the
three existing game API namespaces. Include that location in the lvtd-site
CapRover server block. Nginx streams the original request and response.
New games use URLs below their slug and require only a games-repo release.
