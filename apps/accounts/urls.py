from django.urls import path
from . import views

urlpatterns = [
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),
    #path(
    #    "profile/",
    #    views.profile, 
    #    name="profile"
    #),
    path(
        "reports/",
        views.reports,
        name="reports"
    ),
    
    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),
]