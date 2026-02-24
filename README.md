# LVTD Site

Minimal, production-ready Django org website with Tailwind CSS and background task support.

## Local setup

1. Install dependencies:

```bash
uv sync --extra dev
npm install
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
