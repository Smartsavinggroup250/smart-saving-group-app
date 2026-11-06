
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.members.models import Member
from apps.savings.models import MonthlyContribution
from apps.notifications.services import (
    notify_member,
    notify_admins_and_treasurers,
)

from .models import Penalty, PENALTY_PER_SHARE


def get_contribution_deadline(month):
    """Return the 5th day of the month following the contribution month."""
    if month.month == 12:
        return date(month.year + 1, 1, 5)

    return date(month.year, month.month + 1, 5)


def create_penalty_for_member(member, month, contribution=None):
    """Create one penalty per active member per contribution month."""

    month = month.replace(day=1)

    if member.status != "ACTIVE" or member.shares <= 0:
        return None, False

    shares = member.shares
    amount = Decimal(shares) * PENALTY_PER_SHARE

    with transaction.atomic():
        penalty, created = Penalty.objects.get_or_create(
            member=member,
            contribution_month=month,
            defaults={
                "contribution": contribution,
                "number_of_shares": shares,
                "amount": amount,
                "reason": (
                    f"Late monthly contribution for {month:%B %Y}"
                ),
                "status": "PENDING",
            },
        )

        if (
            not created
            and contribution is not None
            and penalty.contribution_id is None
        ):
            penalty.contribution = contribution
            penalty.save(update_fields=["contribution"])

    if created:
        notify_member(
            member,
            title="Late Contribution Penalty Issued",
            message=(
                f"A penalty of {amount:,.2f} RWF has been issued "
                f"for your {month:%B %Y} contribution. "
                f"The payment deadline was "
                f"{get_contribution_deadline(month):%d %B %Y}. "
                f"Penalty rate: 2,000 RWF per share."
            ),
            notification_type="PENALTY",
        )

        notify_admins_and_treasurers(
            title="Automatic Penalty Generated",
            message=(
                f"A penalty of {amount:,.2f} RWF has been generated "
                f"for member {member.member_number} for "
                f"{month:%B %Y}. Shares: {shares}."
            ),
            notification_type="PENALTY",
        )

    return penalty, created


def generate_monthly_penalties(month, today=None):
    """
    Assess active members whose contributions were not approved
    by the 5th day of the following month.
    """

    month = month.replace(day=1)

    if today is None:
        today = timezone.localdate()

    deadline = get_contribution_deadline(month)

    if today <= deadline:
        return {
            "created": 0,
            "skipped": True,
            "message": (
                f"The deadline is {deadline}. "
                "Penalties cannot be generated yet."
            ),
        }

    members = Member.objects.filter(
        status="ACTIVE"
    ).select_related("user")

    created_count = 0

    for member in members:

        # Get approved contributions with approval dates.
        approved_contributions = list(
            MonthlyContribution.objects.filter(
                member=member,
                month=month,
                status="APPROVED",
                approved_at__isnull=False,
            ).order_by("approved_at")
        )

        # Check approval dates using Python and Kigali timezone.
        paid_on_time = any(
            timezone.localtime(c.approved_at).date() <= deadline
            for c in approved_contributions
        )

        if paid_on_time:
            continue

        # Find a contribution approved after the deadline, if any.
        late_contribution = next(
            (
                c for c in approved_contributions
                if timezone.localtime(c.approved_at).date() > deadline
            ),
            None,
        )

        penalty, created = create_penalty_for_member(
            member=member,
            month=month,
            contribution=late_contribution,
        )

        if created:
            created_count += 1

    return {
        "created": created_count,
        "skipped": False,
        "month": month,
        "deadline": deadline,
    }

def generate_penalty_for_late_approval(contribution):
    """
    Called after Treasurer/Admin approves a contribution.
    Generate a penalty if approval happened after the deadline.
    """

    if contribution.status != "APPROVED":
        return None

    if not contribution.approved_at:
        return None

    month = contribution.month.replace(day=1)
    deadline = get_contribution_deadline(month)

    approval_date = timezone.localtime(
        contribution.approved_at
    ).date()

    if approval_date <= deadline:
        return None

    return create_penalty_for_member(
        member=contribution.member,
        month=month,
        contribution=contribution,
    )
