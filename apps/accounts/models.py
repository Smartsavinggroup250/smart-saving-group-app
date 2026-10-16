from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("TREASURER", "Treasurer"),
        ("MEMBER", "Member"),
        ("AUDITOR", "Auditor"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="MEMBER"
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class MonthlyReportBalance(models.Model):
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()

    initial_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    closing_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    calculated_at = models.DateTimeField(
        auto_now=True
    )
    
    current_outstanding_loan_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = ["year", "month"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "month"],
                name="unique_monthly_report_balance"
            ),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12),
                name="monthly_report_balance_valid_month"
            ),
        ]

    def __str__(self):
        return f"Report Balance - {self.year}-{self.month:02d}"

    