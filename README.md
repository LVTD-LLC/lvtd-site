# LVTD Site

Minimal, production-ready Django org website with Tailwind CSS and background task support.

## Local setup

1. Install dependencies:

```bash
uv sync --extra dev
npm install --include=dev
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Build Tailwind CSS:

```bash
npm run build:css
```

Tailwind output lives at `static/css/app.css`. Run the build command to regenerate it after changes.

4. Run database migrations:

```bash
uv run python manage.py migrate
```

5. Start the server:

```bash
uv run python manage.py runserver
```

Optional Q cluster worker:

```bash
uv run python manage.py qcluster
```

## Environment variables

- `DJANGO_SECRET_KEY`: required in production.
- `DJANGO_DEBUG`: set to `true` for local debug.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated origins.
- `DATABASE_URL`: PostgreSQL connection string (defaults to local SQLite when unset).
- `MVP_DEPOSIT_CHECKOUT_URL`: Stripe checkout/payment link for the MVP deposit CTA.
- `MVP_DEPOSIT_AMOUNT`: display text for the deposit amount (default `$100`).
- `MVP_FINAL_PRICE`: display text for the final MVP service price (default `$5,000`).
- `STRIPE_API_KEY`: Stripe secret API key used to retrieve events by id.
- `STRIPE_CONTEXT_ACCOUNT`: optional Stripe connected account id for event retrieval.
- `STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID`: payment link id to match for the MVP deposit.
- `STRIPE_MVP_DEPOSIT_FALLBACK_AMOUNT`: amount in cents to match when no payment link id is set.
- `MAILGUN_API_KEY`: Mailgun API key for outbound email.
- `MAILGUN_DOMAIN`: Mailgun sending domain (e.g. `mg.example.com`).
- `MAILGUN_FROM_EMAIL`: From address used in outbound emails.
- `MAILGUN_REPLY_TO_EMAIL`: Reply-To address for outbound emails.

## Stripe webhook

Create a webhook endpoint in Stripe that points to `/api/stripe/webhook` and listens for
`checkout.session.completed`. The handler retrieves the event from Stripe by id, validates
it against the MVP deposit payment link (or fallback amount), and sends a Mailgun follow-up
email to the buyer.

## CI + deploy secrets

CI runs lint, tests, and Tailwind build.

CapRover deploy workflow expects:

- `CAPROVER_SERVER`
- `CAPROVER_APP`
- `CAPROVER_TOKEN`
- `CAPROVER_BRANCH` (optional, default `main`)

## Commands

```bash
uv run ruff format
uv run ruff check
uv run python manage.py check
uv run pytest
```
