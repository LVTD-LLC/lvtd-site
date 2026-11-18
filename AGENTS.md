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

LVTD's public Django site is a directory of software, browser games, research,
and writing. Use the project registry and released game manifest as sources.
Keep client credits, archives, deep links, and legacy payment fulfillment intact.

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

`TECH.md` is the canonical source for install, run, CSS, and validation
commands. Use this quick path for normal local validation:

```bash
uv sync --extra dev
npm install --include=dev
uv run python manage.py migrate
npm run build:css
uv run ruff format --check
uv run ruff check
uv run python manage.py check
uv run pytest
```

For server, worker, watch-mode CSS, and environment setup commands, read
`TECH.md`.

Use `uv run ruff format` only when formatting Python files. For frontend changes,
also verify the relevant page in a browser when feasible.

## Product Guardrails

- Use one short description per project and clear links to the work and its source.
- Preserve attribution and archive status. Publish only real destinations.
- Keep the studio voice direct. Avoid promotional labels and sales calls to action.

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
