from django.urls import path
from . import views

app_name = 'loanApp'

urlpatterns = [
    path('', views.home, name='home'),
    path('loan-request/', views.loan_request_view, name='loan_request'),
    path('loan-payment/', views.LoanPayment, name='loan_payment'),
    path('user-transaction/', views.UserTransaction, name='user_transaction'),
    path('user-loan-history/', views.UserLoanHistory, name='user_loan_history'),
    path('user-dashboard/', views.UserDashboard, name='user_dashboard'),
    path('emi-schedule/<int:loan_id>/', views.EMISchedule, name='emi_schedule'),
]