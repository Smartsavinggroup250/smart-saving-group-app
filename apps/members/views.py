from django.contrib.auth import login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied

from django.db import transaction

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.contrib import messages

from .models import Member
from .forms import (
    MemberRegistrationForm,
    MemberProfileForm,
)


# ============================================================
# PERMISSION HELPERS
# ============================================================

def is_admin_or_treasurer(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return profile and profile.role in [
        "ADMIN",
        "TREASURER",
    ]


def is_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return profile and profile.role == "ADMIN"


# ============================================================
# MEMBER NUMBER
# ============================================================

def generate_member_number():
    last_member = Member.objects.order_by(
        "-id"
    ).first()

    next_id = (
        last_member.id + 1
        if last_member
        else 1
    )

    return f"SSG-{next_id:05d}"


# ============================================================
# MEMBER LIST
# ============================================================

@login_required
def member_list(request):

    if not is_admin_or_treasurer(request.user):
        raise PermissionDenied

    members = Member.objects.select_related(
        "user"
    ).order_by("-joined_date")

    # Search
    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:
        members = members.filter(
            user__first_name__icontains=search
        ) | members.filter(
            user__last_name__icontains=search
        ) | members.filter(
            member_number__icontains=search
        ) | members.filter(
            phone__icontains=search
        )

    # ========================================================
    # PAGINATION
    # 10 MEMBERS PER PAGE
    # ========================================================

    paginator = Paginator(
        members,
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
        "members/member_list.html",
        {
            "members": page_obj,
            "page_obj": page_obj,
            "search": search,
        },
    )


# ============================================================
# MEMBER REGISTRATION
# ============================================================

def member_register(request):

    if request.method == "POST":

        form = MemberRegistrationForm(
            request.POST
        )

        if form.is_valid():

            with transaction.atomic():

                user = User.objects.create_user(
                    username=form.cleaned_data[
                        "username"
                    ],
                    password=form.cleaned_data[
                        "password"
                    ],
                    email=form.cleaned_data[
                        "email"
                    ],
                    first_name=form.cleaned_data[
                        "first_name"
                    ],
                    last_name=form.cleaned_data[
                        "last_name"
                    ],
                )

                member = Member.objects.create(
                    user=user,
                    member_number=generate_member_number(),
                    phone=form.cleaned_data[
                        "phone"
                    ],
                    national_id=form.cleaned_data[
                        "national_id"
                    ] or None,
                    address=form.cleaned_data[
                        "address"
                    ],
                )

                # UserProfile is created
                # by the accounts post_save signal.
                #
                # Set the new user's role to MEMBER.

                user.profile.role = "MEMBER"
                user.profile.save()

            login(
                request,
                user
            )

            messages.success(
                request,
                "Registration completed successfully."
            )

            return redirect(
                "member_detail"
            )

    else:

        form = MemberRegistrationForm()

    return render(
        request,
        "members/member_form.html",
        {
            "form": form
        }
    )


# ============================================================
# MEMBER PROFILE
# ============================================================

@login_required
def member_detail(request):

    member = get_object_or_404(
        Member.objects.select_related(
            "user"
        ),
        user=request.user
    )

    role = getattr(
        getattr(
            request.user,
            "profile",
            None
        ),
        "role",
        "MEMBER"
    )

    return render(
        request,
        "members/member_detail.html",
        {
            "member": member,
            "role": role,
        }
    )


# ============================================================
# EDIT PROFILE
# ============================================================

@login_required
def edit_profile(request):

    member = get_object_or_404(
        Member.objects.select_related(
            "user"
        ),
        user=request.user
    )

    if request.method == "POST":

        form = MemberProfileForm(
            request.POST,
            instance=member
        )

        if form.is_valid():

            member = form.save()

            request.user.first_name = (
                form.cleaned_data[
                    "first_name"
                ]
            )

            request.user.last_name = (
                form.cleaned_data[
                    "last_name"
                ]
            )

            request.user.email = (
                form.cleaned_data[
                    "email"
                ]
            )

            request.user.save()

            messages.success(
                request,
                "Your profile has been updated successfully."
            )

            return redirect(
                "member_detail"
            )

    else:

        form = MemberProfileForm(
            instance=member
        )

    return render(
        request,
        "members/edit_profile.html",
        {
            "form": form,
            "member": member,
        }
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            user = form.save()

            # Keep user logged in after
            # changing password.

            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                "Your password has been changed successfully."
            )

            return redirect(
                "member_detail"
            )

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "members/change_password.html",
        {
            "form": form
        }
    )