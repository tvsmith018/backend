# Manual Payment Test Sheet

Last reviewed: 2026-05-05

Use this exactly. Replace the placeholders once, then run top to bottom.

## Setup

Fill these in first:

```text
DOMAIN=<https://your-backend-domain.com>
FRONTEND_RETURN_URL=<https://your-frontend.com/payments/return>
TEST_EMAIL=<paytest@example.com>
TEST_PASSWORD=<Password123!>
ONE_TIME_LOOKUP_KEY=<your_one_time_lookup_key>
RECURRING_LOOKUP_KEY=<your_recurring_lookup_key>
```

## 1. Signup

```bash
curl -X POST <DOMAIN>/authorized/signup/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"<TEST_EMAIL>\",\"firstname\":\"Pay\",\"lastname\":\"Tester\",\"dob\":\"2000-01-01\",\"password\":\"<TEST_PASSWORD>\"}"
```

Expected:
- `201`
- success message

## 2. Login

```bash
curl -X POST <DOMAIN>/authorized/login/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"<TEST_EMAIL>\",\"password\":\"<TEST_PASSWORD>\"}"
```

Save:
- `ACCESS_TOKEN=<paste access>`
- `REFRESH_TOKEN=<paste refresh>`

## 3. Me

```bash
curl -X GET <DOMAIN>/authorized/me/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Expected:
- `200`
- user info returned

## 4. Payment Websocket

Connect this in a browser or websocket client:

```text
wss://<your-backend-host-without-https>/ws/payments/?token=<ACCESS_TOKEN>
```

If local non-SSL:

```text
ws://localhost:8000/ws/payments/?token=<ACCESS_TOKEN>
```

Expected first message:

```json
{"type":"connection.ready","message":"Payment event stream connected."}
```

## 5. One-Time Checkout Session

```bash
curl -X POST <DOMAIN>/payments/one-time/checkout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"price_lookup_key\":\"<ONE_TIME_LOOKUP_KEY>\",\"return_url\":\"<FRONTEND_RETURN_URL>\"}"
```

Save:
- `ONE_TIME_SESSION_ID=<paste session_id>`
- `ONE_TIME_CLIENT_SECRET=<paste client_secret>`

Expected:
- `201`

## 6. One-Time Stripe Test

In the frontend or browser:
- use `ONE_TIME_CLIENT_SECRET`
- pay with success card: `4242 4242 4242 4242`
- use any future expiry and any valid CVC/ZIP

Expected:
- websocket success event
- `CheckoutSession` complete
- `PaymentRecord` succeeded
- receipt email sent

## 7. One-Time Status Check

```bash
curl -X POST <DOMAIN>/payments/checkout/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"session_id\":\"<ONE_TIME_SESSION_ID>\"}"
```

Expected:
- `status` should become `complete`

## 8. Recurring Checkout Session

```bash
curl -X POST <DOMAIN>/payments/recurring/checkout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"price_lookup_key\":\"<RECURRING_LOOKUP_KEY>\",\"return_url\":\"<FRONTEND_RETURN_URL>\"}"
```

Save:
- `RECURRING_SESSION_ID=<paste session_id>`
- `RECURRING_CLIENT_SECRET=<paste client_secret>`

Expected:
- `201`

## 9. Recurring Stripe Test

In the frontend or browser:
- use `RECURRING_CLIENT_SECRET`
- pay with success card: `4242 4242 4242 4242`

Expected:
- websocket recurring success event
- `Subscription` created
- `PaymentMethod` created
- initial recurring `PaymentRecord` succeeded
- receipt email sent

## 10. Recurring Status Check

```bash
curl -X POST <DOMAIN>/payments/checkout/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"session_id\":\"<RECURRING_SESSION_ID>\"}"
```

## 11. Failure Card Test

Create another one-time checkout:

```bash
curl -X POST <DOMAIN>/payments/one-time/checkout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"price_lookup_key\":\"<ONE_TIME_LOOKUP_KEY>\",\"return_url\":\"<FRONTEND_RETURN_URL>\"}"
```

In the frontend or browser use one of these:
- insufficient funds: `4000 0000 0000 9995`
- decline: `4000 0000 0000 0002`
- expired: `4000 0000 0000 0069`

Expected:
- failure event or failed checkout path
- failed payment email if backend records failure

## 12. Force Recurring Due

In Django admin:
- open the user’s `Subscription`
- set `current_period_end` to a past timestamp
- save

## 13. Run Recurring Collection Manually

```bash
pipenv run python manage.py shell
```

Then paste:

```python
from payments.tasks import collect_due_recurring_payments
collect_due_recurring_payments.apply()
```

Expected success path:
- new recurring `PaymentRecord`
- `current_period_end` moved forward 30 days
- receipt email sent

Expected failure path:
- `Subscription.status = past_due`
- failed `PaymentRecord`
- failed payment email sent
- websocket failure event

## 14. Logout

```bash
curl -X POST <DOMAIN>/authorized/logout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d "{\"refresh\":\"<REFRESH_TOKEN>\"}"
```

## 15. What To Check In Admin

Verify these:
- `BillingCustomer`
- `PaymentMethod`
- `CheckoutSession`
- `PaymentRecord`
- `Subscription`
- `WebhookEvent`

## 16. What To Check In Email

Success email:
- subject like `Big Chief Receipt`

Failure email:
- subject like `Big Chief Payment Failed`

## 17. Stripe Test Cards

Success:

```text
4242 4242 4242 4242
```

Insufficient funds:

```text
4000 0000 0000 9995
```

Declined:

```text
4000 0000 0000 0002
```

Expired:

```text
4000 0000 0000 0069
```
