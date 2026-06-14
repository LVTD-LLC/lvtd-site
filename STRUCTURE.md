# Structure

## Scope

This file explains where things belong in `lvtd-site`.

## Directory Map

```text
.
|-- AGENTS.md
|-- CLAUDE.md
|-- GEMINI.md
|-- PRODUCT.md
|-- VISION.md
|-- TECH.md
|-- STRUCTURE.md
|-- DESIGN.md
|-- README.md
|-- pyproject.toml
|-- package.json
|-- Dockerfile
|-- captain-definition
|-- assets/
|   `-- css/
|       `-- app.css
|-- config/
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- static/
|   |-- css/
|   |   `-- app.css
|   |-- fonts/
|   `-- images/
|       |-- brand/
|       `-- logos/
|-- website/
|   |-- models.py
|   |-- views.py
|   |-- urls.py
|   |-- context_processors.py
|   |-- tests.py
|   |-- migrations/
|   `-- templates/
|       `-- website/
|-- .github/
|   |-- copilot-instructions.md
|   `-- workflows/
`-- uv.lock
```

## Placement Rules

- Public page templates belong in `website/templates/website/`.
- Public page routes belong in `website/urls.py`.
- Page views, sitemap, robots, checkout, and webhook code currently live in
  `website/views.py`.
- Site-wide SEO context belongs in `website/context_processors.py`.
- Data models belong in `website/models.py`.
- Tests currently live in `website/tests.py`; keep related tests close together.
- Source CSS belongs in `assets/css/app.css`.
- Generated CSS belongs in `static/css/app.css` and should be regenerated with
  `npm run build:css`.
- Static images referenced by templates belong under `static/images/`.
- Brand images belong under `static/images/brand/`.
- Project logos belong under `static/images/logos/`.
- CI and deploy workflow files belong under `.github/workflows/`.
- Repo steering files belong at the root so multiple agents can find them, except
  `.github/copilot-instructions.md`, which GitHub Copilot requires under
  `.github/`.

## Template Organization

- `base.html` owns the document shell, metadata defaults, navigation, theme
  toggle, Plausible script, footer, and block definitions.
- `home.html` owns the main LVTD homepage, project proof, service offer cards,
  process, writing preview, and closing CTA.
- `hosted_openclaw.html` owns the service detail page for Hosted OpenClaw.
- `blog_list.html` and `blog_detail.html` own public writing pages.
- `terms.html` and `privacy.html` own legal copy.

When adding a new service page, create a dedicated template, route, view class,
metadata blocks, structured data where useful, tests, and sitemap entry if it is
public and indexable.

## Import And Dependency Rules

- Keep project imports explicit.
- Do not introduce a new frontend build framework. The current frontend is
  Django templates plus Tailwind.
- Do not introduce a new Python web framework or task queue without a strong
  reason.
- Use existing dependencies before adding new packages.
- If a new package is needed, update the appropriate lockfile and explain why.

## Boundaries

- `config/` should stay framework configuration, not product logic.
- `website/` owns public site behavior.
- Payment and email integration code should stay testable and avoid global side
  effects beyond settings-driven configuration.
- Static generated output should not become the source of truth.
- Legal pages should be edited carefully and only for requested content changes.

## New Feature Checklist

For a new public service or product page:

1. Add or update product context in `PRODUCT.md` if the positioning changes.
2. Add a template under `website/templates/website/`.
3. Add a view in `website/views.py`.
4. Add a route in `website/urls.py`.
5. Add metadata and structured data where appropriate.
6. Add tests in `website/tests.py`.
7. Add a sitemap entry if the page should be indexed.
8. Update navigation only if the page is a primary surface.
9. Run the relevant Django and CSS checks.
