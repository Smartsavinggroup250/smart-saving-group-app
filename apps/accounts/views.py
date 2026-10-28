
from decimal import Decimal
from datetime import date, datetime, time

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.accounts.models import MonthlyReportBalance
from apps.members.models import Member
from apps.savings.models import MonthlyContribution, SavingsTransaction
from apps.loans.models import Loan
from apps.repayments.models import LoanRepayment
from apps.penalties.models import Penalty, PenaltyPayment

from io import BytesIO

from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
import os
from urllib.parse import unquote





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
    transactions = []

    # APPROVED CONTRIBUTIONS
    contributions = MonthlyContribution.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for contribution in contributions:
        transactions.append({
            "date": (
                contribution.approved_at
                or getattr(contribution, "updated_at", None)
                or contribution.month
            ),
            "member_id": contribution.member.member_number,
            "reason": "Pay Contribution",
            "amount": contribution.amount,
            "status": "Approved",
        })

    # APPROVED LOAN REPAYMENTS
    repayments = LoanRepayment.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for repayment in repayments:
        transactions.append({
            "date": (
                repayment.approved_at
                or getattr(repayment, "updated_at", None)
                or repayment.payment_date
            ),
            "member_id": repayment.member.member_number,
            "reason": "Loan Repayment",
            "amount": repayment.amount,
            "status": "Approved",
        })

    # APPROVED PENALTY PAYMENTS
    penalty_payments = PenaltyPayment.objects.filter(
        status="APPROVED"
    ).select_related("member")

    for payment in penalty_payments:
        transactions.append({
            "date": (
                getattr(payment, "approved_at", None)
                or getattr(payment, "updated_at", None)
                or payment.payment_date
            ),
            "member_id": payment.member.member_number,
            "reason": "Pay Penalty",
            "amount": payment.amount,
            "status": "Approved",
        })

    # APPROVED / DISBURSED / COMPLETED LOANS
    loans = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED", "COMPLETED"]
    ).select_related("member")

    for loan in loans:
        transactions.append({
            "date": (
                loan.disbursed_at
                or loan.approved_at
                or loan.application_date
            ),
            "member_id": loan.member.member_number,
            "reason": "Loan Request",
            "amount": loan.approved_amount or loan.requested_amount,
            "status": "Approved",
        })

    # NEWEST TRANSACTIONS FIRST
    transactions.sort(
        key=lambda transaction: transaction["date"],
        reverse=True,
    )

    # PAGINATION
    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

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

    if user.is_superuser:
        return render(
            request,
            "dashboard/admin.html",
            get_management_dashboard_data(),
        )

    role = getattr(
        getattr(user, "profile", None),
        "role",
        None,
    )

    if role == "ADMIN":
        return render(
            request,
            "dashboard/admin.html",
            get_management_dashboard_data(),
        )

    elif role == "TREASURER":
        return render(
            request,
            "dashboard/treasurer.html",
            get_management_dashboard_data(),
        )

    elif role == "MEMBER":
        member = getattr(user, "member", None)

        if not member:
            return redirect("login")

        return render(
            request,
            "dashboard/member.html",
            get_member_dashboard_data(member),
        )

    elif role == "AUDITOR":
        return render(
            request,
            "dashboard/auditor.html",
            get_management_dashboard_data(),
        )

    return redirect("login")


# ======================================================
# MANAGEMENT DASHBOARD
# ADMIN + TREASURER + AUDITOR
# ======================================================

