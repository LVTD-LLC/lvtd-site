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
- `SITE_URL`: canonical public origin used for canonical tags and sitemap URLs (default `https://lvtd.dev`).
- `SITE_LASTMOD`: ISO date used as the static page `lastmod` value in `sitemap.xml`.
- `CANONICAL_HOST_REDIRECT_ENABLED`: redirects non-canonical host/scheme requests to `SITE_URL` in production.
- `DJANGO_SECURE_HSTS_SECONDS`: HSTS max-age in seconds for production; lower this during HTTPS rollout if needed.
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`: set to `true` only when all subdomains support HTTPS.
- `DJANGO_SECURE_HSTS_PRELOAD`: set to `true` only when the domain is ready for HSTS preload requirements.
- `DATABASE_URL`: PostgreSQL connection string (defaults to local SQLite when unset).
- `MVP_DEPOSIT_CHECKOUT_URL`: Stripe checkout/payment link for the MVP deposit CTA.
- `MVP_DEPOSIT_AMOUNT`: display text for the deposit amount (default `$100`).
- `MVP_FINAL_PRICE`: display text for the final MVP service price (default `$5,000`).
- `HOSTED_OPENCLAW_DEPOSIT_PRICE_ID`: Stripe price id for Hosted OpenClaw $100 deposit checkout.
- `STRIPE_API_KEY`: Stripe secret API key used to retrieve events by id.
- `STRIPE_CONTEXT_ACCOUNT`: optional Stripe connected account id for event retrieval.
- `STRIPE_MVP_DEPOSIT_PAYMENT_LINK_ID`: payment link id to match for the MVP deposit.
- `MAILGUN_API_KEY`: Mailgun API key for outbound email.
- `MAILGUN_DOMAIN`: Mailgun sending domain (e.g. `mg.example.com`).
- `MAILGUN_FROM_EMAIL`: From address used in outbound emails.
- `MAILGUN_REPLY_TO_EMAIL`: Reply-To address for outbound emails.

## Stripe webhook

Create a webhook endpoint in Stripe that points to `/api/stripe/webhook` and listens for
`checkout.session.completed`. The handler retrieves the event from Stripe by id, then either:

- sends the MVP follow-up email for matching MVP deposit sessions, or
- sends the Hosted OpenClaw follow-up email for hosted deposit sessions created by this app.

Both flows require an exact product identifier: the configured Payment Link for MVP
deposits or the configured Price ID in Hosted OpenClaw checkout metadata. Amount-only
matching is intentionally not accepted because this Stripe account hosts several products.

## CI + deploy secrets

CI runs lint, tests, and Tailwind build.
`.github/workflows/reviewgate.yml` runs ReviewGate AI PR review for
in-repository pull requests when a PR opens, when a draft PR is marked ready for
review, or when a PR comment contains `@reviewgate review`. It intentionally
does not run on every new commit. It uses `LVTD-LLC/reviewgate@v0` so this
experimental install tracks the latest v0 action behavior. The workflow expects:

- `OPENROUTER_API_KEY`

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

## Jev Benchmark

The `jev_benchmark` Django app serves `/jev-benchmark` (the original
`/jev-benchamrk` spelling redirects). It stores one OpenRouter answer per active
model/question and one Jev decision per unordered answer pair. Admin supports
models, questions, positive question weights, and read-only answer/judgment audit
records. The question pages expose the exact prompts, answers, and probabilities.

### First run / adding entries

```bash
uv run python manage.py migrate
uv run python manage.py seed_jev_benchmark
uv run python manage.py run_jev_benchmark --dry-run
uv run python manage.py run_jev_benchmark --max-requests 165
```

The initial seed contains ten models from ten creators and three questions
(writing, programming, mathematics), selected against OpenRouter's catalogue on
2026-09-27. It does not overwrite admin changes. The initial run needs 30 answer
requests and 135 judgments. Add models or questions in admin, then rerun the
command: completed work is never intentionally regenerated. An eleventh model
adds three answers and thirty comparisons. Deactivating an entry removes it from
current rankings but retains its results. New answers and judgments immediately
appear on the public pages; do not enter confidential prompts.

Server-side environment:

- `OPENROUTER_JEVBENCHMARK_AI_API_KEY`: Infisical `Openclaw / prod /
  /projects/lvtd`, key of the same name.
- `TYPESAFE_API_KEY`: Infisical `Openclaw / prod / /services/typesafeai`.

Resolve/inject credentials through the deployment environment, never the admin or
browser. The runner requires both keys. No paid requests occur on page views,
admin saves, deploys, seeding, or dry runs. Running the management command is the
explicit spending action. It can be invoked manually in the deployed container
or by a separately configured scheduler; no schedule is installed automatically.
The existing django-q worker's 60-second timeout is too short for this full run,
so do not enqueue the entire command as a default worker job.

### Reproducibility and operations

- Questions pin Jev to `jev-1.13.0`, not the moving `jev-latest` alias. Requests,
  responses (including usage/provider metadata), latency, attempts, and completion
  times are persisted. A/B presentation is hash-assigned; model labels are omitted.
- Used prompt/rubric/judge and model ID/output budget cannot be edited through
  model saves/admin. Create a new question version for new semantics. Weight,
  display name, category, and activation edits do not cause inference.
- Elo starts at 1500, K=32, and replays each stored win/loss once in a stable hashed
  model-ID order. It is reproducible for the same data, not order-independent.
  Confidence does not change match weight. Overall ratings are weighted arithmetic
  means and require all active-question matchups to be complete for that model.
- One cross-process database lease protects paid work. It renews before each
  request and expires after 20 minutes if a process crashes. Do not manually clear
  it while a runner may still be active. Individual HTTP read timeout is 240s;
  retries for 429/503/529 are bounded to three attempts with capped backoff.
- `--max-requests` bounds logical jobs, not rate-limit retries or dollars. Provider
  pricing and reasoning defaults vary. Incomplete answers and malformed decisions
  are excluded, not counted as losses. Failed jobs are retried on the next run;
  nonzero command exit means inspect admin errors before retrying.
- Database uniqueness and the lease prevent normal duplicate runs, but an upstream
  response followed by a crash before the database save can still be billed twice
  on retry. No provider-side exactly-once guarantee is claimed. Network timeouts
  are not automatically retried.
- Back up the database before rollout, apply the additive `jev_benchmark` migration
  before serving the new routes, seed once, then run the benchmark. Rollback uses
  the previous application image; keep these additive tables and stored results.
  Never reverse/drop the migration to roll back application code.

This is an exploratory judge-preference benchmark, not a correctness certification.
Generated code is never executed and answer text is HTML-escaped. The methodology
page explicitly covers sample size, presentation bias, provider defaults, and
confidence interpretation.

API references: [TypeSafe HTTP API](https://docs.typesafe.ai/api),
[TypeSafe models](https://docs.typesafe.ai/models),
[OpenRouter model catalogue](https://openrouter.ai/api/v1/models).

### Retrying reasoning-token exhaustion

If an answer fails with OpenRouter `finish_reason=length` (including empty final
content when reasoning consumed the whole allowance), an operator can explicitly
raise the retry budget without editing frozen model inputs:

```bash
uv run python manage.py run_jev_benchmark --retry-max-tokens 16384
```

This applies only to failed, truncated answers. New answers and other failure
types retain the model's configured budget; completed answers and judgments are
never repeated. The override is bounded to 16,384 tokens and may increase API
cost. Each saved request records the actual budget, shown on its question page.
It does not automatically escalate budgets or promise a successful completion.
