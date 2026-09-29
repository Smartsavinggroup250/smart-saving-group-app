from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


# ============================================================
# LOAN INTEREST RATES
# ============================================================

LOAN_INTEREST_RATES = {
    "GOLD": Decimal("5.00"),
    "PLATINUM": Decimal("4.00"),
    "TITANIUM": Decimal("3.00"),
}


# ============================================================
# LOAN TYPE CALCULATION
# ============================================================

def get_loan_type(amount):
    """
    Determine the loan category based on the requested amount.

    Gold:     <= 100,000 RWF
    Platinum: 100,001 - 300,000 RWF
    Titanium: > 300,000 RWF
    """

    amount = Decimal(amount)

    if amount <= Decimal("100000"):
        return "GOLD"

    elif amount <= Decimal("300000"):
        return "PLATINUM"

    return "TITANIUM"


# ============================================================
# INTEREST RATE CALCULATION
# ============================================================

def get_interest_rate(loan_type):
    """
    Return the monthly interest rate for the loan type.
    """

    return LOAN_INTEREST_RATES.get(
        loan_type,
        Decimal("0.00")
    )


# ============================================================
# LOAN MODEL
# ============================================================

class Loan(models.Model):

    LOAN_TYPES = [
        ("GOLD", "Gold Loan"),
        ("PLATINUM", "Platinum Loan"),
        ("TITANIUM", "Titanium Loan"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("DISBURSED", "Disbursed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    # --------------------------------------------------------
    # MEMBER
    # --------------------------------------------------------

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="loans",
    )

    # --------------------------------------------------------
    # LOAN TYPE
    # --------------------------------------------------------

    loan_type = models.CharField(
        max_length=20,
        choices=LOAN_TYPES,
    )

    # --------------------------------------------------------
    # REQUESTED AMOUNT
    # --------------------------------------------------------

    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("1.00")
            )
        ],
    )

    # --------------------------------------------------------
    # APPROVED AMOUNT
    # --------------------------------------------------------

    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # INTEREST RATE
    # --------------------------------------------------------

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    # --------------------------------------------------------
    # LOAN DURATION
    # --------------------------------------------------------

    duration_months = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ],
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    # --------------------------------------------------------
    # PURPOSE
    # --------------------------------------------------------

    purpose = models.TextField()

    # --------------------------------------------------------
    # APPLICATION DATE
    # --------------------------------------------------------

    application_date = models.DateTimeField(
        auto_now_add=True,
    )

    # --------------------------------------------------------
    # APPROVAL INFORMATION
    # --------------------------------------------------------

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_loans",
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

    # --------------------------------------------------------
    # DISBURSEMENT
    # --------------------------------------------------------

    disbursed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # COMPLETION
    # --------------------------------------------------------

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # --------------------------------------------------------
    # META
    # --------------------------------------------------------

    class Meta:
        ordering = ["-application_date"]

    # --------------------------------------------------------
    # STRING REPRESENTATION
    # --------------------------------------------------------

    def __str__(self):
        return (
            f"{self.member.member_number} - "
            f"{self.get_loan_type_display()} - "
            f"{self.requested_amount}"
        )

    # ========================================================
    # CALCULATIONS
    # ========================================================

    @property
    def principal_amount(self):
        """
        Use approved amount when available,
        otherwise use requested amount.
        """

        return (
            self.approved_amount
            if self.approved_amount is not None
            else self.requested_amount
        )

    @property
    def monthly_interest(self):
        """
        Calculate one month's interest using
        the flat-rate method.
        """

        return (
            self.principal_amount
            * self.interest_rate
            / Decimal("100")
        )

    @property
    def total_interest(self):
        """
        Calculate total interest over the
        entire loan duration.
        """

        return (
            self.monthly_interest
            * Decimal(self.duration_months)
        )

    @property
    def total_payable(self):
        """
        Principal + total interest.
        """

        return (
            self.principal_amount
            + self.total_interest
        )

    @property
    def monthly_installment(self):
        """
        Calculate the monthly installment.
        """

        if self.duration_months <= 0:
            return Decimal("0.00")

        return (
            self.total_payable
            / Decimal(self.duration_months)
        )
        
# ibi mbishyize hano ngo bizadufashe muri loan repayments
    @property
    def total_repaid(self):
        from apps.repayments.models import LoanRepayment

        total = LoanRepayment.objects.filter(
            loan=self,
            status="APPROVED",
        ).aggregate(
            total=models.Sum("amount")
        )["total"]

        return total or Decimal("0.00")

    @property
    def remaining_balance(self):
        balance = self.total_payable - self.total_repaid

        if balance < Decimal("0.00"):
            return Decimal("0.00")

        return balance

    @property
    def is_fully_paid(self):
        return self.remaining_balance <= Decimal("0.00")        