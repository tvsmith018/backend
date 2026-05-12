from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
import stripe

from payments.models import (
    BillingCustomer,
    BillingPrice,
    BillingProduct,
    CheckoutSession,
    PaymentMethod,
    PaymentRecord,
    Subscription,
    WebhookEvent,
)
from payments.services.stripe_service import StripeService
from payments.services.stripe_service import PaymentProcessingError


User = get_user_model()
CardError = stripe.error.CardError


class StripeServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="billing@example.com",
            firstname="Billing",
            lastname="User",
            password="Password123!",
            dob=date(2001, 3, 3),
            bio="bio",
        )
        self.customer = BillingCustomer.objects.create(
            user=self.user,
            provider=BillingCustomer.Provider.STRIPE,
            provider_customer_id="cus_123",
            email=self.user.email,
        )
        self.one_time_product = BillingProduct.objects.create(
            name="Single Drop",
            code="single-drop",
            provider_product_id="prod_single",
            product_type=BillingProduct.ProductType.ONE_TIME,
        )
        self.one_time_price = BillingPrice.objects.create(
            product=self.one_time_product,
            lookup_key="single_drop",
            provider_price_id="price_single",
            price_type=BillingPrice.PriceType.ONE_TIME,
            unit_amount=2500,
        )
        self.recurring_product = BillingProduct.objects.create(
            name="VIP Access",
            code="vip-access",
            provider_product_id="prod_vip",
            product_type=BillingProduct.ProductType.SUBSCRIPTION,
        )
        self.recurring_price = BillingPrice.objects.create(
            product=self.recurring_product,
            lookup_key="vip_30_day",
            provider_price_id="price_vip",
            price_type=BillingPrice.PriceType.RECURRING,
            unit_amount=1500,
            recurring_interval=BillingPrice.Interval.MONTH,
        )

    @patch("payments.services.stripe_service.stripe.PaymentIntent.retrieve")
    @patch("payments.services.stripe_service.stripe.PaymentMethod.retrieve")
    def test_handle_recurring_checkout_completion_creates_subscription(
        self,
        retrieve_payment_method,
        retrieve_payment_intent,
    ):
        checkout = CheckoutSession.objects.create(
            customer=self.customer,
            price=self.recurring_price,
            provider_checkout_session_id="cs_recurring",
            metadata={"payment_kind": "recurring"},
        )
        retrieve_payment_intent.return_value = {
            "id": "pi_initial",
            "payment_method": "pm_123",
        }
        retrieve_payment_method.return_value = {
            "id": "pm_123",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2030,
            },
            "metadata": {"origin": "checkout"},
        }

        StripeService.handle_event(
            {
                "id": "evt_checkout_complete",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_recurring",
                        "payment_intent": "pi_initial",
                        "amount_total": 1500,
                        "currency": "usd",
                        "metadata": {
                            "payment_kind": "recurring",
                            "price_lookup_key": "vip_30_day",
                            "user_id": str(self.user.id),
                        },
                    }
                },
            }
        )

        checkout.refresh_from_db()
        subscription = Subscription.objects.get(
            provider_subscription_id="manual_cs_recurring"
        )
        payment_method = PaymentMethod.objects.get(provider_payment_method_id="pm_123")
        payment = PaymentRecord.objects.get(provider_payment_intent_id="pi_initial")

        self.assertEqual(checkout.status, CheckoutSession.Status.COMPLETE)
        self.assertEqual(subscription.customer, self.customer)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(payment_method.customer, self.customer)
        self.assertTrue(payment_method.is_default)
        self.assertEqual(payment.subscription, subscription)

    def test_handle_one_time_checkout_completion_creates_payment_record(self):
        checkout = CheckoutSession.objects.create(
            customer=self.customer,
            price=self.one_time_price,
            provider_checkout_session_id="cs_one_time",
            metadata={"payment_kind": "one_time"},
        )

        StripeService.handle_event(
            {
                "id": "evt_checkout_one_time",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_one_time",
                        "payment_intent": "pi_one_time",
                        "amount_total": 2500,
                        "currency": "usd",
                        "metadata": {
                            "payment_kind": "one_time",
                            "price_lookup_key": "single_drop",
                            "user_id": str(self.user.id),
                        },
                    }
                },
            }
        )

        checkout.refresh_from_db()
        payment = PaymentRecord.objects.get(provider_payment_intent_id="pi_one_time")

        self.assertEqual(checkout.status, CheckoutSession.Status.COMPLETE)
        self.assertEqual(payment.subscription, None)
        self.assertEqual(payment.amount, 2500)
        self.assertEqual(payment.status, PaymentRecord.Status.SUCCEEDED)

    def test_create_recurring_checkout_session_blocks_second_open_subscription(self):
        Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_existing_subscription",
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
            started_at=timezone.now() - timedelta(days=5),
        )

        with self.assertRaises(PaymentProcessingError) as exc:
            StripeService.create_recurring_checkout_session(
                self.user,
                "vip_30_day",
                "https://example.com/return",
            )

        self.assertEqual(exc.exception.code, "subscription_already_exists")
        self.assertEqual(exc.exception.status_code, 409)

    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_subscription_payment_advances_due_date(self, create_payment_intent):
        payment_method = PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_due",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030,
            is_default=True,
        )
        due_now = timezone.now()
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_due",
            status=Subscription.Status.ACTIVE,
            current_period_start=due_now - timedelta(days=30),
            current_period_end=due_now,
            started_at=due_now - timedelta(days=30),
            metadata={"billing_engine": "celery_manual_recurring"},
        )
        create_payment_intent.return_value = {
            "id": "pi_cycle",
            "amount": 1500,
            "currency": "usd",
        }

        StripeService.collect_subscription_payment(subscription)

        subscription.refresh_from_db()
        payment = PaymentRecord.objects.get(provider_payment_intent_id="pi_cycle")

        self.assertEqual(payment.subscription, subscription)
        self.assertEqual(payment.status, PaymentRecord.Status.SUCCEEDED)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(
            subscription.current_period_end,
            due_now + timedelta(days=30),
        )

    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_due_recurring_payments_marks_card_errors_past_due(self, create_payment_intent):
        PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_fail",
            brand="visa",
            last4="4000",
            exp_month=1,
            exp_year=2031,
            is_default=True,
        )
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_fail",
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(minutes=1),
            started_at=timezone.now() - timedelta(days=30),
            metadata={"billing_engine": "celery_manual_recurring"},
        )
        create_payment_intent.side_effect = CardError(
            message="Insufficient funds.",
            param="payment_method",
            code="insufficient_funds",
            json_body={"error": {"message": "Insufficient funds."}},
        )

        summary = StripeService.collect_due_recurring_payments()

        subscription.refresh_from_db()
        failure_record = PaymentRecord.objects.filter(subscription=subscription).latest("created_at")

        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(subscription.status, Subscription.Status.PAST_DUE)
        self.assertEqual(failure_record.status, PaymentRecord.Status.FAILED)
        self.assertEqual(
            failure_record.metadata["error_code"],
            "insufficient_funds",
        )
        self.assertEqual(
            subscription.metadata["dunning_attempt_count"],
            1,
        )
        self.assertIn("next_retry_at", subscription.metadata)

    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_due_recurring_payments_skips_until_next_retry_at(self, create_payment_intent):
        PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_future_retry",
            brand="visa",
            last4="4242",
            exp_month=1,
            exp_year=2031,
            is_default=True,
        )
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_future_retry",
            status=Subscription.Status.PAST_DUE,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(minutes=1),
            started_at=timezone.now() - timedelta(days=30),
            metadata={
                "billing_engine": "celery_manual_recurring",
                "next_retry_at": (timezone.now() + timedelta(hours=6)).isoformat(),
                "dunning_attempt_count": 1,
            },
        )

        summary = StripeService.collect_due_recurring_payments()

        subscription.refresh_from_db()
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["succeeded"], 0)
        self.assertEqual(subscription.status, Subscription.Status.PAST_DUE)
        create_payment_intent.assert_not_called()

    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_due_recurring_payments_disables_plan_after_third_failure(self, create_payment_intent):
        PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_disable_plan",
            brand="visa",
            last4="4000",
            exp_month=1,
            exp_year=2031,
            is_default=True,
        )
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_disable_plan",
            status=Subscription.Status.PAST_DUE,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(minutes=1),
            started_at=timezone.now() - timedelta(days=30),
            metadata={
                "billing_engine": "celery_manual_recurring",
                "dunning_attempt_count": 2,
            },
        )
        create_payment_intent.side_effect = CardError(
            message="Insufficient funds.",
            param="payment_method",
            code="insufficient_funds",
            json_body={"error": {"message": "Insufficient funds."}},
        )

        summary = StripeService.collect_due_recurring_payments()

        subscription.refresh_from_db()
        failure_record = PaymentRecord.objects.filter(subscription=subscription).latest("created_at")

        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(subscription.status, Subscription.Status.UNPAID)
        self.assertTrue(subscription.cancel_at_period_end)
        self.assertIsNotNone(subscription.canceled_at)
        self.assertTrue(subscription.plan_disabled)
        self.assertEqual(subscription.plan_disabled_reason, "max_payment_failures")
        self.assertEqual(subscription.plan_disabled_attempt_count, 3)
        self.assertIsNotNone(subscription.plan_disabled_at)
        self.assertTrue(subscription.metadata["plan_disabled"])
        self.assertEqual(subscription.metadata["plan_disabled_reason"], "max_payment_failures")
        self.assertEqual(subscription.metadata["plan_disabled_attempt_count"], 3)
        self.assertIsNone(subscription.metadata["next_retry_at"])
        self.assertEqual(subscription.metadata["dunning_attempt_count"], 3)
        self.assertEqual(failure_record.status, PaymentRecord.Status.FAILED)

    @patch("payments.services.stripe_service.StripeService._publish_payment_event")
    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_subscription_payment_uses_idempotency_and_resets_dunning_state(
        self,
        create_payment_intent,
        publish_payment_event,
    ):
        PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_reset",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030,
            is_default=True,
        )
        due_now = timezone.now()
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_dunning_reset",
            status=Subscription.Status.PAST_DUE,
            current_period_start=due_now - timedelta(days=30),
            current_period_end=due_now,
            started_at=due_now - timedelta(days=30),
            metadata={
                "dunning_attempt_count": 2,
                "next_retry_at": (due_now + timedelta(hours=1)).isoformat(),
                "last_dunning_error": {"code": "processing_error"},
            },
        )
        create_payment_intent.return_value = {
            "id": "pi_reset",
            "amount": 1500,
            "currency": "usd",
        }

        StripeService.collect_subscription_payment(subscription)

        subscription.refresh_from_db()
        self.assertEqual(subscription.metadata["dunning_attempt_count"], 0)
        self.assertIsNone(subscription.metadata["next_retry_at"])
        self.assertIsNone(subscription.metadata["last_dunning_error"])
        _, kwargs = create_payment_intent.call_args
        self.assertIn("idempotency_key", kwargs)
        self.assertTrue(kwargs["idempotency_key"].startswith("subscription-charge:"))
        publish_payment_event.assert_called_once()

    def test_billing_reconciliation_report_includes_retry_and_due_counts(self):
        PaymentRecord.objects.create(
            customer=self.customer,
            amount=2500,
            currency="usd",
            status=PaymentRecord.Status.SUCCEEDED,
            provider_payment_intent_id="pi_report_success",
        )
        Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_report_due",
            status=Subscription.Status.PAST_DUE,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(minutes=5),
            metadata={"next_retry_at": (timezone.now() + timedelta(hours=4)).isoformat()},
        )

        output = StringIO()
        call_command("billing_reconciliation_report", stdout=output)
        report = output.getvalue()

        self.assertIn("Billing Reconciliation Report", report)
        self.assertIn("Billing timezone:", report)
        self.assertIn("Scheduled for retry: 1", report)
        self.assertIn("Currently due now: 1", report)

    def test_handle_event_is_idempotent_for_processed_webhook(self):
        WebhookEvent.objects.create(
            provider_event_id="evt_done",
            event_type="checkout.session.completed",
            processed=True,
            payload={"id": "evt_done"},
        )

        StripeService.handle_event(
            {
                "id": "evt_done",
                "type": "checkout.session.completed",
                "data": {"object": {"id": "ignored"}},
            }
        )

        self.assertEqual(PaymentRecord.objects.count(), 0)

    @override_settings(STRIPE_WEBHOOK_TOLERANCE_SECONDS=120)
    @patch("payments.services.stripe_service.stripe.Webhook.construct_event")
    def test_construct_webhook_event_uses_tolerance_setting(self, construct_event):
        construct_event.return_value = {"id": "evt_test"}
        StripeService.construct_webhook_event(b"{}", "sig")
        _, kwargs = construct_event.call_args
        self.assertEqual(kwargs["tolerance"], 120)

    def test_handle_checkout_completed_is_idempotent_for_same_event(self):
        CheckoutSession.objects.create(
            customer=self.customer,
            price=self.one_time_price,
            provider_checkout_session_id="cs_idempotent_checkout",
            metadata={"payment_kind": "one_time"},
        )
        event = {
            "id": "evt_idempotent_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_idempotent_checkout",
                    "payment_intent": "pi_idempotent_checkout",
                    "amount_total": 2500,
                    "currency": "usd",
                    "metadata": {
                        "payment_kind": "one_time",
                        "price_lookup_key": "single_drop",
                        "user_id": str(self.user.id),
                    },
                }
            },
        }

        StripeService.handle_event(event)
        StripeService.handle_event(event)

        self.assertEqual(
            PaymentRecord.objects.filter(provider_payment_intent_id="pi_idempotent_checkout").count(),
            1,
        )
        self.assertEqual(
            CheckoutSession.objects.get(provider_checkout_session_id="cs_idempotent_checkout").status,
            CheckoutSession.Status.COMPLETE,
        )

    def test_handle_payment_failed_is_idempotent_for_same_event(self):
        event = {
            "id": "evt_idempotent_failed",
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_idempotent_failed",
                    "customer": self.customer.provider_customer_id,
                    "amount": 1700,
                    "currency": "usd",
                    "metadata": {
                        "user_id": str(self.user.id),
                        "payment_kind": "one_time",
                    },
                    "last_payment_error": {
                        "code": "card_declined",
                        "message": "Declined for idempotency test",
                    },
                }
            },
        }

        StripeService.handle_event(event)
        StripeService.handle_event(event)

        self.assertEqual(
            PaymentRecord.objects.filter(provider_payment_intent_id="pi_idempotent_failed").count(),
            1,
        )
        self.assertEqual(
            PaymentRecord.objects.get(provider_payment_intent_id="pi_idempotent_failed").status,
            PaymentRecord.Status.FAILED,
        )

    @patch("payments.services.stripe_service.StripeService._publish_payment_event")
    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_subscription_payment_clears_disabled_plan_state_on_recovery(
        self,
        create_payment_intent,
        publish_payment_event,
    ):
        PaymentMethod.objects.create(
            customer=self.customer,
            provider_payment_method_id="pm_recovery",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030,
            is_default=True,
        )
        due_now = timezone.now()
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_recovery",
            status=Subscription.Status.PAST_DUE,
            current_period_start=due_now - timedelta(days=30),
            current_period_end=due_now,
            cancel_at_period_end=True,
            canceled_at=due_now - timedelta(days=1),
            plan_disabled=True,
            plan_disabled_reason="max_payment_failures",
            plan_disabled_attempt_count=3,
            plan_disabled_at=due_now - timedelta(days=1),
            started_at=due_now - timedelta(days=30),
            metadata={
                "dunning_attempt_count": 2,
                "next_retry_at": None,
                "last_dunning_error": {"code": "card_declined"},
                "plan_disabled": True,
            },
        )
        create_payment_intent.return_value = {
            "id": "pi_recovery_success",
            "amount": 1500,
            "currency": "usd",
        }

        StripeService.collect_subscription_payment(subscription)

        subscription.refresh_from_db()
        payment = PaymentRecord.objects.get(provider_payment_intent_id="pi_recovery_success")

        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertFalse(subscription.cancel_at_period_end)
        self.assertIsNone(subscription.canceled_at)
        self.assertFalse(subscription.plan_disabled)
        self.assertEqual(subscription.plan_disabled_reason, "")
        self.assertEqual(subscription.plan_disabled_attempt_count, 0)
        self.assertIsNone(subscription.plan_disabled_at)
        self.assertEqual(subscription.metadata["dunning_attempt_count"], 0)
        self.assertIsNone(subscription.metadata["next_retry_at"])
        self.assertEqual(payment.status, PaymentRecord.Status.SUCCEEDED)
        publish_payment_event.assert_called_once()

    @patch("payments.services.stripe_service.stripe.PaymentIntent.create")
    def test_collect_due_recurring_payments_skips_unpaid_disabled_subscriptions(self, create_payment_intent):
        subscription = Subscription.objects.create(
            customer=self.customer,
            product=self.recurring_product,
            price=self.recurring_price,
            provider_subscription_id="manual_skip_unpaid",
            status=Subscription.Status.UNPAID,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(minutes=1),
            cancel_at_period_end=True,
            canceled_at=timezone.now() - timedelta(days=1),
            plan_disabled=True,
            plan_disabled_reason="max_payment_failures",
            plan_disabled_attempt_count=3,
            plan_disabled_at=timezone.now() - timedelta(days=1),
            started_at=timezone.now() - timedelta(days=30),
            metadata={"plan_disabled": True},
        )

        summary = StripeService.collect_due_recurring_payments()

        subscription.refresh_from_db()
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(summary["succeeded"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(PaymentRecord.objects.filter(subscription=subscription).count(), 0)
        self.assertEqual(subscription.status, Subscription.Status.UNPAID)
        create_payment_intent.assert_not_called()
