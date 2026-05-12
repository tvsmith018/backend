from django.core.management.base import BaseCommand
from django.db.models import Count

from profiles.models import ProfilePost


class Command(BaseCommand):
    help = (
        "Recalculate ProfilePost.likes_count from related ProfilePostLike rows "
        "(idempotent; safe to re-run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print posts that would be updated, without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        scanned = 0
        mismatched = 0
        updated = 0

        qs = (
            ProfilePost.objects
            .annotate(likes_count_live=Count("likes", distinct=True))
            .order_by("pk")
        )

        for post in qs.iterator(chunk_size=500):
            scanned += 1
            expected = int(post.likes_count_live or 0)
            current = int(post.likes_count or 0)
            if current == expected:
                continue

            mismatched += 1
            if dry_run:
                self.stdout.write(
                    f"[dry-run] post_id={post.pk} likes_count={current} -> {expected}"
                )
                continue

            ProfilePost.objects.filter(pk=post.pk).update(likes_count=expected)
            updated += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[dry-run] scanned={scanned}, mismatched={mismatched}, updates_applied=0"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. scanned={scanned}, mismatched={mismatched}, updated={updated}"
            )
        )
