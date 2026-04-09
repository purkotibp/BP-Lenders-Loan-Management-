from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import LoanRequestForm, LoanTransactionForm
from .models import loanRequest, loanTransaction, CustomerLoan, EMIPayment
from django.db.models import Sum
from datetime import date

# Helper to handle empty sums
def get_sum(queryset, field):
    result = queryset.aggregate(Sum(field))[f'{field}__sum']
    return result if result else 0

# Home View - Fixed the AttributeError
def home(request):
    return render(request, 'home.html')

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # <--- REQUIRED FOR NOTIFICATIONS
from .forms import LoanRequestForm

@login_required(login_url='/account/login-customer/')
def loan_request_view(request):
    if request.method == 'POST':
        # Handle both POST data and uploaded FILES
        form = LoanRequestForm(request.POST, request.FILES) 
        if form.is_valid():
            loan_obj = form.save(commit=False)
            loan_obj.customer = request.user.customer
            loan_obj.save()
            
            # 1. ADD SUCCESS MESSAGE HERE
            messages.success(request, f'Your loan request for Rs. {loan_obj.amount} has been submitted successfully!')
            
            # Redirect to dashboard
            return redirect('loanApp:user_dashboard') 
    else:
        form = LoanRequestForm()
        
    return render(request, 'loanApp/loanrequest.html', {'form': form})



import json # Added to safely pass the interest map to JS
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import loanRequest, CustomerLoan, EMIPayment, loanTransaction
from .forms import LoanTransactionForm # Ensure this import is correct

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import loanRequest, CustomerLoan, EMIPayment, loanTransaction
from .forms import LoanTransactionForm

@login_required(login_url='/account/login-customer/')
def LoanPayment(request):
    customer = request.user.customer
    
    # 1. Fetch Approved Loans for the dropdown
    active_loans = loanRequest.objects.filter(customer=customer, status='approved')
    
    # 2. Calculate Total Due for the Dashboard Header
    unpaid_emis = EMIPayment.objects.filter(loan__customer=customer, is_paid=False)
    total_due = sum(emi.emi_amount for emi in unpaid_emis)

    # 3. Build Interest Map for JavaScript Autofill
    interest_map = {}
    for loan in active_loans:
        # Get the very next unpaid EMI for this specific loan
        next_emi = EMIPayment.objects.filter(
            loan=loan, 
            is_paid=False
        ).order_by('installment_no').first()
        
        # We use string keys for the dictionary to ensure JS reads them correctly as Object Keys
        interest_map[str(loan.id)] = float(next_emi.interest_component) if next_emi else 0.0

    if request.method == 'POST':
        form = LoanTransactionForm(request.POST)
        if form.is_valid():
            pay_obj = form.save(commit=False)
            pay_obj.customer = customer
            pay_obj.category = 'in'  # This marks it as money coming INTO the bank
            
            # Retrieve values from the submitted form
            payment_type = request.POST.get('payment_type')
            selected_loan_id = request.POST.get('loan_account')
            
            pay_obj.payment_type = payment_type
            # Link to the loan ID so the models.py signal knows which schedule to update
            pay_obj.loan_account = int(selected_loan_id)

            # AUTO-SET AMOUNT: If 'interest' is selected, override input with schedule amount
            if payment_type == 'interest':
                # We pull the actual interest component from our map to ensure accuracy
                actual_interest = interest_map.get(str(selected_loan_id), 0)
                pay_obj.payment = int(actual_interest)
            
            pay_obj.save() 
            
            # Show the success invoice
            return render(request, 'loanApp/payment_invoice.html', {'transaction': pay_obj})
    else:
        form = LoanTransactionForm()
            
    return render(request, 'loanApp/payment.html', {
        'form': form, 
        'customer_loans': active_loans, 
        'total_due': total_due, 
        # json.dumps converts the Python dict into a JS-friendly JSON string
        'interest_json': json.dumps(interest_map) 
    })

@login_required(login_url='/account/login-customer/')
def UserDashboard(request):
    customer = request.user.customer
    loan_qs = loanRequest.objects.filter(customer=customer)
    cl_qs = CustomerLoan.objects.filter(customer=customer)
    
    # NEW: Also get transactions to calculate total paid amount for the template
    transaction_qs = loanTransaction.objects.filter(customer=customer)
    
    # Consistent Math: Due amount comes from the Schedule
    unpaid_emis = EMIPayment.objects.filter(loan__customer=customer, is_paid=False)
    total_due = sum(emi.emi_amount for emi in unpaid_emis)

    # Calculate Total Paid for the template
    total_paid_amt = get_sum(transaction_qs, 'payment')

    context = {
        'request': loan_qs.count(),
        'approved': loan_qs.filter(status='approved').count(),
        'rejected': loan_qs.filter(status='rejected').count(),
        'totalLoan': get_sum(cl_qs, 'total_loan'),
        'totalPayable': get_sum(cl_qs, 'payable_loan'),
        'totalPaid': total_paid_amt,  # ADDED THIS LINE TO FIX THE ERROR
        'totalDue': total_due
    }
    return render(request, 'loanApp/user_dashboard.html', context)


@login_required(login_url='/account/login-customer/')
def UserTransaction(request):
    transactions = loanTransaction.objects.filter(customer=request.user.customer).order_by('-payment_date')
    return render(request, 'loanApp/user_transaction.html', {'transactions': transactions})

@login_required(login_url='/account/login-customer/')
def UserLoanHistory(request):
    # This allows {{ loan.amount }} to work in your Portfolio table
    loans = loanRequest.objects.filter(customer=request.user.customer).order_by('-id')
    return render(request, 'loanApp/user_loan_history.html', {'loans': loans})

from django.db.models import Sum # Ensure this is imported at the top

@login_required(login_url='/account/login-customer/')
def EMISchedule(request, loan_id):
    # Fetch the loan and the schedule
    loan = get_object_or_404(loanRequest, id=loan_id, customer=request.user.customer)
    schedule = EMIPayment.objects.filter(loan=loan).order_by('installment_no')

    # Calculate Totals for the Summary Cards and Table Footer
    # We use .aggregate to let the database do the math efficiently
    totals = schedule.aggregate(
        total_emi=Sum('emi_amount'),
        total_interest=Sum('interest_component'),
        total_principal=Sum('principal_component')
    )

    context = {
        'loan': loan,
        'schedule': schedule,
        'today': date.today(),
        # Pass the calculated values to the template
        'total_emi': totals['total_emi'] or 0,
        'total_interest': totals['total_interest'] or 0,
        'total_principal': totals['total_principal'] or 0,
    }
    return render(request, 'loanApp/emi_schedule.html', context)

def error_404_view(request, exception):
    return render(request, '404.html', status=404)