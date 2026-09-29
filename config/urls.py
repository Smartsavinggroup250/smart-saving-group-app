from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 1. Django Admin Panel
    path("admin/", admin.site.urls),

    # 2. Django Built-in Authentication (Ibyo kwinjira, gusohoka, n'ibindi)
    path("accounts/", include("django.contrib.auth.urls")),

    # 3. Urubuga rwawe rw'ibanze cyangwa porogaramu yawe (Home/Custom Accounts)
    path("", include("apps.accounts.urls")),
]

# members
from django.contrib import admin
from django.urls import path, include

urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "accounts/",
        include("django.contrib.auth.urls")
    ),

    path(
        "",
        include("apps.accounts.urls")
    ),

    path(
        "members/",
        include("apps.members.urls")
    ),

    path(
        "savings/",
         include("apps.savings.urls")
    ),
    
    path(
        "loans/",
        include("apps.loans.urls")
    ),

    path(
        "repayments/",
        include("apps.repayments.urls"),
    ),
    
    path(
        "penalties/",
        include("apps.penalties.urls")
    ),
    
    path(
        "notifications/",
        include("apps.notifications.urls"),
    ),

]