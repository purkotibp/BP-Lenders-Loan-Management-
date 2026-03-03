from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from datetime import date
from .models import loanRequest, loanCategory, CustomerLoan, loanTransaction, EMIPayment


# ─────────────────────────────────────────────
# Custom Admin Site Header / Title
# ─────────────────────────────────────────────
admin.site.site_header = "Loan Management System — Admin"
admin.site.site_title = "LMS Admin"
admin.site.index_title = "Welcome to the LMS Administration Panel"


# ─────────────────────────────────────────────
# Inline: EMI payments inside a LoanRequest
# ─────────────────────────────────────────────
class EMIPaymentInline(admin.TabularInline):
    model = EMIPayment
    extra = 0
    readonly_fields = (
        'installment_no', 'due_date', 'emi_amount',
        'principal_component', 'interest_component', 'balance',
    )
    fields = (
        'installment_no', 'due_date', 'emi_amount',
        'principal_component', 'interest_component', 'balance',
        'is_paid', 'paid_date',
    )
    can_delete = False
    show_change_link = False
    verbose_name = "EMI Instalment"
    verbose_name_plural = "EMI Amortization Schedule"

    def has_add_permission(self, request, obj=None):
        return False


# ─────────────────────────────────────────────
# Loan Category
# ─────────────────────────────────────────────
from django.contrib import admin, messages
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from datetime import date
from django.db.models import F

# Check your models.py for the exact spelling of these names
from .models import loanCategory, loanTransaction, CustomerLoan
# If your model is actually named 'loanRequest' with a small 'l', use that here:
try:
    from .models import LoanRequest
except ImportError:
    from .models import loanRequest as LoanRequest

# ─────────────────────────────────────────────
# Loan Category with Password Intercept
# ─────────────────────────────────────────────
@admin.register(loanCategory)
class LoanCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan_name', 'creation_date', 'updated_date')
    search_fields = ('loan_name',)
    ordering = ('loan_name',)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:  # Only for ADDING new categories
            request.session['pending_category_name'] = obj.loan_name
            return 
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('admin:secure_confirm_category')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('confirm-add/', self.admin_site.admin_view(self.secure_confirm_view), name='secure_confirm_category'),
        ]
        return custom_urls + urls

    def secure_confirm_view(self, request):
        if request.method == 'POST':
            password = request.POST.get('password')
            if check_password(password, request.user.password):
                loan_name = request.session.get('pending_category_name')
                if loan_name:
                    loanCategory.objects.create(loan_name=loan_name)
                    del request.session['pending_category_name']
                    messages.success(request, "New category added securely.")
                    return redirect('admin:loanApp_loancategory_changelist')
            else:
                messages.error(request, "Incorrect password. Category not created.")
                return redirect('admin:loanApp_loancategory_changelist')

        context = self.admin_site.each_context(request)
        return render(request, 'loanApp/confirm_password.html', context)        
# ─────────────────────────────────────────────
# Loan Approval Helper
# ─────────────────────────────────────────────
def _process_loan_approval(loan_obj):
    today = date.today()
    loan_obj.status_date = today.strftime("%B %d, %Y")
    loan_obj.status = 'approved'
    loan_obj.save()

    # Automatic OUT transaction
    loanTransaction.objects.create(
        customer=loan_obj.customer,
        payment=loan_obj.amount,
        category='out'
    )

    year = loan_obj.year
    approved_customer = loan_obj.customer
    interest_rate = 0.12 #

    if CustomerLoan.objects.filter(customer=approved_customer).exists():
        existing = CustomerLoan.objects.get(customer=approved_customer)
        existing.total_loan = F('total_loan') + int(loan_obj.amount)
        existing.payable_loan = (
            F('payable_loan') 
            + int(loan_obj.amount) 
            + (int(loan_obj.amount) * interest_rate * int(year))
        )
        existing.save()
    else:
        CustomerLoan.objects.create(
            customer=approved_customer,
            total_loan=int(loan_obj.amount),
            payable_loan=int(loan_obj.amount) + (int(loan_obj.amount) * interest_rate * int(year)),
        )

    loan_obj.refresh_from_db()
    loan_obj.generate_emi_schedule(loan_obj)

# ─────────────────────────────────────────────
# Loan Request
# ─────────────────────────────────────────────
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect

