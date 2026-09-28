# Changelog

## 2026-09-28 — Native reasoning compatibility

- Map requested low effort to Mistral Medium 3.5's documented minimal mode, with effective request settings visible in answer details and public data.
- Classify reasoning-only length finishes as truncation, retaining charged usage and requiring explicit retry; preserve completed answers and frozen question profiles.


## 2026-09-28 — Benchmark results explorer

- Show five models per table with expand/collapse, sorting, and shaded numeric cells; remove eyebrow labels and the answer/judging coverage column.
- Add transparent value-v1 scoring from Elo and actual weighted answer cost, plus an accessible cost/quality plot and observed frontier.
- Publish a versioned, checksummed JSON evidence bundle and agent-readable methodology with explicit provenance and unknown-cost semantics.
- Add two idempotent practical question versions covering observational data analysis and source-grounded incident synthesis; preserve all existing results.


## 2026-09-28 - Jev benchmark launch study

- Publish a dated, illustrated study of 29 models and 1,624 Jev judgments, with task-level findings, saved-answer costs, and explicit methodology limits.
- Add a repository-owned rich article template while preserving escaped plain-text posts, seed publication metadata, and link the study from the benchmark and existing blog/home feeds.
- Make the repository-owned article body and slug read-only in admin with a clear PR editing path.
- Establish lightweight SEO voice, link, and private research-store pointers for future articles.

## 2026-09-28 - Durable benchmark jobs and real cost visibility

- Separate collected answers from fully judged coverage; show provider-reported saved-answer costs beside scores with explicit unknown/partial coverage.
- Persist attempt-level cost/audit history, safely backfill retained responses and historical snapshots, and keep completed outputs immutable during retries.
- Add a long-lived missing-work coordinator: overlap judging with generation, isolate blocked models, schedule bounded durable retries, recover interrupted calls as uncertain, and reserve OpenRouter credits before submission.
- Add a conservative $18 OpenRouter alert/pause threshold, administrative retry controls, and frozen per-question generation profiles.

## 2026-09-28 - Timed benchmark expansion

- Add 19 requested model variants and an equally weighted personal-advice question through an idempotent seed command.
- Add bounded parallel HTTP execution with main-thread database writes, lease heartbeat, fatal-error draining, UTC progress, and elapsed run timing.
- Support explicit first-attempt budget files and new-model budgets up to 65,536 tokens; preserve existing results and frozen inputs.

## 2026-09-28 - Reasoning headroom for explicit retries

- Permit an explicit retry ceiling of 65,536 tokens after production reasoning models exhausted 16,384; preserve default budgets and all successful work.

- Increase bounded ReviewGate review timeouts after repeated provider timeouts; review requirements and on-demand triggers are unchanged.

## 2026-09-27 - Explicit truncated-answer retries

- Add an opt-in bounded retry budget for answers truncated by reasoning/output
  token limits, retaining all completed answers and pairwise judgments.
- Show each answer's actual request budget rather than the model default.


## 2026-09-27 - Jev Benchmark

- Add a public Jev-judged model benchmark with per-question Elo, weighted overall
  rankings, coverage, full answers, decision probabilities, and methodology.
- Add admin-managed models/questions, immutable used inputs, persistent API audit
  records, resumable missing-work commands, unique pairs, and a runner lease.
- Seed ten OpenRouter models and three writing/programming/mathematics prompts;
  pin Jev 1.13.0 and keep all API calls behind an explicit management command.
- Add regression coverage for incremental runs, failures, ranking calculations,
  provider validation, HTML escaping, and admin permissions.
- Allow ReviewGate to publish its check result, preserving on-demand reruns.


## Unreleased

### Security

- Stripe webhook fulfillment now requires the exact configured Payment Link or Price ID,
  preventing unrelated products in the shared Stripe account from triggering emails.
- Stripe SDK webhook objects are normalized before product validation.
