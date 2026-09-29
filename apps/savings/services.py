from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.members.models import Member
from apps.notifications.models import Notification
from apps.notifications.services import notify_member

from .models import MonthlyContribution


DEADLINE_DAY = 5
SHARE_VALUE = Decimal("10000.00")


def get_contribution_deadline(year, month):
    if month == 12:
        deadline_year = year + 1
        deadline_month = 1
    else:
        deadline_year = year
        deadline_month = month + 1

    return date(
        deadline_year,
        deadline_month,
        DEADLINE_DAY,
    )


def send_contribution_reminders():
    today = timezone.localdate()

    # Reminder is sent exactly 5 days before the deadline.
    future_deadline = today + timedelta(days=5)

    if future_deadline.day != DEADLINE_DAY:
        return {
            "success": True,
            "message": (
                f"No contribution reminder is scheduled for "
                f"{today:%d %B %Y}."
            ),
            "sent": 0,
        }

    # Determine the contribution month.
    if future_deadline.month == 1:
        contribution_year = future_deadline.year - 1
        contribution_month = 12
    else:
        contribution_year = future_deadline.year
        contribution_month = future_deadline.month - 1

    contribution_date = date(
        contribution_year,
        contribution_month,
        1,
    )

    sent_count = 0

    members = Member.objects.filter(
        status="ACTIVE"
    ).select_related("user")

    for member in members:

        contribution = MonthlyContribution.objects.filter(
            member=member,
            month__year=contribution_year,
            month__month=contribution_month,
        ).order_by("-created_at").first()

        # If an approved contribution exists, the member has paid.
        if contribution and contribution.status == "APPROVED":
            continue

        title = "Monthly Contribution Reminder"

        message = (
            f"Your monthly contribution for "
            f"{contribution_date:%B %Y} "
            f"has not yet been paid. "
            f"The payment deadline is "
            f"{future_deadline:%d %B %Y}. "
            f"Please pay your contribution before the deadline "
            f"to avoid a late contribution penalty."
        )

        # Prevent duplicate notification on the same day.
        already_sent = Notification.objects.filter(
            recipient=member.user,
            title=title,
            notification_type="CONTRIBUTION",
            message=message,
            created_at__date=today,
        ).exists()

        if already_sent:
            continue

        notify_member(
            member,
            title=title,
            message=message,
            notification_type="CONTRIBUTION",
        )

        sent_count += 1

    return {
        "success": True,
        "message": (
            f"Contribution reminders processed for "
            f"{today:%d %B %Y}."
        ),
        "sent": sent_count,
    }