from django.test import SimpleTestCase

from schemas.schema import schema


class GraphQLSchemaSmokeTests(SimpleTestCase):
    def test_schema_executes_introspection_query(self):
        result = schema.execute(
            "{ __schema { queryType { name } } }",
        )
        self.assertIsNone(result.errors)
        self.assertEqual(result.data["__schema"]["queryType"]["name"], "Query")
