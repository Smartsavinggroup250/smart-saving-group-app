
from django.contrib import admin
from .models import Penalty, PenaltyPayment


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "member",
        "contribution",
        "number_of_shares",
        "amount",
        "status",
        "issued_at",
    )

    list_filter = (
        "status",
        "issued_at",
    )

    search_fields = (
        "member__member_number",
        "member__user__username",
        "member__user__first_name",
        "member__user__last_name",
        "reason",
    )

    readonly_fields = (
        "issued_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.issued_by_id:
            obj.issued_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(PenaltyPayment)
class PenaltyPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "penalty",
        "member",
        "amount",
        "payment_method",
        "reference",
        "status",
        "payment_date",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_date",
    )

    search_fields = (
        "member__member_number",
        "member__user__username",
        "reference",
    )

    readonly_fields = (
        "payment_date",
        "updated_at",
    )
