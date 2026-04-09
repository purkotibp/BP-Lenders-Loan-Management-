from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path, reverse
from django.db.models import Sum, F
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from datetime import date
from .models import loanRequest, loanCategory, CustomerLoan, loanTransaction, EMIPayment

# ────────────────────────────────────────────────────────────────────────
# 1. ADMIN SITE CUSTOMIZATION
# ────────────────────────────────────────────────────────────────────────
admin.site.site_header = "Loan Management System — Admin"
admin.site.site_title = "LMS Admin"
admin.site.index_title = "Welcome to the LMS Administration Panel"


# ────────────────────────────────────────────────────────────────────────
# 2. INLINE CONFIGURATION
# ────────────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────────────
# 3. LOAN CATEGORY ADMIN (With Password Intercept)
# ────────────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────────────
# 4. LOAN REQUEST ADMIN
# ────────────────────────────────────────────────────────────────────────
class LoanRequestAdmin(admin.ModelAdmin):
    inlines = [EMIPaymentInline]
    actions = None  
    actions_selection_counter = False  
    search_fields = ('customer__user__username', 'customer__first_name', 'customer__last_name')

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"

    def amount_display(self, obj):
        # CHANGED: Tk -> Rs.
        return f"Rs. {obj.amount:,}"
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
        if obj.status == 'pending':
            return format_html(
                '<a class="btn btn-success btn-sm" href="approve/{}/" style="color:white;background:#28a745;padding:2px 8px;text-decoration:none;border-radius:4px;">Approve</a>'
                '<a class="btn btn-danger btn-sm" href="reject/{}/" style="color:white;background:#dc3545;padding:2px 8px;text-decoration:none;border-radius:4px;">Reject</a>',
                obj.pk, obj.pk
            )
        return format_html('<span style="color:gray;">Processed</span>')

    list_display = (
        'id', 'customer_name', 'category', 'amount_display',
        'year', 'status_badge', 'view_documents', 'loan_actions', 
        'request_date', 'emi_schedule_link',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:loan_id>/', self.admin_site.admin_view(self.approve_loan), name='approve_loan'),
            path('reject/<int:loan_id>/', self.admin_site.admin_view(self.reject_loan), name='reject_loan'),
        ]
        return custom_urls + urls

    def approve_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        if loan.status != 'approved':
            loan.status = 'approved'
            loan.generate_emi_schedule() 
            loan.save()
            # Automatic Transaction Out
            loanTransaction.objects.create(customer=loan.customer, payment=loan.amount, category='out')
            self.message_user(request, f"Loan {loan_id} Approved and Disbursed.")
        return redirect('admin:loanApp_loanrequest_changelist')

    def reject_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        loan.status = 'rejected'
        loan.save()
        self.message_user(request, f"Loan {loan_id} Rejected", level='warning')
        return redirect('admin:loanApp_loanrequest_changelist')


# ────────────────────────────────────────────────────────────────────────
# 5. CUSTOMER LOAN ADMIN (Balance Ledger)
# ────────────────────────────────────────────────────────────────────────
@admin.register(CustomerLoan)
class CustomerLoanAdmin(admin.ModelAdmin):
    # FIXED: Methods defined before list_display to avoid E108
    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"

    def loan_category(self, obj):
        active_loan = loanRequest.objects.filter(customer=obj.customer, status='approved').first()
        return active_loan.category if active_loan else "N/A"
    loan_category.short_description = "Category"

    def principal_disbursed_box(self, obj):
        # CHANGED: Tk -> Rs.
        val_text = f"Rs. {obj.total_loan:,.0f}"
        return format_html('<div style="background:#f8f9fa; border:1px solid #dee2e6; padding:4px 10px; border-radius:5px; text-align:center; min-width:110px; display:inline-block; color:#212529; font-weight:bold;">{}</div>', val_text)
    principal_disbursed_box.short_description = "Principal Disbursed"

    def total_receivable_box(self, obj):
        # CHANGED: Tk -> Rs.
        val_text = f"Rs. {obj.payable_loan:,.0f}"
        return format_html('<div style="background:#e8f0fe; border:1px solid #b3d7ff; padding:4px 10px; border-radius:5px; text-align:center; min-width:110px; display:inline-block; color:#1a73e8; font-weight:bold;">{}</div>', val_text)
    total_receivable_box.short_description = "Total Receivable"

    def balance_receivable_box(self, obj):
        paid_sum = EMIPayment.objects.filter(loan__customer=obj.customer, is_paid=True).aggregate(Sum('emi_amount'))['emi_amount__sum'] or 0
        balance = float(obj.payable_loan) - float(paid_sum)
        color = "#d93025" if balance > 0 else "#1e8e3e"
        bg = "#fce8e6" if balance > 0 else "#e6f4ea"
        # CHANGED: Tk -> Rs.
        value_text = f"Rs. {balance:,.0f}"
        return format_html('<div style="background:{}; border:1px solid {}; padding:4px 10px; border-radius:5px; text-align:center; min-width:110px; display:inline-block; color:{}; font-weight:bold;">{}</div>', bg, color, color, value_text)
    balance_receivable_box.short_description = 'Balance Receivable'

    def view_document_button(self, obj):
        return format_html('<a class="button" href="/admin/loanApp/customerloan/{}/change/" style="background:#444; color:white; padding:4px 12px; border-radius:5px; text-decoration:none; font-weight:bold;">📄 Open Application File</a>', obj.id)
    view_document_button.short_description = "Application File"

    list_display = (
        'id', 'customer_name', 'loan_category', 
        'principal_disbursed_box', 'total_receivable_box', 
        'balance_receivable_box', 'view_document_button'
    )
    
    list_display_links = None 
    search_fields = ('customer__user__username', 'customer__first_name', 'customer__last_name')
    
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

    def get_readonly_fields(self, request, obj=None):
        if obj: return [f.name for f in obj._meta.fields] + ['customer_name', 'loan_category']
        return self.readonly_fields


