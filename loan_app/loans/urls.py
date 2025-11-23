from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('customer/signup/', views.customer_signup, name='customer_signup'),
    path('customer/login/', views.customer_login, name='customer_login'),
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/apply-loan/', views.apply_loan, name='apply_loan'),
    path('logout/', views.logout_view, name='logout'),
]