def get_management_dashboard_data():

    # MEMBERS
    total_members = Member.objects.count()

    active_members = Member.objects.filter(
        status="ACTIVE"
    ).count()

    total_shares = (
        Member.objects.aggregate(total=Sum("shares"))["total"]
        or 0
    )

    # TOTAL SAVINGS
    total_savings = (
        SavingsTransaction.objects.filter(
            transaction_type="CONTRIBUTION"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # ACTIVE LOANS
    active_loan_queryset = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED"]
    )

    active_loans = active_loan_queryset.count()

    outstanding_loans = sum(
        (loan.remaining_balance for loan in active_loan_queryset),
        Decimal("0.00"),
    )

    # TOTAL INTEREST GENERATED
    approved_loans = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED", "COMPLETED"]
    )

    total_profits = sum(
        (loan.total_interest for loan in approved_loans),
        Decimal("0.00"),
    )

    # PENDING TRANSACTIONS
    pending_loans = Loan.objects.filter(
        status="PENDING"
    ).count()

    pending_contributions = MonthlyContribution.objects.filter(
        status="PENDING"
    ).count()

    pending_repayments = LoanRepayment.objects.filter(
        status="PENDING"
    ).count()

    # TOTAL PENALTIES
    total_penalties = (
        Penalty.objects.filter(
            status__in=["PENDING", "PAID"]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # UNPAID PENALTIES
    unpaid_penalties = (
        Penalty.objects.filter(
            status="PENDING"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    unpaid_penalty_count = Penalty.objects.filter(
        status="PENDING"
    ).count()

    pending_penalty_payments = PenaltyPayment.objects.filter(
        status="PENDING"
    ).count()

    # GROUP BALANCE
    group_balance = (
        total_savings
        + total_profits
        + total_penalties
        - outstanding_loans
        - unpaid_penalties
    )

    return {
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
        "pending_loans": pending_loans,
        "pending_contributions": pending_contributions,
        "pending_repayments": pending_repayments,
        "pending_penalty_payments": pending_penalty_payments,
    }


# ======================================================
# MEMBER DASHBOARD
# ======================================================

def get_member_dashboard_data(member):

    # GROUP SAVINGS
    total_savings = (
        SavingsTransaction.objects.filter(
            transaction_type="CONTRIBUTION"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # GROUP ACTIVE LOANS
    active_loan_queryset = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED"]
    )

    active_loans = active_loan_queryset.count()

    outstanding_loans = sum(
        (loan.remaining_balance for loan in active_loan_queryset),
        Decimal("0.00"),
    )

    # GROUP INTEREST
    approved_loans = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED", "COMPLETED"]
    )

    total_profits = sum(
        (loan.total_interest for loan in approved_loans),
        Decimal("0.00"),
    )

    # GROUP PENALTIES
    total_penalties = (
        Penalty.objects.filter(
            status__in=["PENDING", "PAID"]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    unpaid_penalties = (
        Penalty.objects.filter(
            status="PENDING"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # GROUP BALANCE
    group_balance = (
        total_savings
        + total_profits
        + total_penalties
        - outstanding_loans
        - unpaid_penalties
    )

    # MY SAVINGS
    my_savings = (
        SavingsTransaction.objects.filter(
            member=member,
            transaction_type="CONTRIBUTION",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # MY PENALTIES
    my_total_penalties = (
        Penalty.objects.filter(
            member=member,
            status__in=["PENDING", "PAID"],
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    my_unpaid_penalties = (
        Penalty.objects.filter(
            member=member,
            status="PENDING",
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    my_unpaid_penalty_count = Penalty.objects.filter(
        member=member,
        status="PENDING",
    ).count()

    # MY ACTIVE LOANS
    my_active_loans = Loan.objects.filter(
        member=member,
        status__in=["APPROVED", "DISBURSED"],
    )

    my_active_loan_count = my_active_loans.count()

    my_loan_balance = sum(
        (loan.remaining_balance for loan in my_active_loans),
        Decimal("0.00"),
    )

    return {
        "total_savings": total_savings,
        "total_profits": total_profits,
        "total_penalties": total_penalties,
        "active_loans": active_loans,
        "outstanding_loans": outstanding_loans,
        "group_balance": group_balance,
        "my_savings": my_savings,
        "my_total_penalties": my_total_penalties,
        "my_unpaid_penalties": my_unpaid_penalties,
        "my_unpaid_penalty_count": my_unpaid_penalty_count,
        "my_active_loan_count": my_active_loan_count,
        "my_loan_balance": my_loan_balance,
    }


# ======================================================
# MONTHLY FINANCIAL REPORT
# Report month becomes available on the 6th.
# Contribution deadline: 5th of the following month.
# ======================================================

@login_required
def monthly_report(request):

    today = timezone.localdate()
    current_month_start = date(today.year, today.month, 1)

    # Determine the most recently completed contribution month.
    previous_calendar_month = (
        current_month_start - timezone.timedelta(days=1)
    ).replace(day=1)

    if today.day >= 6:
        default_month = previous_calendar_month
    else:
        default_month = (
            previous_calendar_month - timezone.timedelta(days=1)
        ).replace(day=1)

    # --------------------------------------------------
    # SELECT REPORT MONTH
    # --------------------------------------------------

    try:
        year = int(request.GET.get("year", default_month.year))
        month = int(request.GET.get("month", default_month.month))
        selected_month = date(year, month, 1)
    except (ValueError, TypeError):
        selected_month = default_month

    year = selected_month.year
    month = selected_month.month

    # --------------------------------------------------
    # CALENDAR MONTH BOUNDARIES
    # --------------------------------------------------

    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)

    start_of_month = timezone.make_aware(
        datetime.combine(selected_month, time.min)
    )

    start_of_next_month = timezone.make_aware(
        datetime.combine(next_month_start, time.min)
    )

    # --------------------------------------------------
    # ACCOUNTING PERIOD: 6TH TO 5TH
    # --------------------------------------------------

    start_date = date(year, month, 6)
    end_date_exclusive = next_month_start.replace(day=6)

    start_datetime = timezone.make_aware(
        datetime.combine(start_date, time.min)
    )

    end_datetime = timezone.make_aware(
        datetime.combine(end_date_exclusive, time.min)
    )

    # --------------------------------------------------
    # EXPECTED CONTRIBUTIONS
    # One share = Frw 10,000
    # --------------------------------------------------

    total_active_shares = (
        Member.objects.filter(
            status="ACTIVE"
        ).aggregate(total=Sum("shares"))["total"]
        or 0
    )

    expected_contributions = (
        Decimal(total_active_shares) * Decimal("10000")
    )

    # --------------------------------------------------
    # APPROVED CONTRIBUTIONS FOR SELECTED MONTH
    # --------------------------------------------------

    approved_contributions = MonthlyContribution.objects.filter(
        status="APPROVED",
        month__year=year,
        month__month=month,
    )

    total_contributions = (
        approved_contributions.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    contribution_count = approved_contributions.count()

    # --------------------------------------------------
    # LOAN PORTFOLIO
    # Opening balance is carried forward from the
    # immediately preceding month's saved report.
    # --------------------------------------------------

    if month == 1:
        previous_loan_year = year - 1
        previous_loan_month = 12
    else:
        previous_loan_year = year
        previous_loan_month = month - 1

    previous_loan_report = MonthlyReportBalance.objects.filter(
        year=previous_loan_year,
        month=previous_loan_month,
    ).first()

    if previous_loan_report:
        opening_loan_balance = (
            previous_loan_report.current_outstanding_loan_balance
        )
    else:
        opening_loan_balance = Decimal("0.00")

    # New loans disbursed during the selected calendar month.
    newly_disbursed_loans = Loan.objects.filter(
        status__in=["DISBURSED", "COMPLETED"],
        disbursed_at__gte=start_of_month,
        disbursed_at__lt=start_of_next_month,
    )

    # Includes principal plus the loan's calculated interest.
    new_loans_disbursed = sum(
        (loan.total_payable for loan in newly_disbursed_loans),
        Decimal("0.00"),
    )

    # Approved repayments during the selected calendar month.
    loan_portfolio_repayments = LoanRepayment.objects.filter(
        status="APPROVED",
        approved_at__gte=start_of_month,
        approved_at__lt=start_of_next_month,
    )

    # TEMPORARY ESTIMATE:
    # Repayment records do not separately identify principal
    # and interest, so this currently uses the full repayment.
    loan_principal_repaid = (
        loan_portfolio_repayments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    current_outstanding_loan_balance = max(
        opening_loan_balance
        + new_loans_disbursed
        - loan_principal_repaid,
        Decimal("0.00"),
    )

    # --------------------------------------------------
    # APPROVED LOAN REPAYMENTS IN THE ACCOUNTING PERIOD
    # --------------------------------------------------

    approved_repayments = LoanRepayment.objects.filter(
        status="APPROVED",
        payment_date__gte=start_datetime,
        payment_date__lt=end_datetime,
    )

    total_repayments = (
        approved_repayments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    repayment_count = approved_repayments.count()

    # --------------------------------------------------
    # APPROVED PENALTY PAYMENTS IN THE ACCOUNTING PERIOD
    # --------------------------------------------------

    approved_penalty_payments = PenaltyPayment.objects.filter(
        status="APPROVED",
        payment_date__gte=start_datetime,
        payment_date__lt=end_datetime,
    )

    total_penalty_payments = (
        approved_penalty_payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    penalty_payment_count = approved_penalty_payments.count()

    # --------------------------------------------------
    # LOANS DISBURSED IN THE ACCOUNTING PERIOD
    # This is the principal cash outflow, not total payable.
    # --------------------------------------------------

    disbursed_loans = Loan.objects.filter(
        status__in=["DISBURSED", "COMPLETED"],
        disbursed_at__gte=start_datetime,
        disbursed_at__lt=end_datetime,
    )

    total_loans_disbursed = sum(
        (
            loan.principal_amount
            for loan in disbursed_loans
        ),
        Decimal("0.00"),
    )

    disbursed_loan_count = disbursed_loans.count()

    # --------------------------------------------------
    # CURRENT OUTSTANDING LOANS
    # Current live balance of active loans.
    # --------------------------------------------------

    active_loans = Loan.objects.filter(
        status__in=["APPROVED", "DISBURSED"]
    )

    outstanding_loans = sum(
        (loan.remaining_balance for loan in active_loans),
        Decimal("0.00"),
    )

    active_loan_count = active_loans.count()

    # --------------------------------------------------
    # CURRENT CUMULATIVE SAVINGS LEDGER
    # --------------------------------------------------

    total_savings = (
        SavingsTransaction.objects.filter(
            transaction_type="CONTRIBUTION"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    
    # --------------------------------------------------
    # PENALTIES REPORT
    # Accounting period: 6th to 5th of the next month
    # --------------------------------------------------

    # 1. Penalties assessed during the selected period
    penalties_assessed = Penalty.objects.filter(
        issued_at__gte=start_datetime,
        issued_at__lt=end_datetime,
    ).exclude(
        status__in=["REJECTED", "WAIVED"]
    )

    penalties_assessed_amount = (
        penalties_assessed.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # 2. Old unpaid penalties assessed before this period
    old_unpaid_penalties = (
        Penalty.objects.filter(
            issued_at__lt=start_datetime,
            status__in=["PENDING", "APPROVED"],
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # 3. Total penalties due
    total_penalties_due = (
        old_unpaid_penalties
        + penalties_assessed_amount
    )

    # 4. Penalties collected during the selected period
    penalty_payments_in_period = PenaltyPayment.objects.filter(
        status="APPROVED",
        payment_date__gte=start_datetime,
        payment_date__lt=end_datetime,
    )

    penalties_collected = (
        penalty_payments_in_period.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # 5. Outstanding penalties
    outstanding_penalties = max(
        total_penalties_due - penalties_collected,
        Decimal("0.00"),
    )


    # --------------------------------------------------
    # MEMBERS
    # --------------------------------------------------

    total_members = Member.objects.count()

    active_members = Member.objects.filter(
        status="ACTIVE"
    ).count()

    # --------------------------------------------------
    # MEMBERS WHO HAVE NOT FULLY PAID THIS MONTH
    # --------------------------------------------------

    active_members_qs = Member.objects.filter(
        status="ACTIVE"
    )

    members_who_have_not_paid = 0

    for member in active_members_qs:
        expected_amount = (
            Decimal(member.shares) * Decimal("10000")
        )

        approved_amount = (
            MonthlyContribution.objects.filter(
                member=member,
                month__year=year,
                month__month=month,
                status="APPROVED",
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        if approved_amount < expected_amount:
            members_who_have_not_paid += 1

    # --------------------------------------------------
    # OUTSTANDING CONTRIBUTIONS FROM OLDER MONTHS
    # --------------------------------------------------

    first_contribution_month = (
        MonthlyContribution.objects
        .order_by("month")
        .values_list("month", flat=True)
        .first()
    )

    outstanding_old_contributions = Decimal("0.00")

    if first_contribution_month:
        current_contribution_month = (
            first_contribution_month.replace(day=1)
        )

        expected_monthly_contributions = (
            Decimal(total_active_shares) * Decimal("10000")
        )

        while current_contribution_month < selected_month:

            paid_amount = (
                MonthlyContribution.objects.filter(
                    status="APPROVED",
                    month__year=current_contribution_month.year,
                    month__month=current_contribution_month.month,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            monthly_outstanding = (
                expected_monthly_contributions - paid_amount
            )

            if monthly_outstanding > 0:
                outstanding_old_contributions += monthly_outstanding

            if current_contribution_month.month == 12:
                current_contribution_month = date(
                    current_contribution_month.year + 1,
                    1,
                    1,
                )
            else:
                current_contribution_month = date(
                    current_contribution_month.year,
                    current_contribution_month.month + 1,
                    1,
                )

    total_contributions_due = (
        outstanding_old_contributions
        + expected_contributions
    )

    outstanding_contributions = max(
        total_contributions_due - total_contributions,
        Decimal("0.00"),
    )

    # --------------------------------------------------
    # INITIAL BALANCE
    # Carry forward the previous month's closing balance.
    # --------------------------------------------------

    previous_report = MonthlyReportBalance.objects.filter(
        year=previous_loan_year,
        month=previous_loan_month,
    ).first()

    if previous_report:
        initial_balance = previous_report.closing_balance
    else:
        initial_balance = Decimal("0.00")

    # --------------------------------------------------
    # OLD PENALTIES COLLECTED DURING THE PERIOD
    # --------------------------------------------------

    old_penalties_collected = (
        Penalty.objects.filter(
            status="PAID",
            paid_at__gte=start_datetime,
            paid_at__lt=end_datetime,
            issued_at__lt=start_datetime,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # --------------------------------------------------
    # CLOSING BALANCE
    # --------------------------------------------------

    closing_balance = (
        initial_balance
        + total_contributions
        + total_repayments
        + penalties_collected
        - total_loans_disbursed
    )

    # --------------------------------------------------
    # SAVE MONTHLY REPORT BALANCES
    # Also save current outstanding loan balance so the
    # next month's report can use it as its opening balance.
    # --------------------------------------------------

    MonthlyReportBalance.objects.update_or_create(
        year=year,
        month=month,
        defaults={
            "initial_balance": initial_balance,
            "closing_balance": closing_balance,
            "current_outstanding_loan_balance": (
                current_outstanding_loan_balance
            ),
        },
    )

    # --------------------------------------------------
    # MONTHLY CASH FLOW
    # --------------------------------------------------

    total_monthly_inflows = (
        initial_balance
        + total_contributions
        + total_repayments
        + total_penalty_payments
    )

    monthly_net_cash_flow = (
        total_monthly_inflows - total_loans_disbursed
    )


    net_financial_position = (
        closing_balance
        + outstanding_loans
        + outstanding_contributions
        + outstanding_penalties
    )
    # --------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------

    context = {
        "selected_month": selected_month,
        "selected_year": year,
        "selected_month_number": month,

        "initial_balance": initial_balance,
        "closing_balance": closing_balance,
        "total_penalties_incurred": penalties_assessed_amount,

        "total_contributions": total_contributions,
        "contribution_count": contribution_count,
        "outstanding_old_contributions": (
            outstanding_old_contributions
        ),
        "expected_contributions": expected_contributions,
        "total_contributions_due": total_contributions_due,
        "outstanding_contributions": outstanding_contributions,

        "total_repayments": total_repayments,
        "repayment_count": repayment_count,

        "total_penalty_payments": total_penalty_payments,
        "penalty_payment_count": penalty_payment_count,
        "old_penalties_collected": old_penalties_collected,

        "total_loans_disbursed": total_loans_disbursed,
        "disbursed_loan_count": disbursed_loan_count,

        "outstanding_loans": outstanding_loans,
        "active_loan_count": active_loan_count,

        "opening_loan_balance": opening_loan_balance,
        "new_loans_disbursed": new_loans_disbursed,
        "loan_principal_repaid": loan_principal_repaid,
        "current_outstanding_loan_balance": (
            current_outstanding_loan_balance
        ),

        "total_savings": total_savings,
        "unpaid_penalties": outstanding_penalties,

        "total_monthly_inflows": total_monthly_inflows,
        "monthly_net_cash_flow": monthly_net_cash_flow,

        "total_members": total_members,
        "active_members": active_members,
        "members_who_have_not_paid": members_who_have_not_paid,
        
        "old_unpaid_penalties": old_unpaid_penalties,
        "penalties_assessed_amount": penalties_assessed_amount,
        "total_penalties_due": total_penalties_due,
        "penalties_collected": penalties_collected,
        "outstanding_penalties": outstanding_penalties,
        "net_financial_position": net_financial_position,
    }

    
    
    
    if request.GET.get("format") == "pdf":
        template = get_template(
            "accounts/monthly_report_pdf.html"
        )
        html = template.render(context, request)

        filename = (
            f"Smart_Saving_Group_Report_{year}_{month:02d}.pdf"
        )
        response = HttpResponse(
            content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )

        pdf_status = pisa.CreatePDF(
            src=html,
            dest=response,
            link_callback=link_callback,
            encoding="UTF-8",
        )

        if pdf_status.err:
            return HttpResponse(
                "PDF generation failed. Please check the server error log.",
                status=500,
                content_type="text/plain",
            )

        return response

    # --------------------------------------------------
    # DISPLAY NORMAL HTML REPORT
    # --------------------------------------------------

    return render(
        request,
        "accounts/monthly_report.html",
        context,
    )


def link_callback(uri, rel):
    uri = unquote(uri)

    if uri.startswith(settings.STATIC_URL):
        relative_path = uri.replace(
            settings.STATIC_URL, "", 1
        )
        path = finders.find(relative_path)

        if path:
            return os.path.abspath(path)

    if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        relative_path = uri.replace(
            settings.MEDIA_URL, "", 1
        )
        path = os.path.join(
            settings.MEDIA_ROOT,
            relative_path,
        )

        if os.path.isfile(path):
            return os.path.abspath(path)

    return uri

        