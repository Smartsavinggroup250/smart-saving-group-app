from django.urls import path

from . import views


urlpatterns = [
    path(
        "contributions/new/",
        views.contribution_create,
        name="contribution_create",
    ),

    path(
        "contributions/",
        views.contribution_list,
        name="contribution_list",
    ),

    path(
        "contributions/pending/",
        views.contribution_pending,
        name="contribution_pending",
    ),

    path(
        "contributions/<int:pk>/approve/",
        views.contribution_approve,
        name="contribution_approve",
    ),

    path(
        "contributions/<int:pk>/reject/",
        views.contribution_reject,
        name="contribution_reject",
    ),

    path(
        "balance/",
        views.savings_balance,
        name="savings_balance",
    ),
    
    path(
        "contributions/paid/",
        views.paid_contribution_list,
        name="paid_contribution_list",
    ),
    
    path(
        "contributions/<int:pk>/edit/",
        views.contribution_edit,
        name="contribution_edit",
    ),

    path(
        "contributions/<int:pk>/delete/",
        views.contribution_delete,
        name="contribution_delete",
    ),
]