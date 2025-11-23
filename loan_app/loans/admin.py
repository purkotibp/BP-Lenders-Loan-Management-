from django.contrib import admin
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
from .models import CustomerProfile, LoanType, LoanApplication, Loan

def generate_random_password():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(8))

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'surname', 'email', 'phone_number', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'gender']
    search_fields = ['first_name', 'surname', 'email', 'phone_number']
    readonly_fields = ['created_at', 'approved_at']
    actions = ['approve_customers', 'reject_customers']
    
    def approve_customers(self, request, queryset):
        for customer in queryset:
            if customer.status != 'approved':
                username = f"{customer.first_name.lower()}{customer.id}"
                password = generate_random_password()
                
                from django.contrib.auth.models import User
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=customer.email,
                    first_name=customer.first_name,
                    last_name=customer.surname
                )
                
                customer.user = user
                customer.status = 'approved'
                customer.approved_by = request.user
                customer.approved_at = timezone.now()
                customer.save()
                
                try:
                    send_mail(
                        'Your Loan Account Has Been Approved',
                        f'''Dear {customer.first_name} {customer.surname},

Your account has been approved by the admin.

Your login credentials:
Username: {username}
Password: {password}

Please login at: http://localhost:8000/customer/login/

Best regards,
Loan Management System Team''',
                        settings.DEFAULT_FROM_EMAIL,
                        [customer.email],
                        fail_silently=False,
                    )
                    self.message_user(
                        request, 
                        f'Successfully approved {customer.first_name} {customer.surname}. Login credentials sent to {customer.email}', 
                        messages.SUCCESS
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f'Approved {customer.first_name} {customer.surname} but failed to send email: {str(e)}',
                        messages.WARNING
                    )
    
    approve_customers.short_description = "Approve selected customers and send login credentials"
    
    def reject_customers(self, request, queryset):
        updated = queryset.update(status='rejected', approved_by=request.user)
        self.message_user(request, f'Successfully rejected {updated} customers', messages.SUCCESS)
    
    reject_customers.short_description = "Reject selected customers"

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['customer', 'loan_type', 'requested_amount', 'status', 'application_date', 'approval_score']
    list_filter = ['status', 'loan_type', 'application_date']
    search_fields = ['customer__first_name', 'customer__surname', 'customer__email']
    readonly_fields = ['application_date', 'approval_score_display']
    actions = ['approve_applications', 'reject_applications']
    
    def approval_score(self, obj):
        return f"{obj.calculate_approval_score():.2f}"
    approval_score.short_description = "Score"
    
    def approval_score_display(self, obj):
        return f"{obj.calculate_approval_score():.2f}/100"
    approval_score_display.short_description = "Approval Score"
    
    def approve_applications(self, request, queryset):
        approved_count = 0
        for application in queryset:
            if application.status == 'pending':
                approval_score = application.calculate_approval_score()
                if application.should_approve():
                    application.status = 'approved'
                    application.approved_amount = application.requested_amount
                    application.reviewed_by = request.user
                    application.reviewed_date = timezone.now()
                    application.save()
                    approved_count += 1
                    
                    Loan.objects.create(
                        application=application,
                        principal_amount=application.approved_amount,
                        outstanding_balance=application.approved_amount,
                        interest_rate=application.loan_type.interest_rate,
                        start_date=timezone.now().date(),
                        end_date=timezone.now().date() + timezone.timedelta(days=application.loan_type.duration_months * 30)
                    )
                else:
                    self.message_user(
                        request,
                        f'Application #{application.id} cannot be approved. Score: {approval_score:.2f} (below threshold)',
                        messages.WARNING
                    )
        
        self.message_user(request, f'Successfully approved {approved_count} loan applications', messages.SUCCESS)
    
    approve_applications.short_description = "Approve selected loan applications using linear algorithm"
    
    def reject_applications(self, request, queryset):
        updated = queryset.update(status='rejected', reviewed_by=request.user, reviewed_date=timezone.now())
        self.message_user(request, f'Successfully rejected {updated} loan applications', messages.SUCCESS)
    
    reject_applications.short_description = "Reject selected loan applications"

@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_amount', 'interest_rate', 'duration_months']
    list_filter = ['interest_rate']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['id', 'application', 'principal_amount', 'outstanding_balance', 'start_date']
    list_filter = ['start_date']
    search_fields = ['application__customer__first_name', 'application__customer__surname']