from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):

    list_display = (
        "member",
        "loan_type",
        "requested_amount",
        "approved_amount",
        "duration_months",
        "status",
        "application_date",
        "approved_by",
    )

    list_filter = (
        "loan_type",
        "status",
        "duration_months",
    )

    search_fields = (
        "member__member_number",
        "member__user__first_name",
        "member__user__last_name",
    )

    readonly_fields = (
        "application_date",
        "approved_at",
        "disbursed_at",
        "completed_at",
        "created_at",
        "updated_at",
    )