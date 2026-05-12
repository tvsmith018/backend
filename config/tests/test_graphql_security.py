from django.test import SimpleTestCase, override_settings

from config.graphql_security import build_graphql_validation_rules
from graphql.validation import NoSchemaIntrospectionCustomRule


class GraphQLSecurityTests(SimpleTestCase):
    @override_settings(GRAPHQL_ALLOW_INTROSPECTION=True)
    def test_validation_rules_allow_introspection_when_enabled(self):
        self.assertIsNone(build_graphql_validation_rules())

    @override_settings(GRAPHQL_ALLOW_INTROSPECTION=False)
    def test_validation_rules_disable_introspection_when_disabled(self):
        rules = build_graphql_validation_rules()
        self.assertIsNotNone(rules)
        self.assertIn(NoSchemaIntrospectionCustomRule, rules)
