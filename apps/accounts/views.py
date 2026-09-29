from decimal import Decimal
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from apps.members.models import Member
from apps.savings.models import MonthlyContribution, SavingsTransaction
from apps.loans.models import Loan
from apps.repayments.models import LoanRepayment
from apps.penalties.models import Penalty, PenaltyPayment

# ======================================================
# LOGOUT
# ======================================================

@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")
# ======================================================
# REPORTS
# ======================================================

@login_required
def reports(request):
    from apps.savings.models import MonthlyContribution
    from apps.loans.models import Loan
    from apps.repayments.models import LoanRepayment
    from apps.penalties.models import PenaltyPayment

    transactions = []

    # --------------------------------------------------
    # Approved Contributions
    # --------------------------------------------------

    contributions = MonthlyContribution.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for contribution in contributions:
        transactions.append({
            "date": contribution.approved_at or contribution.updated_at,
            "member_id": contribution.member.member_number,
            "reason": "Pay Contribution",
            "amount": contribution.amount,
            "status": "Approved",
        })

    # --------------------------------------------------
    # Approved Loan Repayments
    # --------------------------------------------------

    repayments = LoanRepayment.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for repayment in repayments:
        transactions.append({
            "date": repayment.approved_at or repayment.updated_at,
            "member_id": repayment.member.member_number,
            "reason": "Loan Repayment",
            "amount": repayment.amount,
            "status": "Approved",
        })

    # --------------------------------------------------
    # Approved Penalty Payments
    # --------------------------------------------------

    penalty_payments = PenaltyPayment.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for payment in penalty_payments:
        transactions.append({
            "date": payment.approved_at or payment.updated_at,
            "member_id": payment.member.member_number,
            "reason": "Pay Penalty",
            "amount": payment.amount,
            "status": "Approved",
        })

    # --------------------------------------------------
    # Approved Loan Requests
    # --------------------------------------------------

    loans = Loan.objects.filter(
        status__in=[
            "APPROVED",
            "DISBURSED",
            "COMPLETED",
        ]
    ).select_related("member")

    for loan in loans:
        transactions.append({
            "date": loan.approved_at or loan.updated_at,
            "member_id": loan.member.member_number,
            "reason": "Loan Request",
            "amount": loan.approved_amount or loan.requested_amount,
            "status": "Approved",
        })

    # --------------------------------------------------
    # Newest transactions first
    # --------------------------------------------------

    transactions.sort(
        key=lambda transaction: transaction["date"],
        reverse=True
    )

    # ======================================================
    # PAGINATION
    # 10 transactions per page
    # ======================================================

    paginator = Paginator(transactions, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "accounts/reports.html",
        {
            "transactions": page_obj,
            "page_obj": page_obj,
        },
    )


# ======================================================
# DASHBOARD
# ======================================================

@login_required
def dashboard(request):

    user = request.user

    # --------------------------------------------------
    # SUPERUSER / ADMIN
    # --------------------------------------------------

    if user.is_superuser:

        context = get_management_dashboard_data()

        return render(
            request,
            "dashboard/admin.html",
            context
        )

    role = getattr(
        getattr(user, "profile", None),
        "role",
        None
    )

    # --------------------------------------------------
    # ADMIN
    # --------------------------------------------------

    if role == "ADMIN":

        context = get_management_dashboard_data()

        return render(
            request,
            "dashboard/admin.html",
            context
        )

    # --------------------------------------------------
    # TREASURER
    # --------------------------------------------------

    elif role == "TREASURER":

        context = get_management_dashboard_data()

        return render(
            request,
            "dashboard/treasurer.html",
            context
        )

    # --------------------------------------------------
    # MEMBER
    # --------------------------------------------------

    elif role == "MEMBER":

        member = getattr(user, "member", None)

        if not member:
            return redirect("login")

        context = get_member_dashboard_data(member)

        return render(
            request,
            "dashboard/member.html",
            context
        )

    # --------------------------------------------------
    # AUDITOR
    # --------------------------------------------------

    elif role == "AUDITOR":

        context = get_management_dashboard_data()

        return render(
            request,
            "dashboard/auditor.html",
            context
        )

    return redirect("login")


