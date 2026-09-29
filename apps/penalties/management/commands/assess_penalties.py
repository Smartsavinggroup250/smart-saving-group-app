from django.core.management.base import BaseCommand

from apps.penalties.services import assess_monthly_penalties


class Command(BaseCommand):
    help = "Automatically assess penalties for late monthly contributions."

    def handle(self, *args, **options):
        result = assess_monthly_penalties()

        if not result["success"]:
            self.stdout.write(
                self.style.WARNING(result["message"])
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'{result["message"]} '
                f'Penalties created: {result["created"]}'
            )
        )