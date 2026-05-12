from types import SimpleNamespace

from django.contrib import admin
from django.test import SimpleTestCase

from config.admin_site import apply_superuser_only_admin_access


class AdminSitePermissionTests(SimpleTestCase):
    def test_superuser_admin_access_is_allowed(self):
        site = apply_superuser_only_admin_access(admin.AdminSite(name="test_admin"))
        request = SimpleNamespace(
            user=SimpleNamespace(is_active=True, is_superuser=True)
        )

        self.assertTrue(site.has_permission(request))

    def test_staff_user_without_superuser_access_is_denied(self):
        site = apply_superuser_only_admin_access(admin.AdminSite(name="test_admin"))
        request = SimpleNamespace(
            user=SimpleNamespace(is_active=True, is_superuser=False)
        )

        self.assertFalse(site.has_permission(request))

    def test_inactive_superuser_access_is_denied(self):
        site = apply_superuser_only_admin_access(admin.AdminSite(name="test_admin"))
        request = SimpleNamespace(
            user=SimpleNamespace(is_active=False, is_superuser=True)
        )

        self.assertFalse(site.has_permission(request))
