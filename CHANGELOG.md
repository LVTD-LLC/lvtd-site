# Changelog

## Unreleased

### Security

- Stripe webhook fulfillment now requires the exact configured Payment Link or Price ID,
  preventing unrelated products in the shared Stripe account from triggering emails.
- Stripe SDK webhook objects are normalized before product validation.
