from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from .forms import MonthlyContributionForm
from .models import MonthlyContribution, SavingsTransaction
from apps.notifications.services import (
    notify_admins_and_treasurers,
    notify_member,
)



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
def contribution_create(request):

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    if request.method == "POST":
        form = MonthlyContributionForm(request.POST)

        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.member = member
            contribution.requested_by = request.user
            contribution.status = "PENDING"
            contribution.save()

            # Notify the member that the contribution request was submitted
            notify_member(
                member,
                title="Contribution Request Submitted",
                message=(
                    f"Your monthly contribution request for "
                    f"{contribution.month:%B %Y} has been submitted successfully. "
                    f"Amount: {contribution.amount:,.2f} RWF. "
                    f"Your request is currently awaiting approval."
                ),
                notification_type="CONTRIBUTION",
            )

            # Notify Admin and Treasurer that a new request needs approval
            notify_admins_and_treasurers(
                title="New Contribution Request",
                message=(
                    f"{request.user.get_full_name() or request.user.username} "
                    f"has submitted a monthly contribution request of "
                    f"{contribution.amount:,.2f} RWF for "
                    f"{contribution.month:%B %Y}. "
                    f"Please review and process the request."
                ),
                notification_type="CONTRIBUTION",
            )

            messages.success(
                request,
                "Your monthly contribution request has been submitted successfully."
            )

            return redirect("contribution_list")
    else:
        form = MonthlyContributionForm()

    return render(
        request,
        "savings/contribution_form.html",
        {"form": form},
    )


@login_required
def contribution_edit(request, pk):
    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    contribution = get_object_or_404(
        MonthlyContribution,
        pk=pk,
        member=member,
        status="REJECTED",
    )

    if request.method == "POST":
        form = MonthlyContributionForm(
            request.POST,
            instance=contribution,
        )

        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.status = "PENDING"
            contribution.rejection_reason = ""
            contribution.approved_by = None
            contribution.approved_at = None
            contribution.requested_by = request.user
            contribution.save()

            notify_member(
                member,
                title="Contribution Resubmitted",
                message=(
                    f"Your corrected contribution for "
                    f"{contribution.month:%B %Y} has been resubmitted "
                    "and is awaiting approval."
                ),
                notification_type="CONTRIBUTION",
            )

            notify_admins_and_treasurers(
                title="Contribution Resubmitted",
                message=(
                    f"{request.user.get_full_name() or request.user.username} "
                    f"has resubmitted a contribution of "
                    f"{contribution.amount:,.2f} RWF for "
                    f"{contribution.month:%B %Y}. Please review it."
                ),
                notification_type="CONTRIBUTION",
            )

            messages.success(
                request,
                "Contribution corrected and resubmitted successfully.",
            )
            return redirect("contribution_list")
    else:
        form = MonthlyContributionForm(instance=contribution)

    return render(
        request,
        "savings/contribution_form.html",
        {
            "form": form,
            "edit_mode": True,
            "contribution": contribution,
        },
    )


@login_required
def contribution_delete(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    contribution = get_object_or_404(
        MonthlyContribution,
        pk=pk,
        member=member,
        status="REJECTED",
    )

    contribution.delete()

    messages.success(
        request,
        "Rejected contribution deleted successfully.",
    )
    return redirect("contribution_list")

    
@login_required
def contribution_list(request):

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    contributions = MonthlyContribution.objects.filter(
        member=member
    ).order_by("-month", "-created_at")

    return render(
        request,
        "savings/contribution_list.html",
        {
            "contributions": contributions,
        },
    )
    
@login_required
def contribution_pending(request):

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can access this page."
        )

    contributions = MonthlyContribution.objects.filter(
        status="PENDING"
    ).select_related(
        "member",
        "member__user",
        "requested_by",
    )

    return render(
        request,
        "savings/contribution_pending.html",
        {
            "contributions": contributions,
        },
    )
    
