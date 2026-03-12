from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import LoanRequestForm, LoanTransactionForm
from .models import loanRequest, loanTransaction, CustomerLoan, EMIPayment
from django.db.models import Sum
from datetime import date

# --- Helper function to handle None values in Sum ---
def get_sum(queryset, field):
    result = queryset.aggregate(Sum(field))[f'{field}__sum']
    return result if result else 0

def home(request):
    return render(request, 'home.html')

# loanApp/views.py

@login_required(login_url='/account/login-customer/')
def loan_request_view(request):
    form = LoanRequestForm()
    if request.method == 'POST':
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            loan_obj = form.save(commit=False)
            loan_obj.customer = request.user.customer
            loan_obj.save()
            return redirect('home')
    return render(request, 'loanApp/loanrequest.html', {'form': form})

@login_required(login_url='/account/login-customer/')
def LoanPayment(request):
    form = LoanTransactionForm()
    if request.method == 'POST':
        form = LoanTransactionForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.customer = request.user.customer
            payment.save()
            return redirect('home')
    return render(request, 'loanApp/payment.html', {'form': form})

@login_required(login_url='/account/login-customer/')
def UserTransaction(request):
    transactions = loanTransaction.objects.filter(customer=request.user.customer).order_by('-id')
    return render(request, 'loanApp/user_transaction.html', {'transactions': transactions})

@login_required(login_url='/account/login-customer/')
def UserLoanHistory(request):
    loans = loanRequest.objects.filter(customer=request.user.customer).order_by('-id')
    return render(request, 'loanApp/user_loan_history.html', {'loans': loans})

@login_required(login_url='/account/login-customer/')
def UserDashboard(request):
    # Filter by current customer
    customer_qs = loanRequest.objects.filter(customer=request.user.customer)
    customer_loan_qs = CustomerLoan.objects.filter(customer=request.user.customer)
    transaction_qs = loanTransaction.objects.filter(customer=request.user.customer)

    # REMOVED the trailing commas here to prevent Tuple conversion
    request_count = customer_qs.count()
    approved_count = customer_qs.filter(status='approved').count()
    rejected_count = customer_qs.filter(status='rejected').count()
    
    # Using helper to handle 'None' results if no loans exist
    total_loan_amt = get_sum(customer_loan_qs, 'total_loan')
    total_payable_amt = get_sum(customer_loan_qs, 'payable_loan')
    total_paid_amt = get_sum(transaction_qs, 'payment')

    context = {
        'request': request_count,
        'approved': approved_count,
        'rejected': rejected_count,
        'totalLoan': total_loan_amt,
        'totalPayable': total_payable_amt,
        'totalPaid': total_paid_amt,
        'totalDue': total_payable_amt - total_paid_amt # Direct calculation
    }

    return render(request, 'loanApp/user_dashboard.html', context)

@login_required(login_url='/account/login-customer/')
def EMISchedule(request, loan_id):
    loan = get_object_or_404(loanRequest, id=loan_id, customer=request.user.customer)
    schedule = EMIPayment.objects.filter(loan=loan)

    # Use Django's sum logic or python sum
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

# loanApp/views.py
from django.shortcuts import render

def error_404_view(request, exception):
    return render(request, '404.html', status=404) 
