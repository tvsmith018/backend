# Secrets Rotation Checklist

Last reviewed: 2026-05-05

## Rotate immediately if previously committed

- `SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- database credentials
- Redis / broker credentials
- email provider credentials
- any private keys in `*.pem`

## Rotation process

1. Create replacement secrets in the provider dashboard.
2. Update Heroku config vars first.
3. Validate the app in production.
4. Remove old values from local `.env`.
5. Keep only placeholders in `.env.example`.
6. Never recommit live credentials.

## Rotation governance

- Cadence:
  - critical auth/payment secrets: every 90 days
  - infrastructure credentials (DB/Redis/email): every 180 days
- Trigger immediate rotation after any suspected leak or unauthorized access event.
- Record evidence for each rotation:
  - date/time
  - owner
  - systems rotated
  - rollback status
  - post-rotation validation result