@login_required
@transaction.atomic
def contribution_approve(request, pk):

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can approve contributions."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    contribution = get_object_or_404(
        MonthlyContribution.objects.select_for_update(),
        pk=pk,
    )

    if contribution.status != "PENDING":
        messages.warning(
            request,
            "This contribution has already been processed."
        )
        return redirect("contribution_pending")

    # Make sure the member does not already have
    # an approved contribution for the same month.
    duplicate = MonthlyContribution.objects.filter(
        member=contribution.member,
        month=contribution.month,
        status="APPROVED",
    ).exclude(
        pk=contribution.pk
    ).exists()

    if duplicate:
        contribution.status = "REJECTED"
        contribution.rejection_reason = (
            "An approved contribution already exists for this month."
        )
        contribution.save(
            update_fields=[
                "status",
                "rejection_reason",
                "updated_at",
            ]
        )

        notify_member(
            contribution.member,
            title="Contribution Rejected",
            message=(
                f"Your monthly contribution request for "
                f"{contribution.month:%B %Y} was rejected because "
                f"an approved contribution already exists for this month."
            ),
            notification_type="CONTRIBUTION",
        )

        
        messages.error(
            request,
            "This member already has an approved contribution for this month."
        )

        return redirect("contribution_pending")

    contribution.status = "APPROVED"
    contribution.approved_by = request.user
    contribution.approved_at = timezone.now()
    contribution.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )
    notify_member(
        contribution.member,
        title="Contribution Approved",
        message=(
            f"Your monthly contribution of "
            f"{contribution.amount:,.2f} RWF for "
            f"{contribution.month:%B %Y} has been approved "
            f"by {request.user.get_full_name() or request.user.username}."
        ),
        notification_type="CONTRIBUTION",
    )

    SavingsTransaction.objects.create(
        member=contribution.member,
        contribution=contribution,
        transaction_type="CONTRIBUTION",
        amount=contribution.amount,
        reference=f"CONTR-{contribution.id}",
        description=(
            f"Monthly contribution for "
            f"{contribution.month:%B %Y}"
        ),
        created_by=request.user,
    )

    messages.success(
        request,
        "Contribution approved successfully."
    )

    return redirect("contribution_pending")

@login_required
def contribution_reject(request, pk):

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "Only Admin or Treasurer can reject contributions."
        )

    if request.method != "POST":
        return HttpResponseForbidden(
            "Invalid request method."
        )

    contribution = get_object_or_404(
        MonthlyContribution,
        pk=pk,
        status="PENDING",
    )

    reason = request.POST.get("reason", "").strip()

    if len(reason) < 3:
        messages.error(
            request,
            "Please provide a rejection reason of at least 3 characters."
        )
        return redirect("contribution_pending")

    contribution.status = "REJECTED"
    contribution.rejection_reason = reason
    contribution.approved_by = request.user
    contribution.approved_at = timezone.now()

    contribution.save(
        update_fields=[
            "status",
            "rejection_reason",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )

    notify_member(
        contribution.member,
        title="Contribution Rejected",
        message=(
            f"Your monthly contribution request for "
            f"{contribution.month:%B %Y} was rejected. "
            f"Reason: {reason}"
        ),
        notification_type="CONTRIBUTION",
    )
     
    messages.success(
        request,
        "Contribution rejected."
    )

    return redirect("contribution_pending")

@login_required
def savings_balance(request):

    member = getattr(request.user, "member", None)

    if not member:
        return HttpResponseForbidden(
            "You do not have a member profile."
        )

    transactions = SavingsTransaction.objects.filter(
        member=member
    )

    balance = sum(
        transaction.amount
        for transaction in transactions
    )

    return render(
        request,
        "savings/balance.html",
        {
            "balance": balance,
            "transactions": transactions,
        },
    )
    
@login_required
def paid_contribution_list(request):

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "You are not allowed to view this page."
        )

    contributions = (
        MonthlyContribution.objects
        .filter(status="APPROVED")
        .select_related(
            "member",
            "member__user",
            "approved_by",
        )
        .order_by(
            "-approved_at",
            "-month",
        )
    )

    # ========================================================
    # PAGINATION
    # 10 CONTRIBUTIONS PER PAGE
    # ========================================================

    paginator = Paginator(
        contributions,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "savings/paid_contribution_list.html",
        {
            "contributions": page_obj,
            "page_obj": page_obj,
        },
    )