from django.urls import path

from . import views


urlpatterns = [
    path(
        "loan/<int:loan_id>/pay/",
        views.repayment_create,
        name="repayment_create",
    ),

    path(
        "",
        views.repayment_list,
        name="repayment_list",
    ),

    path(
        "pending/",
        views.repayment_pending,
        name="repayment_pending",
    ),

    path(
        "<int:pk>/approve/",
        views.repayment_approve,
        name="repayment_approve",
    ),

    path(
        "<int:pk>/reject/",
        views.repayment_reject,
        name="repayment_reject",
    ),
    
    path(
        "<int:pk>/edit/",
        views.repayment_edit,
        name="repayment_edit",
    ),

    path(
        "<int:pk>/delete/",
        views.repayment_delete,
        name="repayment_delete",
    ),
]