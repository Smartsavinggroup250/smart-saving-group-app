from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


SHARE_VALUE = Decimal("10000.00")
PENALTY_PER_SHARE = Decimal("2000.00")


class Penalty(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("PAID", "Paid"),
        ("WAIVED", "Waived"),
        ("REJECTED", "Rejected"),
    ]

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="penalties",
    )

    contribution = models.ForeignKey(
        "savings.MonthlyContribution",
        on_delete=models.PROTECT,
        related_name="penalties",
    )

    number_of_shares = models.PositiveIntegerField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    reason = models.TextField(
        default="Late monthly contribution",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_penalties",
        blank=True,
        null=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_penalties",
        blank=True,
        null=True,
    )

    issued_at = models.DateTimeField(
        auto_now_add=True,
    )

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    waived_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"{self.number_of_shares} shares - "
            f"{self.amount} RWF"
        )

    @staticmethod
    def calculate_shares(contribution_amount):
        """
        Calculate the number of shares from the monthly contribution.

        One share = 10,000 RWF.
        """
        contribution_amount = Decimal(contribution_amount)

        if contribution_amount <= 0:
            return 0

        return int(
            contribution_amount / SHARE_VALUE
        )

    @staticmethod
    def calculate_penalty(contribution_amount):
        """
        Calculate late contribution penalty.

        Penalty per share = 2,000 RWF.
        """
        shares = Penalty.calculate_shares(
            contribution_amount
        )

        return Decimal(shares) * PENALTY_PER_SHARE


class PenaltyPayment(models.Model):

    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("BANK", "Bank"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    penalty = models.ForeignKey(
        Penalty,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="penalty_payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_penalty_payments",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_penalty_payments",
        blank=True,
        null=True,
    )

    approved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    payment_date = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"Penalty Payment - {self.amount} RWF"
        )