@admin.register(loanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    # --- UI CONFIGURATION ---
    actions = None  
    actions_selection_counter = False  
    search_fields = (
        'customer__user__username', 
        'customer__first_name', 
        'customer__last_name'
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # --- HELPER METHODS ---
    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Custom "

    def amount_display(self, obj):
        return f"{obj.amount:,} Tk"
    amount_display.short_description = "Amount"

    def status_badge(self, obj):
        colours = {'pending': ('#856404', '#fff3cd'), 'approved': ('#155724', '#d4edda'), 'rejected': ('#721c24', '#f8d7da')}
        fg, bg = colours.get(obj.status, ('#333', '#eee'))
        return format_html('<span style="padding:2px 8px;border-radius:10px;color:{};background:{};">{}</span>', fg, bg, obj.status.title())
    status_badge.short_description = "Status"

    def emi_schedule_link(self, obj):
        count = obj.emi_payments.count()
        return format_html('<a href="{}?loan__id__exact={}">{} instalments</a>', reverse('admin:loanApp_emipayment_changelist'), obj.pk, count) if count else "—"
    emi_schedule_link.short_description = "EMI Schedule"

    def view_documents(self, obj):
        if hasattr(obj, 'document') and obj.document:
            return format_html('<a class="btn btn-info btn-sm" href="{}" target="_blank">View Doc</a>', obj.document.url)
        return "No Doc"

    def loan_actions(self, obj):
        # REPLACED: Removed the 'approved' block and 'Regenerate' button
        if obj.status == 'pending':
            return format_html(
                '<a class="btn btn-success btn-sm" href="approve/{}/" style="color:white;background:#28a745;padding:2px 5px;margin-right:4px;">Approve</a>'
                '<a class="btn btn-danger btn-sm" href="reject/{}/" style="color:white;background:#dc3545;padding:2px 5px;">Reject</a>',
                obj.pk, obj.pk
            )
        return format_html('<span style="color:gray;">Processed</span>')

    # --- LIST DISPLAY ---
    list_display = (
        'id', 'customer_name', 'category', 'amount_display',
        'year', 'status_badge', 'view_documents', 'loan_actions', 
        'request_date', 'emi_schedule_link',
    )

    # --- URL HANDLERS ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:loan_id>/', self.admin_site.admin_view(self.approve_loan), name='approve_loan'),
            path('reject/<int:loan_id>/', self.admin_site.admin_view(self.reject_loan), name='reject_loan'),
        ]
        return custom_urls + urls

    def approve_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        
        # Only process if not already approved to protect existing EMI data
        if loan.status != 'approved':
            loan.status = 'approved'
            # This triggers the logic in models.py
            loan.generate_emi_schedule() 
            loan.save()
            self.message_user(request, f"Loan {loan_id} Approved and EMI Schedule Generated")
        else:
            self.message_user(request, f"Loan {loan_id} is already approved.", level='info')
            
        return redirect('admin:loanApp_loanrequest_changelist')

    def reject_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        loan.status = 'rejected'
        loan.save()
        self.message_user(request, f"Loan {loan_id} Rejected", level='warning')
        return redirect('admin:loanApp_loanrequest_changelist')
    
    def save_model(self, request, obj, form, change):
        # 1. Save the LoanRequest first to ensure the database updates successfully
        super().save_model(request, obj, form, change)

        # 2. Check if the status was just changed to 'approved'
        if obj.status == 'approved' and 'status' in form.changed_data:
            from .models import loanTransaction # Local import to avoid circular dependencies
            
            # 3. Create the 'OUT' transaction automatically
            loanTransaction.objects.create(
                customer=obj.customer,
                payment=obj.loan_amount,
                category='out' # Records as Red/Expense in your ledger
            )
# ─────────────────────────────────────────────
# Customer Loan (balance ledger)
# ─────────────────────────────────────────────
@admin.register(CustomerLoan)
class CustomerLoanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer_name', 'total_loan_display',
        'payable_loan_display', 'outstanding_display',
    )
    search_fields = (
        'customer__user__username',
        'customer__user__email',
        'customer__first_name',
        'customer__last_name',
    )
    ordering = ('-total_loan',)
    readonly_fields = ('customer',)

    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"
    customer_name.admin_order_field = 'customer__user__username'

    def total_loan_display(self, obj):
        return f"{obj.total_loan:,} Tk"
    total_loan_display.short_description = "Total Loan"
    total_loan_display.admin_order_field = 'total_loan'

    def payable_loan_display(self, obj):
        return f"{obj.payable_loan:,} Tk"
    payable_loan_display.short_description = "Payable (with interest)"
    payable_loan_display.admin_order_field = 'payable_loan'

    def outstanding_display(self, obj):
        paid = loanTransaction.objects.filter(
            customer=obj.customer
        ).aggregate(total=Sum('payment'))['total'] or 0
        outstanding = obj.payable_loan - paid
        colour = '#dc3545' if outstanding > 0 else '#28a745'
        return format_html(
            '<span style="color:{};">{:,} Tk</span>', colour, outstanding
        )
    outstanding_display.short_description = "Outstanding"


