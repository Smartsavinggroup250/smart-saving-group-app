from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification


def _send_notification_email(
    recipient,
    title,
    message,
):
    """
    Send notification email after the current database
    transaction has successfully committed.
    """

    if not recipient.email:
        return

    transaction.on_commit(
        lambda: send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    )


def create_notification(
    recipient,
    title,
    message,
    notification_type="SYSTEM",
    send_email=True,
):
    """
    Create an in-app notification and optionally send
    an email notification to the same user.
    """

    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
    )

    if send_email:
        _send_notification_email(
            recipient=recipient,
            title=title,
            message=message,
        )

    return notification


def notify_member(
    member,
    title,
    message,
    notification_type="SYSTEM",
    send_email=True,
):
    """
    Notify a specific member and send the notification
    to the member's email address.
    """

    return create_notification(
        recipient=member.user,
        title=title,
        message=message,
        notification_type=notification_type,
        send_email=send_email,
    )


def notify_admins_and_treasurers(
    title,
    message,
    notification_type="SYSTEM",
    send_email=True,
):
    """
    Notify all active Admins and Treasurers.
    Each recipient receives:
      1. An in-app notification
      2. An email notification
    """

    User = get_user_model()

    users = (
        User.objects
        .filter(
            is_active=True,
            profile__role__in=["ADMIN", "TREASURER"],
        )
        .distinct()
    )

    notifications = []

    for user in users:
        notification = create_notification(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            send_email=send_email,
        )

        notifications.append(notification)

    return notifications