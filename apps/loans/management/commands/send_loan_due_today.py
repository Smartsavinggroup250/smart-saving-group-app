from django.core.management.base import BaseCommand

from apps.loans.services import send_loan_due_today_notifications


class Command(BaseCommand):
    help = "Notify borrowers whose loans are due today."

    def handle(self, *args, **options):
        result = send_loan_due_today_notifications()

        self.stdout.write(
            self.style.SUCCESS(
                f'{result["message"]} '
                f'Notifications sent: {result["sent"]}'
            )
        )