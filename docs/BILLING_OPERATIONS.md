# Billing Operations

Last reviewed: 2026-05-05

This backend can now be operated without the frontend for the most important billing support flows.

## Daily recurring collection

- Celery beat runs `payments.tasks.collect_due_recurring_payments` every day at `00:01` server time.
- Recurring subscriptions are charged only when `current_period_end <= now`.
- Successful recurring charges advance the next due date by 30 days.

## Dunning behavior

- Failed recurring charges move the subscription to `past_due`.
- The backend stores:
  - `dunning_attempt_count`
  - `next_retry_at`
  - `last_dunning_error`
- After the configured max failure count, the subscription becomes `unpaid` and is marked `cancel_at_period_end=True`.

Environment controls:

- `BILLING_TIME_ZONE`
- `BILLING_DUNNING_RETRY_DAYS`
- `BILLING_DUNNING_MAX_FAILURES`

## Admin recovery tools

In Django admin:

- `Subscription` has a `Retry recurring charge for selected subscriptions` action.
- `PaymentRecord` has:
  - `Queue success receipt email`
  - `Queue failed payment email`

## Reconciliation report

Run:

```powershell
pipenv run python manage.py billing_reconciliation_report --days 30
```

The report includes:

- active subscriptions
- past due subscriptions
- unpaid subscriptions
- subscriptions already scheduled for retry
- subscriptions currently due now
- payment totals grouped by status

## Recommended backend-only validation

1. Create a recurring subscription in Stripe test mode.
2. Force `current_period_end` into the past for that subscription.
3. Run the recurring collector manually.
4. Confirm the correct payment record, email, and admin state changes.
