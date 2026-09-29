from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    )

    unread_count = notifications.filter(
        is_read=False
    ).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }

    return render(
        request,
        "notifications/notification_list.html",
        context,
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = Notification.objects.filter(
        pk=pk,
        recipient=request.user,
    ).first()

    if notification:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return redirect("notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    return redirect("notification_list")

@login_required
@require_POST
def notification_delete(request, pk):
    notification = Notification.objects.filter(
        pk=pk,
        recipient=request.user,
    ).first()

    if notification:
        notification.delete()

    return redirect("notification_list")

@login_required
@require_POST
def notification_delete_all(request):
    Notification.objects.filter(
        recipient=request.user,
    ).delete()

    return redirect("notification_list")