from django.test import SimpleTestCase

from config.settings import _build_allowed_origins, _parse_bool_env


class SecuritySettingsHelperTests(SimpleTestCase):
    def test_parse_bool_env_defaults_when_missing(self):
        self.assertFalse(_parse_bool_env("MISSING_BOOL_TEST"))

    def test_build_allowed_origins_from_hosts(self):
        origins = _build_allowed_origins(
            [
                "www.bigchiefnewz.com",
                "bigchiefnewz-a2e8434d1e6d.herokuapp.com",
                "localhost:3000",
                "127.0.0.1:8000",
            ]
        )

        self.assertEqual(
            origins,
            [
                "https://www.bigchiefnewz.com",
                "https://bigchiefnewz-a2e8434d1e6d.herokuapp.com",
                "http://localhost:3000",
                "https://localhost:3000",
                "http://127.0.0.1:8000",
                "https://127.0.0.1:8000",
            ],
        )

    def test_build_allowed_origins_skips_wildcards(self):
        origins = _build_allowed_origins(["*", "*.example.com", ""])

        self.assertEqual(origins, [])