# ─────────────────────────────────────────────
# Loan Transaction (payments made by customers)
# ─────────────────────────────────────────────
@admin.register(loanTransaction)
class LoanTransactionAdmin(admin.ModelAdmin):
    # Added 'type_badge' and updated payment display
    list_display = (
        'transaction', 'customer_name', 'type_badge', 'payment_display', 'payment_date',
    )
    list_filter = ('category', 'payment_date') # Added category filter
    search_fields = (
        'customer__user__username',
        'customer__user__email',
        'customer__first_name',
        'customer__last_name',
    )
    ordering = ('-payment_date',)
    readonly_fields = ('transaction', 'payment_date')

    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"

    # Automated Badge to show if it's Income or Expense
    def type_badge(self, obj):
        if obj.category == 'in':
            return format_html('<span style="color:#155724; background:#d4edda; padding:2px 10px; border-radius:12px; font-weight:600;">INCOME</span>')
        return format_html('<span style="color:#721c24; background:#f8d7da; padding:2px 10px; border-radius:12px; font-weight:600;">EXPENSE</span>')
    type_badge.short_description = "Type"

    # Color-coded amount: Green for In, Red for Out
    def payment_display(self, obj):
        color = "#28a745" if obj.category == 'in' else "#dc3545"
        symbol = "+" if obj.category == 'in' else "-"
        return format_html('<b style="color:{}; font-size:14px;">{}{} Tk</b>', color, symbol, f"{obj.payment:,}")
    payment_display.short_description = "Amount"

    # 1. This removes the green "Add loan transaction" button
    def has_add_permission(self, request):
        return False

    # 2. This removes the checkboxes and the "0 of 4 selected" bar
    def has_delete_permission(self, request, obj=None):
        return False

    # Optional: If you want to prevent clicking into a transaction to edit it
    def has_change_permission(self, request, obj=None):
        return False



# ─────────────────────────────────────────────
# EMI PAYMENT
# ─────────────────────────────────────────────
@admin.register(EMIPayment)
class EMIPaymentAdmin(admin.ModelAdmin):
    # Removed 'payment_action' to take away Admin control
    list_display = (
        'id', 'loan_link', 'customer_name', 'installment_no',
        'due_date', 'emi_amount', 'interest_income', 'principal_deduct', 
        'status_badge', 'paid_date',
    )
    
    list_filter = ('is_paid', 'due_date')
    search_fields = ('loan__customer__user__username', 'loan__customer__first_name', 'loan__customer__last_name')
    ordering = ('loan', 'installment_no')

    # All fields are read-only to ensure the admin cannot manually change payment status
    readonly_fields = (
        'loan', 'installment_no', 'due_date', 'emi_amount', 
        'principal_component', 'interest_component', 'balance', 
        'is_paid', 'paid_date'
    )

    def customer_name(self, obj):
        return obj.loan.customer.user.username
    customer_name.short_description = "Customer"

    def loan_link(self, obj):
        url = reverse('admin:loanApp_loanrequest_change', args=[obj.loan.pk])
        return format_html('<a href="{}">Loan #{}</a>', url, obj.loan.pk)
    loan_link.short_description = "Loan"

    def status_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;color:#155724;background:#d4edda;">Paid</span>')
        if obj.due_date < date.today():
            return format_html('<span style="padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;color:#721c24;background:#f8d7da;">Overdue</span>')
        return format_html('<span style="padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;color:#856404;background:#fff3cd;">Pending</span>')
    status_badge.short_description = "Status"

    def interest_income(self, obj):
        return format_html('<span style="color:#155724; font-weight:bold;">{} Tk</span>', obj.interest_component)
    interest_income.short_description = "Income"

    def principal_deduct(self, obj):
        return f"{obj.principal_component} Tk"
    principal_deduct.short_description = "Deduct"

    # Security: Disable manual record creation and selection checkboxes
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

    # ... keep your existing loan_link, customer_name, and status_badge methods ...
# Remove the @admin.register(loanRequest) from the top of the class
# and put this at the very bottom of the file:

try:
    admin.site.register(loanRequest, LoanRequestAdmin)
except admin.sites.AlreadyRegistered:
    pass