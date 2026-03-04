"""
managerApp/views.py

All admin functionality has been migrated to Django's built-in admin at /admin/.
Only the loan approval/rejection action endpoints are retained here for
backward compatibility (e.g. bookmarked direct links). The primary workflow
for staff is now through /admin/.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from datetime import date

from loanApp.models import loanRequest, CustomerLoan, EMIPayment, loanTransaction
from loginApp.models import CustomerSignUp
from django.db.models import Sum
from decimal import Decimal


@staff_member_required(login_url='/admin/login/')
def approved_request(request, id):
    today = date.today()
    status_date = today.strftime("%B %d, %Y")
    loan_obj = loanRequest.objects.get(id=id)
    loan_obj.status_date = status_date
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

    loanRequest.objects.filter(id=id).update(status='approved')
    loan_obj.refresh_from_db()
    loan_obj.generate_emi_schedule(loan_obj)

    return HttpResponseRedirect('/admin/loanApp/loanrequest/')


@staff_member_required(login_url='/admin/login/')
def rejected_request(request, id):
    today = date.today()
    status_date = today.strftime("%B %d, %Y")
    loanRequest.objects.filter(id=id).update(
        status='rejected',
        status_date=status_date,
    )
    return HttpResponseRedirect('/admin/loanApp/loanrequest/')


@staff_member_required(login_url='/admin/login/')
def customer_loans(request):
    """
    Admin page: every registered customer + their full loan portfolio.
    """
    from loginApp.models import CustomerSignUp
    from loanApp.models import loanRequest, CustomerLoan, EMIPayment, loanTransaction
    from django.db.models import Sum
    from datetime import date

    customers = CustomerSignUp.objects.select_related('user').all().order_by('user__date_joined')

    total_disbursed   = CustomerLoan.objects.aggregate(s=Sum('total_loan'))['s'] or 0
    total_payable_all = CustomerLoan.objects.aggregate(s=Sum('payable_loan'))['s'] or 0
    total_paid_all    = loanTransaction.objects.filter(category='in').aggregate(s=Sum('payment'))['s'] or 0
    total_outstanding = max(int(total_payable_all) - int(total_paid_all), 0)
    pending_count     = loanRequest.objects.filter(status='pending').count()
    total_loans       = loanRequest.objects.filter(status='approved').count()

    customer_data = []
    today = date.today()

    for customer in customers:
        loans_qs      = loanRequest.objects.filter(customer=customer).order_by('-request_date')
        customer_loan = CustomerLoan.objects.filter(customer=customer).first()

        paid_amount = loanTransaction.objects.filter(
            customer=customer, category='in'
        ).aggregate(s=Sum('payment'))['s'] or 0

        outstanding = 0
        paid_pct    = 0
        if customer_loan:
            outstanding = max(int(customer_loan.payable_loan) - int(paid_amount), 0)
            if customer_loan.payable_loan > 0:
                paid_pct = min(int(paid_amount * 100 / customer_loan.payable_loan), 100)

        loans = []
        has_overdue = False
        for loan in loans_qs:
            emis       = EMIPayment.objects.filter(loan=loan)
            total_emis = emis.count()
            paid_emis  = emis.filter(is_paid=True).count()
            first_emi  = emis.first()
            emi_amount = first_emi.emi_amount if first_emi else None
            if emis.filter(is_paid=False, due_date__lt=today).exists():
                has_overdue = True

            loans.append({
                'id':          loan.id,
                'category':    loan.category,
                'amount':      loan.amount,
                'year':        loan.year,
                'request_date': loan.request_date,
                'status':      loan.status,
                'emi_amount':  emi_amount,
                'total_emis':  total_emis,
                'paid_emis':   paid_emis,
            })

        customer_data.append({
            'customer':      customer,
            'customer_loan': customer_loan,
            'loans':         loans,
            'paid_amount':   paid_amount,
            'outstanding':   outstanding,
            'paid_pct':      paid_pct,
            'has_overdue':   has_overdue,
        })

    context = {
        'customer_data':     customer_data,
        'total_customers':   customers.count(),
        'total_loans':       total_loans,
        'total_disbursed':   f"{int(total_disbursed):,}",
        'total_outstanding': f"{total_outstanding:,}",
        'pending_count':     pending_count,
    }
    return render(request, 'admin/customer_loans.html', context)