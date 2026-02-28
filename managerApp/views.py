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

from loanApp.models import loanRequest, CustomerLoan, EMIPayment


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
