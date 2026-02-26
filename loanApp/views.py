from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import LoanRequestForm, LoanTransactionForm
from .models import loanRequest, loanTransaction, CustomerLoan, EMIPayment
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from datetime import date

from django.db.models import Sum
# Create your views here.


# @login_required(login_url='/account/login-customer')
def home(request):

    return render(request, 'home.html', context={})


@login_required(login_url='/account/login-customer')
def LoanRequest(request):

    form = LoanRequestForm()

    if request.method == 'POST':
        form = LoanRequestForm(request.POST)

        if form.is_valid():
            loan_obj = form.save(commit=False)
            loan_obj.customer = request.user.customer
            loan_obj.save()
            return redirect('/')

    return render(request, 'loanApp/loanrequest.html', context={'form': form})

    # reason = request.POST.get('reason')
    # amount = request.POST.get('amount')
    # category = request.POST.get('category')
    # year = request.POST.get('year')
    # customer = request.user.customer

    # loan_request = LoanRequest(request)
    # loan_request.customer = customer
    # loan_request.save()
    # if form.is_valid():
    #     loan_request = form.save(commit=False)
    #     loan_request.customer = request.user.customer
    #     print(loan_request)
    #     return redirect('/')


@login_required(login_url='/account/login-customer')
def LoanPayment(request):
    form = LoanTransactionForm()
    if request.method == 'POST':
        form = LoanTransactionForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.customer = request.user.customer
            payment.save()
            # pay_save = loanTransaction()
            return redirect('/')

    return render(request, 'loanApp/payment.html', context={'form': form})


@login_required(login_url='/account/login-customer')
def UserTransaction(request):
    transactions = loanTransaction.objects.filter(
        customer=request.user.customer)
    return render(request, 'loanApp/user_transaction.html', context={'transactions': transactions})


@login_required(login_url='/account/login-customer')
def UserLoanHistory(request):
    loans = loanRequest.objects.filter(
        customer=request.user.customer)
    return render(request, 'loanApp/user_loan_history.html', context={'loans': loans})


@login_required(login_url='/account/login-customer')
def UserDashboard(request):

    requestLoan = loanRequest.objects.all().filter(
        customer=request.user.customer).count(),
    approved = loanRequest.objects.all().filter(
        customer=request.user.customer).filter(status='approved').count(),
    rejected = loanRequest.objects.all().filter(
        customer=request.user.customer).filter(status='rejected').count(),
    totalLoan = CustomerLoan.objects.filter(customer=request.user.customer).aggregate(Sum('total_loan'))[
        'total_loan__sum'],
    totalPayable = CustomerLoan.objects.filter(customer=request.user.customer).aggregate(
        Sum('payable_loan'))['payable_loan__sum'],
    totalPaid = loanTransaction.objects.filter(customer=request.user.customer).aggregate(Sum('payment'))[
        'payment__sum'],
    

    dict = {
        'request': requestLoan[0],
        'approved': approved[0],
        'rejected': rejected[0],
        'totalLoan': totalLoan[0],
        'totalPayable': totalPayable[0],
        'totalPaid': totalPaid[0],
        

    }

    return render(request, 'loanApp/user_dashboard.html', context=dict)


@login_required(login_url='/account/login-customer')
def EMISchedule(request, loan_id):
    loan = get_object_or_404(loanRequest, id=loan_id, customer=request.user.customer)
    schedule = EMIPayment.objects.filter(loan=loan)

    # Totals for summary row
    total_emi = sum(p.emi_amount for p in schedule)
    total_interest = sum(p.interest_component for p in schedule)
    total_principal = sum(p.principal_component for p in schedule)

    context = {
        'loan': loan,
        'schedule': schedule,
        'total_emi': total_emi,
        'total_interest': total_interest,
        'total_principal': total_principal,
        'today': date.today(),
    }
    return render(request, 'loanApp/emi_schedule.html', context)


def error_404_view(request, exception):
    print("not found")
    return render(request, 'notFound.html')
