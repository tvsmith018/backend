# Production Runbook

Last reviewed: 2026-05-07

## Before deploy

- Ensure Heroku config vars are set for secrets, database, Redis, email, Stripe, CORS, and CSRF origins.
- Confirm `DEBUG=0` in production.
- Confirm admin access is limited to active superusers only.
- Confirm `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` match the real frontend domains.
- Observability is required in production: set `SENTRY_ENABLED=1`, `SENTRY_DSN`, and an appropriate `SENTRY_TRACES_SAMPLE_RATE`.

## Verification after deploy

- Log in through the normal auth flow.
- Confirm `/authorized/me/` works for an authenticated user.
- Confirm `/admin/` only works for a superuser account.
- Confirm GraphiQL is not exposed in production.
- Confirm password reset OTP email tasks are being processed.
- Confirm Stripe webhook secret is present before testing payment webhooks.
- Review [BACKEND_PRODUCTION_VERIFICATION_2026-05-07.md](C:\Users\terrance\BigChiefEnt-Offical\backend\app\docs\BACKEND_PRODUCTION_VERIFICATION_2026-05-07.md) for the latest live-production verification notes and current operational caveats.

## Backup and restore drill (required)

- Define and track target `RPO` and `RTO` for production.
- Run a restore drill at least once per quarter against a non-production environment.
- Record drill date, owner, recovery duration, and any data integrity issues.
- If drill fails RPO/RTO targets, create a remediation ticket before next release.

## Safe change rules

- Schema changes should be applied separately against the live Heroku database.
- Run tests against `config.settings_test` before shipping backend changes.
- Rotate any secret immediately if it is ever committed or shared.
