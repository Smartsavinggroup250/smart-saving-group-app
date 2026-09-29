from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class MonthlyContribution(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("BANK", "Bank"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="monthly_contributions",
    )

    month = models.DateField(
        help_text="Use the first day of the contribution month."
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    notes = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contribution_requests",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_contributions",
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

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-month", "-created_at"]

    def clean(self):
        super().clean()

        # MySQL does not support Django's conditional
        # UniqueConstraint, so we enforce the same rule
        # through Django validation.
        if (
            self.status == "APPROVED"
            and self.member_id
            and self.month
        ):
            existing = MonthlyContribution.objects.filter(
                member_id=self.member_id,
                month=self.month,
                status="APPROVED",
            )

            # When editing an existing contribution,
            # don't compare it against itself.
            if self.pk:
                existing = existing.exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    {
                        "month": (
                            "This member already has an approved "
                            "contribution for this month."
                        )
                    }
                )

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"{self.month:%Y-%m} - {self.amount}"
        )


class SavingsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("CONTRIBUTION", "Monthly Contribution"),
        ("ADJUSTMENT", "Savings Adjustment"),
    ]

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="savings_transactions",
    )

    contribution = models.OneToOneField(
        MonthlyContribution,
        on_delete=models.PROTECT,
        related_name="transaction",
        blank=True,
        null=True,
    )

    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    transaction_date = models.DateTimeField(
        auto_now_add=True,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_savings_transactions",
    )

    class Meta:
        ordering = ["-transaction_date"]

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"{self.transaction_type} - {self.amount}"
        )
