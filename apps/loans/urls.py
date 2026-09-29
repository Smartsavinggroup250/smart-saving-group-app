from django.urls import path

from . import views


urlpatterns = [

    path(
        "apply/",
        views.loan_apply,
        name="loan_apply",
    ),

    path(
        "",
        views.loan_list,
        name="loan_list",
    ),

    path(
        "pending/",
        views.loan_pending,
        name="loan_pending",
    ),

    path(
        "<int:pk>/approve/",
        views.loan_approve,
        name="loan_approve",
    ),

    path(
        "<int:pk>/reject/",
        views.loan_reject,
        name="loan_reject",
    ),

    path(
        "<int:pk>/disburse/",
        views.loan_disburse,
        name="loan_disburse",
    ),
    
    path(
        "active/",
        views.active_loan_members,
        name="active_loan_members",
    ),
]