# Changelog

## 2026-09-27 - Jev Benchmark

- Add a public Jev-judged model benchmark with per-question Elo, weighted overall
  rankings, coverage, full answers, decision probabilities, and methodology.
- Add admin-managed models/questions, immutable used inputs, persistent API audit
  records, resumable missing-work commands, unique pairs, and a runner lease.
- Seed ten OpenRouter models and three writing/programming/mathematics prompts;
  pin Jev 1.13.0 and keep all API calls behind an explicit management command.
- Add regression coverage for incremental runs, failures, ranking calculations,
  provider validation, HTML escaping, and admin permissions.
- Allow ReviewGate to publish its check result and rerun on updated PR commits.


## Unreleased

### Security

- Stripe webhook fulfillment now requires the exact configured Payment Link or Price ID,
  preventing unrelated products in the shared Stripe account from triggering emails.
- Stripe SDK webhook objects are normalized before product validation.
