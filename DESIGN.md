# Design

## Scope

This file guides visual, UX, and copy decisions for AI-generated interface work
in `lvtd-site`.

## Design Direction

The site should feel like a practical, technical product studio: sharp, calm,
specific, and founder-friendly. It should not feel like a generic AI agency,
overbuilt SaaS landing page, or decorative portfolio.

Use the existing visual system unless the task explicitly asks for a redesign.

## Current Visual System

- Fonts: Geist for UI/body, Geist Mono for technical accents.
- Color tokens live in `assets/css/app.css` as `--lvtd-*` variables.
- The base palette is quiet neutral panels with a warm red accent, light/dark
  theme support, and a subtle grid background.
- Main layout width is constrained by `.site-container` and `.site-frame-inner`
  at `88rem`.
- Buttons use `.btn`, `.btn-primary`, and `.btn-secondary`.
- Cards and panels use existing classes such as `.surface-card`,
  `.surface-muted`, `.confidence-panel`, `project-card`, and `offer-card`.

## Layout Principles

- Build the actual useful page, not a generic landing-page shell.
- Preserve clear hierarchy: hero, proof, services, offer, process, writing, CTA.
- Keep each section focused on one job.
- Use cards for repeated items or real panels, not for every section.
- Do not nest cards inside cards.
- Avoid decorative gradient blobs, stock imagery, and visual filler.
- Keep text from colliding or overflowing on mobile. Prefer tighter copy over
  shrinking text with viewport units.
- Maintain the light/dark theme behavior.

## Copy Principles

- Write like a specific builder, not a committee.
- Prefer concrete nouns and verbs: deploy, integrate, monitor, debug, ship,
  reserve, start, ask.
- Tie claims to proof: projects, process, code, pricing, tools, operations, or
  examples.
- Keep AI language grounded in workflows and outcomes.
- Do not use vague phrases like "AI transformation", "unlock growth", "scale
  seamlessly", or "end-to-end solutions" unless backed by specific scope.
- Do not invent clients, metrics, testimonials, or guarantees.

## Component Guidance

Hero:

- Make LVTD's service/product-lab signal visible immediately.
- Keep the primary CTA practical: start a build, reserve, ask, or view work.
- Do not hide the conversion path behind abstract brand copy.

Project cards:

- Treat projects as proof of shipped capability.
- Keep metadata, project name, description, and tags scannable.
- Only link to real public destinations.
- Archived/private projects should not imply public availability.

Service and offer sections:

- State who the offer is for, what LVTD handles, what the customer gets, and how
  to start.
- Payment/deposit CTAs should be visually distinct and copy-clear.
- Managed-service copy should mention operations, security, monitoring,
  integrations, and iteration only when those are truly part of the offer.

Forms and checkout:

- Keep forms short.
- Make button copy explicit about the action and amount.
- Maintain CSRF tokens for Django POST forms.

Writing surfaces:

- Present writing as proof and working notes, not a content-marketing dump.
- Keep empty states useful and honest.

Legal pages:

- Keep them readable, restrained, and separate from marketing tone.

## Accessibility

- Preserve the skip link.
- Keep focus states visible.
- Maintain WCAG AA contrast targets.
- Use semantic headings in order.
- Provide useful alt text for meaningful images; decorative images should have
  empty alt text.
- Buttons must be real buttons for form actions and links for navigation.
- Do not rely on color alone to communicate state.

## Things To Avoid

- Generic agency pages with interchangeable service cards.
- Oversized hero copy inside cards.
- Decorative mock dashboards that do not represent real product behavior.
- One-note palettes that drown everything in a single hue.
- Dense uppercase labels everywhere.
- Fake "AI agent" UI chrome that does not help users understand the offer.
- Motion-heavy effects that distract from credibility.
