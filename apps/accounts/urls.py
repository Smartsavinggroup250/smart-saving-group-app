from django.urls import path
from . import views

urlpatterns = [
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),
    
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
    
    path(
        "monthly-report/",
        views.monthly_report,
        name="monthly_report",
    ),
]