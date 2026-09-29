from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import MonthlyContribution, SavingsTransaction


@admin.register(MonthlyContribution)
class MonthlyContributionAdmin(admin.ModelAdmin):

    list_display = (
        "member",
        "month",
        "amount",
        "payment_method",
        "status",
        "requested_by",
        "approved_by",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "month",
    )

    search_fields = (
        "member__member_number",
        "member__user__first_name",
        "member__user__last_name",
        "reference",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "approved_at",
    )


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "member",
        "transaction_type",
        "amount",
        "reference",
        "transaction_date",
        "created_by",
    )

    list_filter = (
        "transaction_type",
        "transaction_date",
    )

    search_fields = (
        "member__member_number",
        "reference",
    )

    readonly_fields = (
        "transaction_date",
    )