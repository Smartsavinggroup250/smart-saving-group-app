
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.penalties.services import generate_monthly_penalties


class Command(BaseCommand):

    help = "Generate automatic penalties for late monthly contributions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            help="Contribution month in YYYY-MM format.",
        )

    def handle(self, *args, **options):

        today = timezone.localdate()

        selected_month = options.get("month")

        if selected_month:
            try:
                year, month = map(
                    int,
                    selected_month.split("-")
                )
                contribution_month = date(year, month, 1)

            except (ValueError, TypeError):
                self.stdout.write(
                    self.style.ERROR(
                        "Invalid month. Use YYYY-MM, e.g. 2026-10."
                    )
                )
                return

        else:
            # Check the previous calendar month.
            if today.month == 1:
                contribution_month = date(
                    today.year - 1, 12, 1
                )
            else:
                contribution_month = date(
                    today.year, today.month - 1, 1
                )

        result = generate_monthly_penalties(
            month=contribution_month,
            today=today,
        )

        if result["skipped"]:
            self.stdout.write(
                self.style.WARNING(result["message"])
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Penalty generation completed for "
                f"{contribution_month:%B %Y}. "
                f"New penalties created: {result['created']}."
            )
        )
