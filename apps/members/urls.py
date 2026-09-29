from django.urls import path
from . import views

urlpatterns = [

    path(
        "register/",
        views.member_register,
        name="member_register"
    ),

    path(
        "profile/",
        views.member_detail,
        name="member_detail"
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile"
    ),

    path(
        "profile/change-password/",
        views.change_password,
        name="change_password"
    ),

    path(
        "list/",
        views.member_list,
        name="member_list"
    ),
]