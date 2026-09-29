from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.notifications.services import (
    notify_admins_and_treasurers,
    notify_member,
)

from apps.loans.models import Loan
from .forms import LoanRepaymentForm
from .models import LoanRepayment


def is_admin_or_treasurer(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    role = getattr(
        getattr(user, "profile", None),
        "role",
        None,
    )

    return role in ["ADMIN", "TREASURER"]


@login_required
def repayment_create(request, loan_id):
    """
    Allow a member to submit a repayment for their own loan.
    """

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    loan = get_object_or_404(
        Loan,
        pk=loan_id,
        member=member,
    )

    # Only approved or disbursed loans can receive repayments.
    if loan.status not in ["APPROVED", "DISBURSED"]:
        messages.warning(
            request,
            "Repayment can only be made for an approved or disbursed loan."
        )
        return redirect("loan_list")

    # If the loan is already fully paid.
    if loan.is_fully_paid:
        messages.info(
            request,
            "This loan has already been fully paid."
        )
        return redirect("loan_list")

    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)

        if form.is_valid():
            amount = form.cleaned_data["amount"]

            # Refresh the balance before accepting the repayment.
            remaining_balance = loan.remaining_balance

            # Prevent overpayment.
            if amount > remaining_balance:
                form.add_error(
                    "amount",
                    (
                        f"Repayment cannot exceed the remaining "
                        f"balance of {remaining_balance:.2f} RWF."
                    ),
                )
            else:
                repayment = form.save(commit=False)

                repayment.loan = loan
                repayment.member = member
                repayment.requested_by = request.user
                repayment.status = "PENDING"

                repayment.save()
                notify_member(
                    member,
                    title="Loan Repayment Submitted",
                    message=(
                        f"Your loan repayment request of "
                        f"{repayment.amount:,.2f} RWF has been submitted successfully. "
                        f"Your payment is currently awaiting approval."
                    ),
                    notification_type="REPAYMENT",
                )
                notify_admins_and_treasurers(
                    title="New Repayment Request",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} "
                        f"has submitted a repayment of "
                        f"{repayment.amount:,.2f} RWF "
                        f"for loan #{loan.id}. "
                        f"Please review and process the repayment."
                    ),
                    notification_type="REPAYMENT",
                )

                messages.success(
                    request,
                    "Your repayment has been submitted successfully "
                    "and is awaiting approval."
                )
                return redirect("repayment_list")

    else:
        form = LoanRepaymentForm()

    return render(
        request,
        "repayments/repayment_form.html",
        {
            "form": form,
            "loan": loan,
        },
    )


@login_required
def repayment_list(request):
    """
    Display repayments belonging to the logged-in member.
    """

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    repayments = LoanRepayment.objects.filter(
        member=member
    ).select_related(
        "loan",
    )

    return render(
        request,
        "repayments/repayment_list.html",
        {
            "repayments": repayments,
        },
    )


@login_required
def repayment_pending(request):
    """
    Display pending repayments for Admin/Treasurer.
    """

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can access this page."
        )

    repayments = LoanRepayment.objects.filter(
        status="PENDING"
    ).select_related(
        "loan",
        "member",
        "member__user",
    )

    return render(
        request,
        "repayments/repayment_pending.html",
        {
            "repayments": repayments,
        },
    )


@login_required
@transaction.atomic
def repayment_approve(request, pk):
    """
    Approve a pending repayment.

    Either Admin OR Treasurer can approve.
    """

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can approve repayments."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    repayment = get_object_or_404(
        LoanRepayment.objects.select_for_update(),
        pk=pk,
    )

    if repayment.status != "PENDING":
        messages.warning(
            request,
            "This repayment has already been processed."
        )
        return redirect("repayment_pending")

    # Lock the loan while checking the balance.
    loan = Loan.objects.select_for_update().get(
        pk=repayment.loan_id
    )

    # Recalculate remaining balance after locking.
    remaining_balance = loan.remaining_balance

    # Prevent approval that would create an overpayment.
    if repayment.amount > remaining_balance:
        repayment.status = "REJECTED"
        repayment.rejection_reason = (
            "Repayment exceeds the remaining loan balance."
        )
        repayment.approved_by = request.user
        repayment.approved_at = timezone.now()

        repayment.save(
            update_fields=[
                "status",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        notify_member(
            repayment.member,
            title="Repayment Rejected",
            message=(
                f"Your repayment of {repayment.amount:,.2f} RWF "
                f"was rejected because it exceeds the remaining "
                f"loan balance."
            ),
            notification_type="REPAYMENT",
        )

        messages.error(
            request,
            "Repayment was rejected because it exceeds "
            "the remaining loan balance."
        )

        return redirect("repayment_pending")

    # Approve repayment.
    repayment.status = "APPROVED"
    repayment.approved_by = request.user
    repayment.approved_at = timezone.now()

    repayment.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    notify_member(
        repayment.member,
        title="Repayment Approved",
        message=(
            f"Your repayment of {repayment.amount:,.2f} RWF "
            f"for loan #{loan.id} has been approved."
        ),
        notification_type="REPAYMENT",
    )
    
    # Check whether the loan is now fully paid.
    if loan.is_fully_paid:
        loan.status = "COMPLETED"
        loan.completed_at = timezone.now()

        loan.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        notify_member(
            repayment.member,
            title="Loan Completed",
            message=(
                f"Your loan #{loan.id} has been fully paid "
                f"and marked as completed."
            ),
            notification_type="LOAN",
        )

    messages.success(
        request,
        "Repayment approved successfully."
    )

    return redirect("repayment_pending")


@login_required
def repayment_reject(request, pk):
    """
    Reject a pending repayment.
    """

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can reject repayments."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    repayment = get_object_or_404(
        LoanRepayment,
        pk=pk,
        status="PENDING",
    )

    reason = request.POST.get(
        "reason",
        "Repayment rejected.",
    ).strip()

    repayment.status = "REJECTED"
    repayment.rejection_reason = reason
    repayment.approved_by = request.user
    repayment.approved_at = timezone.now()

    repayment.save(
        update_fields=[
            "status",
            "rejection_reason",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )
    notify_member(
        repayment.member,
        title="Repayment Rejected",
        message=(
            f"Your repayment of {repayment.amount:,.2f} RWF "
            f"for loan #{repayment.loan_id} was rejected. "
            f"Reason: {reason}"
        ),
        notification_type="REPAYMENT",
    )

    messages.success(
        request,
        "Repayment rejected successfully."
    )

    return redirect("repayment_pending")