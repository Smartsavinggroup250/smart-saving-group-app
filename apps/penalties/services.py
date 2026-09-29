from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.members.models import Member
from apps.penalties.models import Penalty
from apps.savings.models import MonthlyContribution


SHARE_VALUE = Decimal("10000.00")
PENALTY_PER_SHARE = Decimal("2000.00")
DEADLINE_DAY = 5


def get_previous_month(year, month):
    """
    Return the previous month and its year.
    """

    if month == 1:
        return year - 1, 12

    return year, month - 1


def assess_monthly_penalties(year=None, month=None):
    """
    Automatically assess penalties for members who have
    not paid their monthly contribution by the 5th of
    the following month.

    Example:
        September contribution
        -> deadline is October 5
        -> penalty is assessed after October 5.
    """

    today = timezone.localdate()

    # By default, assess the previous month's contribution.
    if year is None or month is None:
        assessment_year, assessment_month = get_previous_month(
            today.year,
            today.month,
        )
    else:
        assessment_year = year
        assessment_month = month

    # Deadline is the 5th day of the following month.
    if assessment_month == 12:
        deadline_year = assessment_year + 1
        deadline_month = 1
    else:
        deadline_year = assessment_year
        deadline_month = assessment_month + 1

    deadline_date = date(
        deadline_year,
        deadline_month,
        DEADLINE_DAY,
    )

    # Do not assess penalties until the deadline has passed.
    if today <= deadline_date:
        return {
            "success": False,
            "message": (
                f"Penalty assessment for "
                f"{date(assessment_year, assessment_month, 1):%B %Y} "
                f"starts after {deadline_date:%d %B %Y}."
            ),
            "created": 0,
        }

    created_count = 0

    active_members = Member.objects.filter(
        status="ACTIVE"
    ).select_related("user")

    for member in active_members:

        expected_amount = (
            Decimal(member.shares) * SHARE_VALUE
        )

        # Find the member's contribution for the month being assessed.
        contribution = MonthlyContribution.objects.filter(
            member=member,
            month__year=assessment_year,
            month__month=assessment_month,
        ).first()

        # If an approved contribution exists,
        # the member paid on time.
        if contribution and contribution.status == "APPROVED":
            continue

        # If no contribution exists, create a pending
        # contribution representing the amount due.
        if contribution is None:
            contribution = MonthlyContribution.objects.create(
                member=member,
                month=date(
                    assessment_year,
                    assessment_month,
                    1,
                ),
                amount=expected_amount,
                payment_method="CASH",
                reference=(
                    f"DUE-{member.id}-"
                    f"{assessment_year}-{assessment_month}"
                ),
                status="PENDING",
                requested_by=member.user,
            )

        # Prevent duplicate penalties for the same contribution.
        existing_penalty = Penalty.objects.filter(
            member=member,
            contribution=contribution,
        ).exists()

        if existing_penalty:
            continue

        penalty_amount = (
            Decimal(member.shares) * PENALTY_PER_SHARE
        )

        with transaction.atomic():

            Penalty.objects.create(
                member=member,
                contribution=contribution,
                number_of_shares=member.shares,
                amount=penalty_amount,
                reason="Late monthly contribution",
                status="PENDING",
                issued_by=member.user,
            )

            created_count += 1

    return {
        "success": True,
        "message": (
            f"Monthly penalties assessed for "
            f"{date(assessment_year, assessment_month, 1):%B %Y}."
        ),
        "created": created_count,
    }