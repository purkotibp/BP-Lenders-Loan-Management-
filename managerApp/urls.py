from django.urls import path
from django.views.generic import RedirectView
from managerApp import views

app_name = 'managerApp'

urlpatterns = [
    # Redirect old custom admin login → Django admin login
    path('admin-login/', RedirectView.as_view(url='/admin/login/', permanent=True), name='admin-login'),
    # Redirect old dashboard → Django admin index
    path('dashboard/', RedirectView.as_view(url='/admin/', permanent=True), name='dashboard'),

    # These loan-action endpoints are still used for backward-compat
    # (e.g. any bookmarked direct links) — but the primary flow is Django admin actions.
    path('approved-request/<int:id>/', views.approved_request, name='approved_request'),
    path('rejected-request/<int:id>/', views.rejected_request, name='rejected_request'),
]
