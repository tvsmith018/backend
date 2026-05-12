from io import StringIO
import json

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

from common.security_alerts import record_threshold_alert


class SecurityHealthReportCommandTests(TestCase):
    @override_settings(
        SECURITY_ALERT_WINDOW_SECONDS=300,
        SECURITY_THROTTLE_ALERT_THRESHOLD=25,
        SECURITY_WEBHOOK_BLOCK_ALERT_THRESHOLD=10,
    )
    def test_security_health_report_prints_recent_counters_and_thresholds(self):
        cache.clear()
        record_threshold_alert(
            event_type="throttle",
            identifier="203.0.113.10",
            threshold=25,
            window_seconds=300,
        )
        record_threshold_alert(
            event_type="throttle",
            identifier="203.0.113.10",
            threshold=25,
            window_seconds=300,
        )
        record_threshold_alert(
            event_type="webhook_block",
            identifier="203.0.113.20",
            threshold=10,
            window_seconds=300,
        )

        output = StringIO()
        call_command("security_health_report", stdout=output)
        report = output.getvalue()

        self.assertIn("Security Health Report", report)
        self.assertIn("Window (seconds): 300", report)
        self.assertIn("Throttle spike threshold: 25", report)
        self.assertIn("Webhook block spike threshold: 10", report)
        self.assertIn("throttle events: 2", report)
        self.assertIn("webhook_block events: 1", report)

    @override_settings(
        SECURITY_ALERT_WINDOW_SECONDS=300,
        SECURITY_THROTTLE_ALERT_THRESHOLD=25,
        SECURITY_WEBHOOK_BLOCK_ALERT_THRESHOLD=10,
    )
    def test_security_health_report_json_output(self):
        cache.clear()
        record_threshold_alert(
            event_type="throttle",
            identifier="203.0.113.10",
            threshold=25,
            window_seconds=300,
        )
        record_threshold_alert(
            event_type="webhook_block",
            identifier="203.0.113.20",
            threshold=10,
            window_seconds=300,
        )

        output = StringIO()
        call_command("security_health_report", "--json", stdout=output)
        payload = json.loads(output.getvalue().strip())

        self.assertEqual(payload["window_seconds"], 300)
        self.assertEqual(payload["thresholds"]["throttle"], 25)
        self.assertEqual(payload["thresholds"]["webhook_block"], 10)
        self.assertEqual(payload["recent_counters"]["throttle"], 1)
        self.assertEqual(payload["recent_counters"]["webhook_block"], 1)
