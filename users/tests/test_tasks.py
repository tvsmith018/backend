from unittest.mock import patch

from django.test import SimpleTestCase

from users.tasks.maintence import flush_expired_tokens


class MaintenanceTaskTests(SimpleTestCase):
    @patch("users.tasks.maintence.call_command")
    def test_flush_expired_tokens_runs_management_command(self, call_command):
        flush_expired_tokens()

        call_command.assert_called_once_with("flushexpiredtokens")
