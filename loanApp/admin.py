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
@admin.register(loanCategory)
class LoanCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan_name', 'creation_date', 'updated_date')
    search_fields = ('loan_name',)
    ordering = ('loan_name',)


# ─────────────────────────────────────────────
# Custom admin actions for LoanRequest
# ─────────────────────────────────────────────
def _process_loan_approval(loan_obj):
    """Core approval logic - same as managerApp.views.approved_request."""
    today = date.today()
    loan_obj.status_date = today.strftime("%B %d, %Y")
    loan_obj.status = 'approved'
    loan_obj.save()

    year = loan_obj.year
    approved_customer = loan_obj.customer

    if CustomerLoan.objects.filter(customer=approved_customer).exists():
        existing = CustomerLoan.objects.get(customer=approved_customer)
        existing.total_loan = int(existing.total_loan) + int(loan_obj.amount)
        existing.payable_loan = (
            int(existing.payable_loan)
            + int(loan_obj.amount)
            + int(loan_obj.amount) * 0.12 * int(year)
        )
        existing.save()
    else:
        CustomerLoan.objects.create(
            customer=approved_customer,
            total_loan=int(loan_obj.amount),
            payable_loan=int(loan_obj.amount) + int(loan_obj.amount) * 0.12 * int(year),
        )

    loan_obj.refresh_from_db()
    loan_obj.generate_emi_schedule(loan_obj)


def approve_loans(modeladmin, request, queryset):
    count = 0
    for loan in queryset.filter(status='pending'):
        _process_loan_approval(loan)
        count += 1
    modeladmin.message_user(request, f"{count} loan(s) approved and EMI schedules generated.")

approve_loans.short_description = "Approve selected loan requests"


def reject_loans(modeladmin, request, queryset):
    today = date.today()
    count = queryset.filter(status='pending').update(
        status='rejected',
        status_date=today.strftime("%B %d, %Y"),
    )
    modeladmin.message_user(request, f"{count} loan(s) rejected.")

reject_loans.short_description = "Reject selected loan requests"


def regenerate_emi_schedule(modeladmin, request, queryset):
    count = 0
    for loan in queryset.filter(status='approved'):
        loan.generate_emi_schedule(loan)
        count += 1
    modeladmin.message_user(request, f"EMI schedule regenerated for {count} loan(s).")

regenerate_emi_schedule.short_description = "Regenerate EMI schedule (approved loans only)"


# ─────────────────────────────────────────────
# Loan Request
# ─────────────────────────────────────────────
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect

class LoanRequestAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    # 1. Define your helper methods FIRST inside the class
    def customer_name(self, obj):
        return obj.customer.user.username
    customer_name.short_description = "Customer"

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
        # MAKE SURE 'document' IS THE CORRECT FIELD NAME IN YOUR MODEL
        if hasattr(obj, 'document') and obj.document:
            return format_html('<a class="btn btn-info btn-sm" href="{}" target="_blank">View Doc</a>', obj.document.url)
        return "No Doc"

    def loan_actions(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a class="btn btn-success btn-sm" href="approve/{}/" style="color:white;background:#28a745;padding:2px 5px;margin-right:4px;">Approve</a>'
                '<a class="btn btn-danger btn-sm" href="reject/{}/" style="color:white;background:#dc3545;padding:2px 5px;">Reject</a>',
                obj.pk, obj.pk
            )
        return "Processed"

    # 2. Now set list_display referencing the names above
    list_display = (
        'id', 'customer_name', 'category', 'amount_display',
        'year', 'status_badge', 'view_documents', 'loan_actions', 
        'request_date', 'emi_schedule_link',
    )

    # 3. Handle the URLs for the buttons
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:loan_id>/', self.admin_site.admin_view(self.approve_loan), name='approve_loan'),
            path('reject/<int:loan_id>/', self.admin_site.admin_view(self.reject_loan), name='reject_loan'),
        ]
        return custom_urls + urls

    def approve_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        loan.status = 'approved'
        loan.save()
        self.message_user(request, f"Loan {loan_id} Approved")
        return redirect('admin:loanApp_loanrequest_changelist')

    def reject_loan(self, request, loan_id):
        loan = self.get_object(request, loan_id)
        loan.status = 'rejected'
        loan.save()
        self.message_user(request, f"Loan {loan_id} Rejected", level='warning')
        return redirect('admin:loanApp_loanrequest_changelist')

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
    list_display = (
        'transaction', 'customer_name', 'payment_display', 'payment_date',
    )
    list_filter = ('payment_date',)
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
    customer_name.admin_order_field = 'customer__user__username'

    def payment_display(self, obj):
        return f"{obj.payment:,} Tk"
    payment_display.short_description = "Payment"
    payment_display.admin_order_field = 'payment'


# ─────────────────────────────────────────────
# EMI Payment
# ─────────────────────────────────────────────
@admin.register(EMIPayment)
class EMIPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'loan_link', 'customer_name', 'installment_no',
        'due_date', 'emi_amount', 'status_badge', 'paid_date',
    )
    list_filter = ('is_paid', 'due_date')
    search_fields = (
        'loan__customer__user__username',
        'loan__customer__first_name',
        'loan__customer__last_name',
    )
    ordering = ('loan', 'installment_no')
    readonly_fields = (
        'loan', 'installment_no', 'due_date',
        'emi_amount', 'principal_component', 'interest_component', 'balance',
    )

    fieldsets = (
        ('Loan Reference', {
            'fields': ('loan', 'installment_no'),
        }),
        ('Amounts', {
            'fields': ('emi_amount', 'principal_component', 'interest_component', 'balance'),
        }),
        ('Payment Status', {
            'fields': ('due_date', 'is_paid', 'paid_date'),
        }),
    )

    def loan_link(self, obj):
        url = reverse('admin:loanApp_loanrequest_change', args=[obj.loan.pk])
        return format_html('<a href="{}">Loan #{}</a>', url, obj.loan.pk)
    loan_link.short_description = "Loan"

    def customer_name(self, obj):
        return obj.loan.customer.user.username
    customer_name.short_description = "Customer"

    def status_badge(self, obj):
        if obj.is_paid:
            return format_html(
                '<span style="padding:3px 10px;border-radius:12px;font-size:12px;'
                'font-weight:600;color:#155724;background:#d4edda;">Paid</span>'
            )
        today = date.today()
        if obj.due_date < today:
            return format_html(
                '<span style="padding:3px 10px;border-radius:12px;font-size:12px;'
                'font-weight:600;color:#721c24;background:#f8d7da;">Overdue</span>'
            )
        return format_html(
            '<span style="padding:3px 10px;border-radius:12px;font-size:12px;'
            'font-weight:600;color:#856404;background:#fff3cd;">Pending</span>'
        )
    status_badge.short_description = "Status"
# Remove the @admin.register(loanRequest) from the top of the class
# and put this at the very bottom of the file:

try:
    admin.site.register(loanRequest, LoanRequestAdmin)
except admin.sites.AlreadyRegistered:
    pass