from django.test import SimpleTestCase


class OpenAPIAndHealthTests(SimpleTestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_openapi_schema_available_when_docs_enabled(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"openapi", response.content.lower())
