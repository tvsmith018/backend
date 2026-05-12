from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.conf import settings
from django.utils import timezone

from payments.models import PaymentRecord, Subscription


class Command(BaseCommand):
    help = "Print a lightweight billing reconciliation report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="How many trailing days to include in the report.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        since = timezone.now() - timezone.timedelta(days=days)
        billing_timezone = ZoneInfo(settings.BILLING_TIME_ZONE)

        payments = PaymentRecord.objects.filter(created_at__gte=since)
        payment_summary = list(
            payments.values("status").annotate(
                count=Count("id"),
                total_amount=Sum("amount"),
            )
        )

        active_subscriptions = Subscription.objects.filter(
            status=Subscription.Status.ACTIVE
        ).count()
        past_due_subscriptions = Subscription.objects.filter(
            status=Subscription.Status.PAST_DUE
        ).count()
        unpaid_subscriptions = Subscription.objects.filter(
            status=Subscription.Status.UNPAID
        ).count()
        retry_scheduled = sum(
            1
            for subscription in Subscription.objects.filter(
                status__in=[Subscription.Status.PAST_DUE, Subscription.Status.UNPAID]
            )
            if (subscription.metadata or {}).get("next_retry_at")
        )
        due_now = Subscription.objects.filter(
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE],
            current_period_end__isnull=False,
            current_period_end__lte=timezone.now(),
            cancel_at_period_end=False,
        ).count()

        self.stdout.write(self.style.SUCCESS("Billing Reconciliation Report"))
        self.stdout.write(f"Window start: {since.isoformat()}")
        self.stdout.write(f"Window end:   {timezone.now().isoformat()}")
        self.stdout.write(f"Billing timezone: {billing_timezone.key}")
        self.stdout.write("")
        self.stdout.write(f"Active subscriptions: {active_subscriptions}")
        self.stdout.write(f"Past due subscriptions: {past_due_subscriptions}")
        self.stdout.write(f"Unpaid subscriptions: {unpaid_subscriptions}")
        self.stdout.write(f"Scheduled for retry: {retry_scheduled}")
        self.stdout.write(f"Currently due now: {due_now}")
        self.stdout.write("")

        if not payment_summary:
            self.stdout.write("No payments found in the selected window.")
            return

        for row in payment_summary:
            total_amount = Decimal(row["total_amount"] or 0) / Decimal("100")
            self.stdout.write(
                f"{row['status']}: count={row['count']} total=${total_amount:.2f}"
            )
