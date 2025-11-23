from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomerProfile, LoanApplication, LoanType
from .forms import CustomerRegistrationForm, LoanApplicationForm

def home(request):
    return render(request, 'loan_app/home.html')

def customer_signup(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.status = 'pending'
            customer.save()
            messages.success(request, 'Registration successful! Please wait for admin approval. You will receive login credentials via email.')
            return redirect('home')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'loan_app/customer_signup.html', {'form': form})

def customer_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                customer_profile = CustomerProfile.objects.get(user=user)
                if customer_profile.status == 'approved':
                    login(request, user)
                    return redirect('customer_dashboard')
                else:
                    messages.error(request, 'Your account is not approved yet.')
            except CustomerProfile.DoesNotExist:
                messages.error(request, 'Invalid customer account.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'loan_app/customer_login.html')

@login_required
def customer_dashboard(request):
    try:
        customer_profile = CustomerProfile.objects.get(user=request.user)
        applications = LoanApplication.objects.filter(customer=customer_profile)
        return render(request, 'loan_app/customer_dashboard.html', {
            'customer': customer_profile,
            'applications': applications
        })
    except CustomerProfile.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('home')

@login_required
def apply_loan(request):
    customer_profile = CustomerProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.customer = customer_profile
            application.save()
            messages.success(request, 'Loan application submitted successfully!')
            return redirect('customer_dashboard')
    else:
        form = LoanApplicationForm()
    
    return render(request, 'loan_app/apply_loan.html', {
        'form': form,
        'loan_types': LoanType.objects.all()
    })

def logout_view(request):
    logout(request)
    return redirect('home')