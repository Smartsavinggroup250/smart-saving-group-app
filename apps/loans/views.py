from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from apps.notifications.services import (
    notify_admins_and_treasurers,
    notify_member,
)

from .forms import LoanApplicationForm
from .models import (
    Loan,
    get_interest_rate,
    get_loan_type,
)


# ============================================================
# ROLE CHECK
# ============================================================

def is_admin_or_treasurer(user):
    """
    Check whether the logged-in user is
    Admin or Treasurer.
    """

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    role = getattr(
        getattr(user, "profile", None),
        "role",
        None,
    )

    return role in [
        "ADMIN",
        "TREASURER",
    ]


# ============================================================
# ACTIVE LOAN CHECK
# ============================================================

def has_active_loan(member):
    """
    Check whether a member already has
    an active loan.
    """

    return Loan.objects.filter(
        member=member,
        status__in=[
            "APPROVED",
            "DISBURSED",
        ],
    ).exists()


# ============================================================
# APPLY FOR LOAN
# ============================================================

@login_required
def loan_apply(request):

    member = getattr(
        request.user,
        "member",
        None
    )

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    # Prevent multiple active loans
    if has_active_loan(member):

        messages.warning(
            request,
            "You already have an active loan."
        )

        return redirect("loan_list")

    if request.method == "POST":

        form = LoanApplicationForm(
            request.POST
        )

        if form.is_valid():

            loan = form.save(
                commit=False
            )

            # Assign member
            loan.member = member

            # Determine loan type automatically
            loan.loan_type = get_loan_type(
                loan.requested_amount
            )

            # Determine interest rate automatically
            loan.interest_rate = get_interest_rate(
                loan.loan_type
            )

            # Initial status
            loan.status = "PENDING"

            # Save
            loan.save()
            notify_member(
                member,
                title="Loan Application Submitted",
                message=(
                    f"Your loan application of "
                    f"{loan.requested_amount:,.2f} RWF has been submitted "
                    f"successfully. "
                    f"Your application is currently awaiting approval."
                ),
                notification_type="LOAN",
            )
            notify_admins_and_treasurers(
                title="New Loan Application",
                message=(
                    f"{request.user.get_full_name() or request.user.username} "
                    f"has submitted a loan application of "
                    f"{loan.requested_amount:,.2f} RWF. "
                    f"Please review and process the application."
                ),
                notification_type="LOAN",
            )

            messages.success(
                request,
                "Your loan application has been submitted successfully."
            )

            return redirect(
                "loan_list"
            )

    else:

        form = LoanApplicationForm()

    return render(
        request,
        "loans/loan_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# MEMBER LOAN LIST
# ============================================================

@login_required
def loan_list(request):

    member = getattr(
        request.user,
        "member",
        None
    )

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    loans = Loan.objects.filter(
        member=member
    ).order_by(
        "-application_date"
    )

    return render(
        request,
        "loans/loan_list.html",
        {
            "loans": loans,
        },
    )


# ============================================================
# PENDING LOANS
# ============================================================

@login_required
def loan_pending(request):

    if not is_admin_or_treasurer(
        request.user
    ):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can access this page."
        )

    loans = Loan.objects.filter(
        status="PENDING"
    ).select_related(
        "member",
        "member__user",
    )

    return render(
        request,
        "loans/loan_pending.html",
        {
            "loans": loans,
        },
    )


# ============================================================
# APPROVE LOAN
# ============================================================

@login_required
@transaction.atomic
def loan_approve(request, pk):

    if not is_admin_or_treasurer(
        request.user
    ):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can approve loans."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    loan = get_object_or_404(
        Loan.objects.select_for_update(),
        pk=pk,
    )

    # Make sure the loan is still pending
    if loan.status != "PENDING":

        messages.warning(
            request,
            "This loan has already been processed."
        )

        return redirect(
            "loan_pending"
        )

    # Set approved amount
    loan.approved_amount = (
        loan.requested_amount
    )

    # Recalculate type and interest rate
    loan.loan_type = get_loan_type(
        loan.approved_amount
    )

    loan.interest_rate = get_interest_rate(
        loan.loan_type
    )

    # Approval information
    loan.status = "APPROVED"

    loan.approved_by = request.user

    loan.approved_at = timezone.now()

    loan.save(
        update_fields=[
            "approved_amount",
            "loan_type",
            "interest_rate",
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    notify_member(
        loan.member,
        title="Loan Approved",
        message=(
            f"Your loan application has been approved. "
            f"Approved amount: {loan.approved_amount:,.2f} RWF. "
            f"Loan type: {loan.loan_type}. "
            f"Interest rate: {loan.interest_rate}% per month."
        ),
        notification_type="LOAN",
    )

    messages.success(
        request,
        "Loan approved successfully."
    )
    return redirect(
        "loan_pending"
    )


# ============================================================
# REJECT LOAN
# ============================================================

@login_required
def loan_reject(request, pk):

    if not is_admin_or_treasurer(
        request.user
    ):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can reject loans."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    loan = get_object_or_404(
        Loan,
        pk=pk,
        status="PENDING",
    )

    reason = request.POST.get(
        "reason",
        "Loan application rejected."
    ).strip()

    loan.status = "REJECTED"

    loan.rejection_reason = reason

    loan.approved_by = request.user

    loan.approved_at = timezone.now()

    loan.save(
        update_fields=[
            "status",
            "rejection_reason",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    notify_member(
        loan.member,
        title="Loan Rejected",
        message=(
            f"Your loan application of "
            f"{loan.requested_amount:,.2f} RWF has been rejected. "
            f"Reason: {reason}"
        ),
        notification_type="LOAN",
    )

    messages.success(
        request,
        "Loan rejected successfully."
    )

    return redirect(
        "loan_pending"
    )


# ============================================================
# DISBURSE LOAN
# ============================================================

@login_required
@transaction.atomic
def loan_disburse(request, pk):

    if not is_admin_or_treasurer(
        request.user
    ):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can disburse loans."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    loan = get_object_or_404(
        Loan.objects.select_for_update(),
        pk=pk,
    )

    # Only approved loans can be disbursed
    if loan.status != "APPROVED":

        messages.warning(
            request,
            "Only approved loans can be disbursed."
        )

        return redirect(
            "loan_list"
        )

    loan.status = "DISBURSED"

    loan.disbursed_at = timezone.now()

    loan.save(
        update_fields=[
            "status",
            "disbursed_at",
            "updated_at",
        ]
    )

    notify_member(
        loan.member,
        title="Loan Disbursed",
        message=(
            f"Your loan of "
            f"{loan.approved_amount:,.2f} RWF has been disbursed successfully."
        ),
        notification_type="LOAN",
    )

    messages.success(
        request,
        "Loan disbursed successfully."
    )
    return redirect(
        "loan_list"
    )
    
@login_required
def active_loan_members(request):
    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "You are not allowed to view this page."
        )

    loans = (
        Loan.objects
        .filter(status__in=["APPROVED", "DISBURSED"])
        .select_related("member", "member__user")
        .order_by("-approved_at", "-application_date")
    )

    # Pagination: 10 loans per page
    paginator = Paginator(loans, 10)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "loans/active_loan_members.html",
        {
            "loans": page_obj,
            "page_obj": page_obj,
        },
    )