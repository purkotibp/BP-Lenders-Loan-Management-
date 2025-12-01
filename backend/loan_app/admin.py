from django.contrib import admin
from .models import CustomerProfile, LoanType, LoanApplication

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'surname', 'email', 'status', 'created_at']
    list_filter = ['status', 'created_at']

@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_amount', 'interest_rate']

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['customer', 'loan_type', 'requested_amount', 'status', 'application_date']
