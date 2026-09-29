from django.core.management.base import BaseCommand

from apps.loans.services import send_loan_reminders


class Command(BaseCommand):

    help = "Send loan payment reminders to borrowers whose loans are due in 10 days."

    def handle(self, *args, **options):

        result = send_loan_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f'{result["message"]} '
                f'Reminders sent: {result["sent"]}'
            )
        )