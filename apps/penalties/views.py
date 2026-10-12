from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from apps.members.models import Member

from .forms import PenaltyPaymentForm
from .models import Penalty, PenaltyPayment


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
        None
    )

    return role in ["ADMIN", "TREASURER"]


@login_required
def penalty_list(request):
    member = get_object_or_404(
        Member,
        user=request.user
    )

    penalties = Penalty.objects.filter(
        member=member
    ).order_by("-issued_at")

    return render(
        request,
        "penalties/penalty_list.html",
        {
            "penalties": penalties,
        }
    )


@login_required
def penalty_pay(request, penalty_id):

    member = get_object_or_404(
        Member,
        user=request.user
    )

    penalty = get_object_or_404(
        Penalty,
        id=penalty_id,
        member=member,
    )

    if penalty.status in ["PAID", "WAIVED"]:
        messages.error(
            request,
            "This penalty cannot be paid."
        )
        return redirect("penalty_list")

    existing_payment = PenaltyPayment.objects.filter(
        penalty=penalty,
        status="PENDING",
    ).first()

    if existing_payment:
        messages.warning(
            request,
            "A payment for this penalty is already pending approval."
        )
        return redirect("penalty_list")

    if request.method == "POST":

        form = PenaltyPaymentForm(
            request.POST,
            penalty=penalty,
        )

        if form.is_valid():

            with transaction.atomic():

                payment = form.save(commit=False)

                payment.penalty = penalty
                payment.member = member
                payment.requested_by = request.user
                payment.status = "PENDING"

                payment.save()

                notify_member(
                    member,
                    title="Penalty Payment Submitted",
                    message=(
                        f"Your penalty payment request of "
                        f"{payment.amount:,.2f} RWF has been submitted successfully. "
                        f"Your payment is currently awaiting approval."
                    ),
                    notification_type="PENALTY",
                )
                
                notify_admins_and_treasurers(
                    title="New Penalty Payment Request",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} "
                        f"has submitted a penalty payment of "
                        f"{payment.amount:,.2f} RWF "
                        f"for penalty #{penalty.id}. "
                        f"Please review and process the payment."
                    ),
                    notification_type="PENALTY",
                )

                messages.success(
                    request,
                    "Penalty payment submitted successfully. "
                    "It is waiting for approval."
                )

            return redirect("penalty_list")

    else:

        form = PenaltyPaymentForm(
            penalty=penalty
        )

    return render(
        request,
        "penalties/penalty_payment_form.html",
        {
            "form": form,
            "penalty": penalty,
        }
    )
    
@login_required
def penalty_payment_pending(request):

    if not is_admin_or_treasurer(request.user):
        messages.error(
            request,
            "You are not authorized to access this page."
        )
        return redirect("dashboard")

    payments = PenaltyPayment.objects.filter(
        status="PENDING"
    ).select_related(
        "penalty",
        "member",
        "member__user",
    ).order_by("-payment_date")

    return render(
        request,
        "penalties/penalty_payment_pending.html",
        {
            "payments": payments,
        }
    )
    
@login_required
def penalty_payment_approve(request, payment_id):

    if not is_admin_or_treasurer(request.user):
        messages.error(
            request,
            "You are not authorized to approve payments."
        )
        return redirect("dashboard")

    if request.method != "POST":
        messages.error(
            request,
            "Invalid request method."
        )
        return redirect("penalty_payment_pending")

    with transaction.atomic():

        payment = get_object_or_404(
            PenaltyPayment.objects.select_for_update(),
            id=payment_id,
        )

        penalty = get_object_or_404(
            Penalty.objects.select_for_update(),
            id=payment.penalty_id,
        )

        if payment.status != "PENDING":
            messages.error(
                request,
                "This payment has already been processed."
            )
            return redirect("penalty_payment_pending")

        if penalty.status == "PAID":
            messages.error(
                request,
                "This penalty has already been paid."
            )
            return redirect("penalty_payment_pending")

        if penalty.status == "WAIVED":
            messages.error(
                request,
                "This penalty has been waived."
            )
            return redirect("penalty_payment_pending")

        # Make sure payment belongs to the penalty
        if payment.member_id != penalty.member_id:
            messages.error(
                request,
                "Invalid penalty payment."
            )
            return redirect("penalty_payment_pending")

        # Make sure amount is exactly the penalty amount
        if payment.amount != penalty.amount:
            messages.error(
                request,
                "Payment amount does not match the penalty amount."
            )
            return redirect("penalty_payment_pending")

        payment.status = "APPROVED"
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        penalty.status = "PAID"
        penalty.paid_at = timezone.now()
        penalty.save(
            update_fields=[
                "status",
                "paid_at",
                "updated_at",
            ]
        )
        
        notify_member(
            payment.member,
            title="Penalty Payment Approved",
            message=(
                f"Your penalty payment of "
                f"{payment.amount:,.2f} RWF for penalty "
                f"#{penalty.id} has been approved. "
                f"The penalty has been marked as paid."
            ),
            notification_type="PENALTY",
        )

    messages.success(
        request,
        "Penalty payment approved successfully."
    )

    return redirect("penalty_payment_pending")        

@login_required
def penalty_payment_reject(request, payment_id):

    if not is_admin_or_treasurer(request.user):
        messages.error(
            request,
            "You are not authorized to reject payments."
        )
        return redirect("dashboard")

    if request.method != "POST":
        messages.error(
            request,
            "Invalid request method."
        )
        return redirect("penalty_payment_pending")

    payment = get_object_or_404(
        PenaltyPayment,
        id=payment_id,
        status="PENDING",
    )

    reason = request.POST.get("reason", "").strip()

    if len(reason) < 3:
        messages.error(
            request,
            "Please provide a rejection reason of at least 3 characters."
        )
        return redirect("penalty_payment_pending")

    payment.rejection_reason = reason
    
    payment.status = "REJECTED"
    payment.approved_by = request.user
    payment.approved_at = timezone.now()

    payment.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    
    notify_member(
        payment.member,
        title="Penalty Payment Rejected",
        message=(
            f"Your penalty payment of "
            f"{payment.amount:,.2f} RWF for penalty "
            f"#{payment.penalty_id} was rejected. "
            f"Reason: {payment.rejection_reason}"
        ),
        notification_type="PENALTY",
    )

    messages.success(
        request,
        "Penalty payment rejected."
    )

    return redirect("penalty_payment_pending")

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

@login_required
def members_with_penalties(request):

    if not is_admin_or_treasurer(request.user):
        return HttpResponseForbidden(
            "You are not allowed to view this page."
        )

    penalties = (
        Penalty.objects
        .filter(status__in=["PENDING", "PAID"])
        .select_related(
            "member",
            "member__user",
        )
        .order_by("-issued_at")
    )

    paginator = Paginator(penalties, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "penalties/members_with_penalties.html",
        {
            "penalties": page_obj,
            "page_obj": page_obj,
        },
    )    