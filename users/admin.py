from django.contrib import admin
from rest_framework_simplejwt.token_blacklist.admin import OutstandingTokenAdmin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from .models import Users

@admin.action(description='Delete selected outstanding tokens')
def delete_outstanding_tokens(modeladmin, request, queryset):
    queryset.delete()

class MyOutstandingTokenAdmin(OutstandingTokenAdmin):
    actions = [delete_outstanding_tokens]

    def has_delete_permission(self, request, obj=None):
        return True # Or add specific permission checks as needed


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "firstname",
        "lastname",
        "is_staff",
        "is_active",
        "date_joined",
    )
    search_fields = ("email", "firstname", "lastname", "bio")
    list_filter = ("is_staff", "is_active", "date_joined")
    readonly_fields = ("date_joined",)
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "email",
                    "firstname",
                    "lastname",
                    "bio",
                    "dob",
                    "avatar",
                )
            },
        ),
        (
            "Access",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("date_joined",),
            },
        ),
    )


admin.site.unregister(OutstandingToken)
admin.site.register(OutstandingToken, MyOutstandingTokenAdmin)
