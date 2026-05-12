import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from common.security_alerts import get_recent_event_count


class Command(BaseCommand):
    help = "Print a lightweight security health report from recent cache counters."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Output report as compact JSON for monitoring collectors.",
        )

    def handle(self, *args, **options):
        window_seconds = settings.SECURITY_ALERT_WINDOW_SECONDS
        throttle_threshold = settings.SECURITY_THROTTLE_ALERT_THRESHOLD
        webhook_threshold = settings.SECURITY_WEBHOOK_BLOCK_ALERT_THRESHOLD
        now = timezone.now()

        throttle_count = get_recent_event_count(
            event_type="throttle",
            window_seconds=window_seconds,
        )
        webhook_block_count = get_recent_event_count(
            event_type="webhook_block",
            window_seconds=window_seconds,
        )

        payload = {
            "generated_at": now.isoformat(),
            "window_seconds": window_seconds,
            "thresholds": {
                "throttle": throttle_threshold,
                "webhook_block": webhook_threshold,
            },
            "recent_counters": {
                "throttle": throttle_count,
                "webhook_block": webhook_block_count,
            },
        }

        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, separators=(",", ":")))
            return

        self.stdout.write(self.style.SUCCESS("Security Health Report"))
        self.stdout.write(f"Generated at: {now.isoformat()}")
        self.stdout.write(f"Window (seconds): {window_seconds}")
        self.stdout.write("")
        self.stdout.write("Thresholds")
        self.stdout.write(f"- Throttle spike threshold: {throttle_threshold}")
        self.stdout.write(f"- Webhook block spike threshold: {webhook_threshold}")
        self.stdout.write("")
        self.stdout.write("Recent counters (current window)")
        self.stdout.write(f"- throttle events: {throttle_count}")
        self.stdout.write(f"- webhook_block events: {webhook_block_count}")