# ────────────────────────────────────────────────────────────────────────
# 6. LOAN TRANSACTION ADMIN
# ────────────────────────────────────────────────────────────────────────
@admin.register(loanTransaction)
class LoanTransactionAdmin(admin.ModelAdmin):
    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"

    def type_badge(self, obj):
        if obj.category == 'in':
            return format_html('<span style="color:#155724; background:#d4edda; padding:2px 10px; border-radius:12px; font-weight:600;">INCOME</span>')
        return format_html('<span style="color:#721c24; background:#f8d7da; padding:2px 10px; border-radius:12px; font-weight:600;">EXPENSE</span>')

    def payment_display(self, obj):
        color = "#28a745" if obj.category == 'in' else "#dc3545"
        symbol = "+" if obj.category == 'in' else "-"
        # CHANGED: Tk -> Rs.
        return format_html('<b style="color:{}; font-size:14px;">{}{} Rs.</b>', color, symbol, f"{obj.payment:,}")
    payment_display.short_description = "Amount"

    list_display = ('transaction', 'customer_name', 'type_badge', 'payment_display', 'payment_date')
    list_filter = ('category', 'payment_date')
    readonly_fields = ('transaction', 'payment_date')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


# ────────────────────────────────────────────────────────────────────────
# 7. EMI PAYMENT ADMIN
# ────────────────────────────────────────────────────────────────────────
@admin.register(EMIPayment)
class EMIPaymentAdmin(admin.ModelAdmin):
    def customer_name(self, obj):
        return obj.loan.customer.user.username
    customer_name.short_description = "Customer"

    def emi_amount_display(self, obj):
        # CHANGED: Tk -> Rs.
        return f"Rs. {obj.emi_amount}"
    emi_amount_display.short_description = "EMI Amount"

    def interest_income(self, obj):
        # CHANGED: Tk -> Rs.
        return format_html('<span style="color:#155724; font-weight:bold;">Rs. {}</span>', obj.interest_component)
    interest_income.short_description = "Interest"

    def principal_deduct(self, obj):
        # CHANGED: Tk -> Rs.
        return f"Rs. {obj.principal_component}"
    principal_deduct.short_description = "Principal"

    def loan_link(self, obj):
        url = reverse('admin:loanApp_loanrequest_change', args=[obj.loan.pk])
        return format_html('<a href="{}">Loan #{}</a>', url, obj.loan.pk)
    loan_link.short_description = "Loan"

    def status_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="padding:3px 10px;border-radius:12px;color:#155724;background:#d4edda;">Paid</span>')
        return format_html('<span style="padding:3px 10px;border-radius:12px;color:#856404;background:#fff3cd;">Pending</span>')
    status_badge.short_description = "Status"

    list_display = (
        'id', 'loan_link', 'customer_name', 'installment_no',
        'due_date', 'emi_amount_display', 'interest_income', 'principal_deduct', 
        'status_badge', 'paid_date',
    )
    readonly_fields = ('loan', 'installment_no', 'due_date', 'emi_amount', 'principal_component', 'interest_component', 'balance', 'is_paid', 'paid_date')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


# Final registration check
try:
    admin.site.register(loanRequest, LoanRequestAdmin)
except admin.sites.AlreadyRegistered:
    pass