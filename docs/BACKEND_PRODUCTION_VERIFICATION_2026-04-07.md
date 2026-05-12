# Backend Production Verification - April 17, 2026

This document records the live production checks and production-adjacent verification that were completed before frontend work continues against the backend contract.

It is intentionally honest about what was verified, what passed, and what is still an operational caveat.

This backend is also still actively evolving. The current grade and verification status reflect a strong working foundation, not a frozen system. Features, tests, and operational hardening are still being added continuously.

## Current grade

### Grade snapshot

`Overall | Security | Reliability | Testing | Confidence level`

`A- | A- | A | A- | High`

### Category breakdown

- Backend application design: `A`
- Backend security posture: `A-`
- Backend operational reliability: `A`
- Backend test maturity: `A-`
- Overall backend grade right now: `A-`

## Why the backend is graded `A-`

The backend is in a strong place:

- auth, GraphQL, REST, Channels, Celery, beat, payments, and email all work together in production
- recurring billing success, failure, retry, disable, and recovery behavior has been verified
- the automated backend test suite is passing (`42` tests currently in `config.settings_test`)
- the payment-specific test suite is passing with idempotency and recovery coverage
- the live production environment is stable in its current configuration

It is not a clean `A` yet because one infrastructure caveat remains:

- full Redis certificate verification with `REDIS_SSL_CERT_REQS=REQUIRED` caused `celery beat` to fail in production with `CERTIFICATE_VERIFY_FAILED` because of the current Redis certificate chain

The current stable production posture is:

- `CELERY_SSL_CERT_REQS=REQUIRED`
- `REDIS_SSL_CERT_REQS=NONE`

That keeps production working, but it is still a real operational note.

## Major backend work completed so far

The backend has moved well beyond an early prototype. The work completed so far includes:

- auth endpoints working with the frontend proxy flow
- GraphQL and REST running together in production
- Channels websocket support for comments and payment-status events
- Celery worker and beat handling background jobs in production
- password reset OTP generation and email task processing
- payment receipt and failed-payment email flows
- Stripe billing support for:
  - one-time payments
  - recurring payments
  - webhook handling
  - recurring retries and dunning
  - disable-after-three-failures behavior
  - recovery from disabled or failed recurring payment state
- billing state reflected explicitly in the database for:
  - `plan_disabled`
  - `plan_disabled_reason`
  - `plan_disabled_attempt_count`
  - `plan_disabled_at`
- stronger billing and idempotency tests
- production-safe runbooks and manual test documentation

## Ongoing development note

This backend should be understood as a live, production-capable foundation that is still being expanded.

Current reality:

- the backend is operational today
- major business flows are working today
- tests and production verification are in place today
- new features, stronger coverage, and more operational hardening will continue to be added over time

That is a healthy place for the project to be in. The system is not "done forever," but it is in a strong enough state to support continued frontend build-out and continued feature delivery.

## Automated tests run

These were run against the backend test settings:

- `pipenv run python manage.py test --settings=config.settings_test`

Result:

- `Ran 42 tests`
- `OK`

The payment-focused suite also passed after the billing hardening work:

- recurring disable after third failure
- recurring recovery back to healthy state
- webhook idempotency
- disabled subscription skip behavior

## Production checks completed

The following checks were run against the live production environment.

### Web / HTTP surface

- Live GraphQL HTTP probe:
  - `POST https://bigchiefnewz-a2e8434d1e6d.herokuapp.com/graphql/`
  - response: `200`
  - body included `{"data":{"__typename":"Query"}}`
- Live unauthenticated auth probe:
  - `GET https://bigchiefnewz-a2e8434d1e6d.herokuapp.com/authorized/me/`
  - response: `401`
  - body: `{"detail":"Authentication credentials were not provided."}`

What this means:

- the public web surface is responding correctly
- unauthenticated access is failing cleanly instead of crashing or returning a `500`

### Cache / Redis

A live cache round-trip was executed in production shell:

- `cache.set("live_healthcheck_cache_key", "ok", 60)`
- `cache.get("live_healthcheck_cache_key")`

Observed result:

- `{"cache_value": "ok"}`

What this means:

- the Django cache layer is live and writable in production

### Channels / websocket backend path

A live channel-layer send was executed in production shell:

- channel layer class reported as `RedisChannelLayer`
- `group_send("healthcheck_live_group", ...)` completed successfully

Observed result:

- `{"layer_class": "RedisChannelLayer"}`
- `{"channels_group_send": "ok"}`

What this means:

- the production channel layer is available
- Redis-backed group messaging is functioning

Note:

- this verified the backend Channels transport path
- it did not replay a full browser websocket handshake from the frontend during this pass

### Celery worker

Recent live worker logs showed:

- worker booted successfully
- broker connection succeeded
- tasks were received
- tasks completed successfully

A manual live task dispatch was also executed outside beat:

- `collect_due_recurring_payments.delay()`

Observed result:

- task id returned successfully
- worker received and completed the task
- recurring billing sweep completed with:
  - `processed=0`
  - `succeeded=0`
  - `failed=0`

What this means:

- Celery dispatch works from both beat and manual submission
- the worker is healthy in the current production configuration

### Beat / scheduler

Recent live beat logs showed:

- beat starts successfully
- due task `collect_due_recurring_payments` is sent
- worker receives and completes the scheduled task

What this means:

- scheduled task dispatch is working in the current production configuration

## Production billing flows already verified live

The payment system was tested against the live production database and Stripe test mode with production-side state changes.

Verified scenarios:

- one-time payment success
- one-time payment failure
- recurring initial success
- recurring third-failure disable behavior
- recurring recovery back to healthy state
- webhook idempotency for checkout completion
- webhook idempotency for failed payment handling
- disabled or unpaid subscriptions being skipped by the recurring sweep

Database state verified during these checks included:

- `Subscription.status`
- `cancel_at_period_end`
- `canceled_at`
- `plan_disabled`
- `plan_disabled_reason`
- `plan_disabled_attempt_count`
- `plan_disabled_at`

## Meaningful issue found

One meaningful issue remains, and it is operational rather than application-logic related.

### Redis certificate verification

When live production was configured with:

- `CELERY_SSL_CERT_REQS=REQUIRED`
- `REDIS_SSL_CERT_REQS=REQUIRED`

`celery beat` failed with:

- `CERTIFICATE_VERIFY_FAILED`
- `self-signed certificate in certificate chain`
- `celery.beat.SchedulingError`

To restore production stability, the live environment was returned to:

- `CELERY_SSL_CERT_REQS=REQUIRED`
- `REDIS_SSL_CERT_REQS=NONE`

This is the right working configuration for the current environment, but it is still an operational caveat to track.

## What was not fully verified in this pass

The following were not fully replayed end-to-end in this specific live verification pass:

- a browser-level websocket handshake from the frontend into the production socket endpoints
- inbox-side confirmation for every queued email in this exact run
- every single admin action and every single API route

That means the backend is strongly verified, but this document should not be read as "every possible production path was exercised."

## Recommendation before frontend build-out

The backend contract is strong enough to proceed with frontend work.

Recommended stance:

- proceed with frontend design and backend alignment
- keep the current live Redis SSL posture as-is for stability
- track the Redis certificate-chain issue as an infrastructure follow-up
- continue using the backend test suite plus targeted live verification when touching payments, auth, Channels, or Celery
