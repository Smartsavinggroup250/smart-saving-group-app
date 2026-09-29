from datetime import date

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import notify_member

from .models import Loan


def get_loan_due_date(loan):
    """
    Calculate the loan due date from the disbursement date
    and the loan duration in months.
    """

    if not loan.disbursed_at:
        return None

    disbursed_date = timezone.localtime(
        loan.disbursed_at
    ).date()

    return disbursed_date + relativedelta(
        months=loan.duration_months
    )


def send_loan_reminders():
    """
    Send a reminder to borrowers whose loan is exactly
    10 days away from the due date.

    Only the borrower concerned receives the notification.
    """

    today = timezone.localdate()

    loans = Loan.objects.filter(
        status="DISBURSED",
        disbursed_at__isnull=False,
    ).select_related(
        "member",
        "member__user",
    )

    sent_count = 0

    for loan in loans:

        # Ignore loans already fully paid
        if loan.is_fully_paid:
            continue

        due_date = get_loan_due_date(loan)

        if not due_date:
            continue

        days_remaining = (
            due_date - today
        ).days

        # We only notify when exactly 10 days remain
        if days_remaining != 10:
            continue

        outstanding_balance = loan.remaining_balance

        title = "Loan Payment Reminder"

        message = (
            f"Your loan is due in 10 days, "
            f"on {due_date:%d %B %Y}. "
            f"Your outstanding balance is "
            f"{outstanding_balance:,.2f} RWF. "
            f"Please make your payment before the due date."
        )

        # Prevent duplicate notification on the same day
        already_sent = Notification.objects.filter(
            recipient=loan.member.user,
            title=title,
            notification_type="LOAN",
            message=message,
            created_at__date=today,
        ).exists()

        if already_sent:
            continue

        notify_member(
            loan.member,
            title=title,
            message=message,
            notification_type="LOAN",
        )

        sent_count += 1

    return {
        "success": True,
        "message": (
            f"Loan reminders processed for {today:%d %B %Y}."
        ),
        "sent": sent_count,
    }
    
def send_loan_due_today_notifications():
    today = timezone.localdate()

    loans = Loan.objects.filter(
        status="DISBURSED",
        disbursed_at__isnull=False,
    ).select_related(
        "member",
        "member__user",
    )

    sent_count = 0

    for loan in loans:
        if loan.is_fully_paid:
            continue

        due_date = get_loan_due_date(loan)

        if not due_date:
            continue

        # Notify only when the loan is due today
        if due_date != today:
            continue

        outstanding_balance = loan.remaining_balance

        title = "Loan Payment Due Today"

        message = (
            f"Your loan payment is due today, "
            f"{due_date:%d %B %Y}. "
            f"Your outstanding balance is "
            f"{outstanding_balance:,.2f} RWF. "
            f"Please make your payment today."
        )

        # Prevent duplicate notification on the same day
        already_sent = Notification.objects.filter(
            recipient=loan.member.user,
            title=title,
            notification_type="LOAN",
            message=message,
            created_at__date=today,
        ).exists()

        if already_sent:
            continue

        notify_member(
            loan.member,
            title=title,
            message=message,
            notification_type="LOAN",
        )

        sent_count += 1

    return {
        "success": True,
        "message": (
            f"Loan due-today notifications processed for "
            f"{today:%d %B %Y}."
        ),
        "sent": sent_count,
    }    