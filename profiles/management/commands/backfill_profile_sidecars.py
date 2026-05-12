from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from profiles.models import UserProfileSettings, UserProfileStats, UserRatingSummary

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Create UserProfileSettings, UserProfileStats, and UserRatingSummary rows "
        "for any user that is missing them (idempotent; safe to re-run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print counts only; do not write to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total_users = User.objects.count()
        created_settings = 0
        created_stats = 0
        created_ratings = 0
        errors = 0

        for user in User.objects.order_by("pk").iterator(chunk_size=500):
            try:
                if dry_run:
                    if not UserProfileSettings.objects.filter(user_id=user.pk).exists():
                        created_settings += 1
                    if not UserProfileStats.objects.filter(user_id=user.pk).exists():
                        created_stats += 1
                    if not UserRatingSummary.objects.filter(user_id=user.pk).exists():
                        created_ratings += 1
                else:
                    with transaction.atomic():
                        _, created = UserProfileSettings.objects.get_or_create(user=user)
                        if created:
                            created_settings += 1
                        _, created = UserProfileStats.objects.get_or_create(user=user)
                        if created:
                            created_stats += 1
                        _, created = UserRatingSummary.objects.get_or_create(user=user)
                        if created:
                            created_ratings += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(f"user_id={user.pk} email={user.email!r}: {exc}")
                )

        prefix = "[dry-run] would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix} - settings: {created_settings}, stats: {created_stats}, "
                f"rating_summary: {created_ratings} (users scanned: {total_users}, errors: {errors})"
            )
        )
