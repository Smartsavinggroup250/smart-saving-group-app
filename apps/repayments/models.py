from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class LoanRepayment(models.Model):
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

    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.PROTECT,
        related_name="repayments",
    )

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="loan_repayments",
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
        related_name="requested_loan_repayments",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_loan_repayments",
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

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"{self.amount} - "
            f"{self.get_status_display()}"
        )