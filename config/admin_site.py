from types import MethodType


def _superuser_only_has_permission(self, request):
    user = request.user
    return bool(user and user.is_active and user.is_superuser)


def apply_superuser_only_admin_access(admin_site):
    admin_site.has_permission = MethodType(_superuser_only_has_permission, admin_site)
    return admin_site
