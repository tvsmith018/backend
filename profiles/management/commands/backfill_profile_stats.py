from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from profiles.services.profile_stats_sync import sync_profile_stats_for_user

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Recalculate UserProfileStats and UserRatingSummary from source tables "
        "(posts/follows/views/ratings/comments/likes/images). Use --dry-run to preview impacted users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview how many users would be updated without writing changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total_users = User.objects.count()
        changed_users = 0
        errors = 0

        for user in User.objects.order_by("pk").iterator(chunk_size=300):
            try:
                if dry_run:
                    if sync_profile_stats_for_user(
                        user.pk,
                        touch_last_activity=False,
                        dry_run=True,
                    ):
                        changed_users += 1
                    continue

                if sync_profile_stats_for_user(
                    user.pk,
                    touch_last_activity=True,
                    dry_run=False,
                ):
                    changed_users += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"user_id={user.pk} email={getattr(user, 'email', '')!r}: {exc}"
                    )
                )

        prefix = "[dry-run] users needing updates" if dry_run else "Users updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}: {changed_users} (users scanned: {total_users}, errors: {errors})"
            )
        )
