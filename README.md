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
never repeated. The override is bounded to 65,536 tokens and may increase API
cost. Each saved request records the actual budget, shown on its question page.
It does not automatically escalate budgets or promise a successful completion.

If a response still exhausts 16,384 tokens, an operator may explicitly retry with
`--retry-max-tokens 65536`. Verify the provider supports that output allowance first.
This is not automatic escalation; the default generation allowance stays unchanged.

The effective truncated-retry allowance is the greatest of the model default,
the explicit flag, and the previous recorded request allowance. A lower flag
does not reduce an earlier larger allowance.

### Timed expansion and bounded concurrency

`expand_jev_benchmark` adds the dated 2026-09-28 manifest (19 models and a fictional
personal-advice question, weight 1). It makes no paid calls and refuses to overwrite
conflicting records. MiniMax's dated URL resolves to `minimax/minimax-m2.7:nitro`;
Nitro and free variants are preserved. Provider output limits were checked against
the OpenRouter catalog; Ling and GPT-OSS 20B are capped at 32,768, Hy4 at 64,000,
and the other listed budgets at 65,536 where supported.

```
uv run python manage.py expand_jev_benchmark
uv run python manage.py run_jev_benchmark --dry-run
uv run python manage.py run_jev_benchmark --workers 4 --max-requests 1575 \
  --budget-file jev_benchmark/data/budgets_20260928.json
```

The new cohort totals 116 answers and 1,624 comparisons. Starting with the original
30/135 completed results requires 86 new answers and 1,489 new comparisons.
The budget file affects first attempts only, is validated before paid calls, and
records actual allowances in each answer's request without mutating frozen model
inputs. Historical output budgets are not equal; see each saved request.

Concurrency defaults to 1, is explicitly bounded to 8, and applies only to HTTP
and response parsing. Database writes and progress reporting stay on the main
thread. The runner completes the answer phase before the judgment phase, renews
its lease every waiting interval (15 seconds), and stops scheduling on a fatal
account error while saving already-in-flight work. Up to the configured worker
count may already be billed when a fatal error is discovered. `--max-requests`
counts HTTP submissions. HTTP retries now live in the durable queue. UTC timestamps and
wall-clock elapsed seconds are printed; answer/comparison durations stay in DB.
Run under a durable operator process with private logs, not a short-lived web
request or the default 60-second task worker timeout. Admin requests do not call providers directly. When the durable worker below is
enabled, it discovers newly saved active models/questions and processes them.


### Durable worker, truthful coverage, and actual costs

Production worker command: `uv run python manage.py run_workers` (supervises
Django-Q plus the benchmark coordinator). Before enabling on an existing dataset:

```
uv run python manage.py migrate
uv run python manage.py backfill_jev_costs
uv run python manage.py work_jev_benchmark --workers 8  # one pass over due work
# or continuously discover admin additions and due retries:
uv run python manage.py work_jev_benchmark --watch --workers 8
```

The legacy `run_jev_benchmark` remains an explicit operator command. Only the
new durable worker does credit preflight, interleaving, and scheduled retries.
Do not run either concurrently; the shared DB lease rejects competing runners.
Quiesce paid work before deployment; allow a 30-minute container stop grace so
SIGTERM can drain in-flight work. The watcher never runs in a web request or a
60-second Django-Q job. No new deployment is needed for ordinary admin additions.

- Each new HTTP submission gets an attempt row before dispatch. Main-thread DB
  writes persist responses, reported costs, errors, and next retry time. A crash
  leaves an **uncertain** attempt; it is not blindly replayed.
- Capacity/rate-limit/budget failures get at most three attempts per retry cycle,
  with provider backoff (minimum 30s) and exponential cooldown. Blocked models do
  not stop other models. Account authentication failures pause that provider's
  work. Admin's explicit "Retry selected failed work" resets the retry cycle;
  it cannot regenerate completed work. Truncation/ambiguous outcomes need review.
- Ready comparisons run while other answers are generating. No successful answer
  or pair is regenerated. The original presentation identity and Elo stay intact.
- OpenRouter key spend and available credits are fetched before generation.
  Concurrent reservations use catalog prices and a conservative input/output
  allowance, **not** a claimed bill. Unaffordable jobs wait, while judging can
  continue. Unknown prices fail closed. `JEV_SPEND_ALERT_USD=18` pauses generation
  before approaching the user's $20 threshold. This is the dedicated key's
  cumulative OpenRouter usage, not combined vendor spend; Jev USD is unavailable.
  Budget state/alerts are visible in admin; the operator's scheduled spend alarm
  delivers a Slack alert. Provider prices/settlement can change; estimates are not
  a guaranteed invoice cap. Raising the threshold is an explicit operator change.
- New question versions can set an output ceiling and low/medium/high reasoning
  effort. Settings freeze after use. Existing question defaults and completed
  outputs are unchanged; providers may not support every reasoning setting.

Public coverage distinguishes **answers collected**, **matchups judged**, and
**fully judged questions**. Overall Elo remains withheld until coverage is complete.
Costs next to scores come only from `response.usage.cost` on saved successful
answers. Explicit zero is free; missing/malformed values are Unknown. Partial
cost totals show priced-answer coverage. They exclude retry and Jev charges.
There is deliberately no misleading Elo-per-dollar ratio (Elo is relative and
has an arbitrary baseline).

`WorkAttempt` retains every future attempt's provider-reported USD, including
failed responses when a cost is supplied, separately from the successful-answer
comparison. The idempotent backfill snapshots retained historical responses only;
earlier overwritten attempts are unknown, not zero. OpenRouter account usage may
therefore exceed the sum of public costs. No historical cost is inferred from
current price lists. Jev token usage is retained, but no USD price is invented.
