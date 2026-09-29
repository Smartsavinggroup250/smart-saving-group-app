from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.notification_list,
        name="notification_list",
    ),
    path(
        "<int:pk>/read/",
        views.notification_mark_read,
        name="notification_mark_read",
    ),
    path(
        "mark-all-read/",
        views.notification_mark_all_read,
        name="notification_mark_all_read",
    ),
    
    path(
        "<int:pk>/delete/",
        views.notification_delete,
        name="notification_delete",
    ),

    path(
        "delete-all/",
        views.notification_delete_all,
        name="notification_delete_all",
    ),
]