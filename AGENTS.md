# AGENTS.md

## Scope

These are repository-wide instructions for AI coding agents working on
`lvtd-site`. Read the steering files before making substantial changes:

- `PRODUCT.md` for business, audience, offer, and positioning context.
- `VISION.md` for long-term direction.
- `TECH.md` for stack, commands, and integration constraints.
- `STRUCTURE.md` for where code and assets belong.
- `DESIGN.md` for interface, copy, and visual direction.

## Project Summary

`lvtd-site` is the public Django website for LVTD, LLC. It markets LVTD as a
product lab and an AI-native product engineering service, shows shipped projects,
publishes writing, and supports deposit-led service flows such as MVP builds and
Hosted OpenClaw.

The product direction is to lean into "agency as a service" and
"service-as-software": paid services delivered by an accountable engineer,
supported by reusable software, agent workflows, deployment patterns, and project
playbooks. Keep LVTD's active projects visible as proof, not as a distraction
from the service business.

## Working Rules

- Check `git status --short --branch` before editing so user changes are not
  accidentally overwritten.
- Prefer focused edits that match the existing Django, template, and Tailwind
  patterns.
- Do not rewrite unrelated files, generated CSS, lockfiles, migrations, or legal
  copy unless the task requires it.
- Use `rg` or `rg --files` for search.
- Use `uv run ...` for Python commands and the existing npm scripts for
  Tailwind.
- Keep code, templates, and copy ASCII unless a file already requires another
  character set.
- Never commit secrets. `.env` and `.env.*` are ignored and should stay local.

## Commands

Install dependencies:

```bash
uv sync --extra dev
npm install --include=dev
```

Run the app locally:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Run optional background workers:

```bash
uv run python manage.py qcluster
```

Build CSS after template class or stylesheet changes:

```bash
npm run build:css
```

Validate before handing off meaningful changes:

```bash
uv run ruff format --check
uv run ruff check
uv run python manage.py check
uv run pytest
```

Use `uv run ruff format` only when formatting Python files. For frontend changes,
also verify the relevant page in a browser when feasible.

## Product Guardrails

- Make LVTD's service offer concrete: who it helps, what LVTD handles, what the
  client receives, and how to start.
- Pair service claims with proof from shipped projects, writing, code, process,
  price/deposit signals, or operational details.
- Preserve the founder-builder voice. Write direct, specific copy.
- Avoid generic "AI agency", "digital transformation", "10x growth", and
  template consultancy language.
- Do not imply fully autonomous AI delivery. LVTD sells accountable engineering
  supported by software and agent workflows.
- Keep project listings credible. Do not add fake metrics, clients, logos, or
  links.

## Technical Guardrails

- Stripe and Mailgun code touches payment and customer communication paths. Add
  or update tests for changes there.
- Webhook handling must remain idempotent through `StripeWebhookEvent`.
- Do not expose `/api/`, checkout, or admin URLs in sitemap output.
- Keep `SITE_URL` as the source for canonical and sitemap origins.
- Static assets that are referenced by templates belong under `static/`.
- Source Tailwind input is `assets/css/app.css`; generated output is
  `static/css/app.css`.
- If models change, create migrations and include tests that cover the behavior.

## Review Expectations

Before finalizing, state what changed and what validation ran. If validation could
not run, say why. For copy-only steering changes, a syntax or test run is usually
not necessary, but still inspect the diff.
