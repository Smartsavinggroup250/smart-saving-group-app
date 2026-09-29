from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):

    list_display = [
        "member_number",
        "user",
        "phone",
        "status",
        "joined_date",
    ]

    list_filter = [
        "status",
        "joined_date",
    ]

    search_fields = [
        "member_number",
        "user__username",
        "user__first_name",
        "user__last_name",
        "phone",
    ]

    readonly_fields = [
        "joined_date",
        "updated_at",
    ]