from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.penalty_list,
        name="penalty_list"
    ),

    path(
        "<int:penalty_id>/pay/",
        views.penalty_pay,
        name="penalty_pay"
    ),

    path(
        "payments/pending/",
        views.penalty_payment_pending,
        name="penalty_payment_pending"
    ),

    path(
        "payments/<int:payment_id>/approve/",
        views.penalty_payment_approve,
        name="penalty_payment_approve"
    ),

    path(
        "payments/<int:payment_id>/reject/",
        views.penalty_payment_reject,
        name="penalty_payment_reject"
    ),
    
    path(
        "members-with-penalties/",
        views.members_with_penalties,
        name="members_with_penalties",
    ),
]