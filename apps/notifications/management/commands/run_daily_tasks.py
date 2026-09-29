from django.core.management.base import BaseCommand

from apps.penalties.services import assess_monthly_penalties
from apps.loans.services import send_loan_reminders
from apps.loans.services import send_loan_due_today_notifications
from apps.savings.services import send_contribution_reminders

class Command(BaseCommand):
    help = "Run daily Smart Saving Group notification and penalty tasks."

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                "Starting daily Smart Saving Group tasks..."
            )
        )
        # 1. Send contribution reminders
        contribution_result = send_contribution_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f'Contribution reminders sent: '
                f'{contribution_result["sent"]}'
            )
        )
        # 1. Assess monthly penalties
        penalty_result = assess_monthly_penalties()

        if penalty_result["success"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Penalty assessment completed. '
                    f'Penalties created: {penalty_result["created"]}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    penalty_result["message"]
                )
            )

        # 2. Send loan reminders — 10 days before due date
        loan_reminder_result = send_loan_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f'Loan 10-day reminders sent: '
                f'{loan_reminder_result["sent"]}'
            )
        )

        # 3. Send loan due-today notifications
        due_today_result = send_loan_due_today_notifications()

        self.stdout.write(
            self.style.SUCCESS(
                f'Loan due-today notifications sent: '
                f'{due_today_result["sent"]}'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Daily tasks completed successfully."
            )
        )