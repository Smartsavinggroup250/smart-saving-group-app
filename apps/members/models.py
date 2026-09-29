from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Member(models.Model):

    MEMBERSHIP_STATUS = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("SUSPENDED", "Suspended"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="member"
    )

    # --------------------------------------------------
    # MEMBER INFORMATION
    # --------------------------------------------------

    member_number = models.CharField(
        max_length=30,
        unique=True
    )

    phone = models.CharField(
        max_length=20
    )

    national_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True
    )

    shares = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    # --------------------------------------------------
    # ADDRESS
    # --------------------------------------------------

    country = models.CharField(
        max_length=100,
        default="Rwanda"
    )

    province = models.CharField(
        max_length=100,
        blank=True
    )

    district = models.CharField(
        max_length=100,
        blank=True
    )

    sector = models.CharField(
        max_length=100,
        blank=True
    )

    cell = models.CharField(
        max_length=100,
        blank=True
    )

    village = models.CharField(
        max_length=100,
        blank=True
    )

    # Keep old address field for compatibility
    address = models.CharField(
        max_length=200,
        blank=True
    )

    # --------------------------------------------------
    # PERSONAL INFORMATION
    # --------------------------------------------------

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    joined_date = models.DateField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS,
        default="ACTIVE"
    )

    # --------------------------------------------------
    # NEXT OF KIN
    # --------------------------------------------------

    next_of_kin_name = models.CharField(
        max_length=150,
        blank=True
    )

    next_of_kin_phone = models.CharField(
        max_length=20,
        blank=True
    )

    next_of_kin_relationship = models.CharField(
        max_length=100,
        blank=True
    )

    # --------------------------------------------------
    # SYSTEM
    # --------------------------------------------------

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.member_number} - "
            f"{self.user.get_full_name()}"
        )

    @property
    def monthly_contribution_amount(self):
        return self.shares * 10000