# ======================================================
# MANAGEMENT DASHBOARD
# ADMIN + TREASURER
# ======================================================

def get_management_dashboard_data():

    # ==================================================
    # MEMBERS
    # ==================================================

    total_members = Member.objects.count()

    active_members = Member.objects.filter(
        status="ACTIVE"
    ).count()

    total_shares = (
        Member.objects.aggregate(
            total=Sum("shares")
        )["total"]
        or 0
    )

    # ==================================================
    # TOTAL SAVINGS
    # Approved contributions only
    # ==================================================

    total_savings = (
        SavingsTransaction.objects.filter(
            transaction_type="CONTRIBUTION"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # ACTIVE LOANS
    # ==================================================

    active_loan_queryset = Loan.objects.filter(
        status__in=[
            "APPROVED",
            "DISBURSED",
        ]
    )

    active_loans = active_loan_queryset.count()

    # --------------------------------------------------
    # Total outstanding amount of active loans
    # --------------------------------------------------

    outstanding_loans = sum(
        (
            loan.remaining_balance
            for loan in active_loan_queryset
        ),
        Decimal("0.00")
    )

    # ==================================================
    # TOTAL PROFITS
    #
    # Interest generated from all approved loans
    # ==================================================

    approved_loans = Loan.objects.filter(
        status__in=[
            "APPROVED",
            "DISBURSED",
            "COMPLETED",
        ]
    )

    total_profits = sum(
        (
            loan.total_interest
            for loan in approved_loans
        ),
        Decimal("0.00")
    )

    # ==================================================
    # PENDING LOANS
    #
    # Loans requested by members waiting for approval
    # ==================================================

    pending_loans = Loan.objects.filter(
        status="PENDING"
    ).count()

    # ==================================================
    # PENDING CONTRIBUTIONS
    #
    # Contributions paid by members waiting for approval
    # ==================================================

    pending_contributions = MonthlyContribution.objects.filter(
        status="PENDING"
    ).count()

    # ==================================================
    # PENDING REPAYMENTS
    #
    # Loan repayments submitted by members
    # waiting for approval
    # ==================================================

    pending_repayments = LoanRepayment.objects.filter(
        status="PENDING"
    ).count()

    # ==================================================
    # TOTAL PENALTIES
    #
    # All penalties:
    # PENDING + PAID
    # ==================================================

    total_penalties = (
        Penalty.objects.filter(
            status__in=[
                "PENDING",
                "PAID",
            ]
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # UNPAID PENALTIES
    #
    # Penalties that are still unpaid
    # ==================================================

    unpaid_penalties = (
        Penalty.objects.filter(
            status="PENDING"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # Number of unpaid penalties
    unpaid_penalty_count = Penalty.objects.filter(
        status="PENDING"
    ).count()

    # ==================================================
    # PENDING PENALTY PAYMENTS
    #
    # Penalty payments submitted by members
    # waiting for approval
    # ==================================================

    pending_penalty_payments = PenaltyPayment.objects.filter(
        status="PENDING"
    ).count()

    # ==================================================
    # GROUP BALANCE
    #
    # Total Savings
    # + Total Profits
    # + Total Penalties
    # - Active Loans Outstanding
    # - Unpaid Penalties
    # ==================================================

    group_balance = (
        total_savings
        + total_profits
        + total_penalties
        - outstanding_loans
        - unpaid_penalties
    )

    # ==================================================
    # RETURN DATA
    # ==================================================

    return {

        # ------------------------------------------------
        # MAIN CARDS
        # ------------------------------------------------

        "total_savings": total_savings,

        "total_profits": total_profits,

        "total_penalties": total_penalties,

        "active_loans": active_loans,

        "outstanding_loans": outstanding_loans,

        "group_balance": group_balance,

        "unpaid_penalties": unpaid_penalties,

        "unpaid_penalty_count": unpaid_penalty_count,

        "total_members": total_members,

        "active_members": active_members,

        "total_shares": total_shares,

        # ------------------------------------------------
        # QUICK ACTIONS
        # ------------------------------------------------

        "pending_loans": pending_loans,

        "pending_contributions": pending_contributions,

        "pending_repayments": pending_repayments,

        "pending_penalty_payments": pending_penalty_payments,
    }


# ======================================================
# MEMBER DASHBOARD
# ======================================================

def get_member_dashboard_data(member):

    # ==================================================
    # GROUP TOTAL SAVINGS
    # ==================================================

    total_savings = (
        SavingsTransaction.objects.filter(
            transaction_type="CONTRIBUTION"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # GROUP ACTIVE LOANS
    # ==================================================

    active_loan_queryset = Loan.objects.filter(
        status__in=[
            "APPROVED",
            "DISBURSED",
        ]
    )

    active_loans = active_loan_queryset.count()

    # --------------------------------------------------
    # Outstanding amount of active loans
    # --------------------------------------------------

    outstanding_loans = sum(
        (
            loan.remaining_balance
            for loan in active_loan_queryset
        ),
        Decimal("0.00")
    )

    # ==================================================
    # GROUP TOTAL PROFITS
    # ==================================================

    approved_loans = Loan.objects.filter(
        status__in=[
            "APPROVED",
            "DISBURSED",
            "COMPLETED",
        ]
    )

    total_profits = sum(
        (
            loan.total_interest
            for loan in approved_loans
        ),
        Decimal("0.00")
    )

    # ==================================================
    # GROUP TOTAL PENALTIES
    #
    # Paid + unpaid penalties
    # ==================================================

    total_penalties = (
        Penalty.objects.filter(
            status__in=[
                "PENDING",
                "PAID",
            ]
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # GROUP UNPAID PENALTIES
    # ==================================================

    unpaid_penalties = (
        Penalty.objects.filter(
            status="PENDING"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # GROUP BALANCE
    # ==================================================

    group_balance = (
        total_savings
        + total_profits
        + total_penalties
        - outstanding_loans
        - unpaid_penalties
    )

    # ==================================================
    # MY SAVINGS
    # ==================================================

    my_savings = (
        SavingsTransaction.objects.filter(
            member=member,
            transaction_type="CONTRIBUTION"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==================================================
    # MY PENALTIES
    # ==================================================

    my_total_penalties = (
        Penalty.objects.filter(
            member=member,
            status__in=[
                "PENDING",
                "PAID",
            ]
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # --------------------------------------------------
    # My unpaid penalties
    # --------------------------------------------------

    my_unpaid_penalties = (
        Penalty.objects.filter(
            member=member,
            status="PENDING"
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # Number of my unpaid penalties
    my_unpaid_penalty_count = Penalty.objects.filter(
        member=member,
        status="PENDING"
    ).count()

    # ==================================================
    # MY ACTIVE LOANS
    # ==================================================

    my_active_loans = Loan.objects.filter(
        member=member,
        status__in=[
            "APPROVED",
            "DISBURSED",
        ]
    )

    my_active_loan_count = my_active_loans.count()

    # --------------------------------------------------
    # My loan outstanding balance
    # --------------------------------------------------

    my_loan_balance = sum(
        (
            loan.remaining_balance
            for loan in my_active_loans
        ),
        Decimal("0.00")
    )

    # ==================================================
    # RETURN DATA
    # ==================================================

    return {

        # ------------------------------------------------
        # GROUP CARDS
        # ------------------------------------------------

        "total_savings": total_savings,

        "total_profits": total_profits,

        "total_penalties": total_penalties,

        "active_loans": active_loans,

        "outstanding_loans": outstanding_loans,

        "group_balance": group_balance,

        # ------------------------------------------------
        # MY CARDS
        # ------------------------------------------------

        "my_savings": my_savings,

        "my_total_penalties": my_total_penalties,

        "my_unpaid_penalties": my_unpaid_penalties,

        "my_unpaid_penalty_count": my_unpaid_penalty_count,

        "my_active_loan_count": my_active_loan_count,

        "my_loan_balance": my_loan_balance,
    }