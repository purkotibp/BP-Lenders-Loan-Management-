from django.db import models
from django.contrib.auth.models import User
from loginApp.models import CustomerSignUp
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
# Create your models here.


class loanCategory(models.Model):
    loan_name = models.CharField(max_length=250)
    creation_date = models.DateField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.loan_name


class loanRequest(models.Model):
    customer = models.ForeignKey(
        CustomerSignUp, on_delete=models.CASCADE, related_name='loan_customer')
    category = models.ForeignKey(
        loanCategory, on_delete=models.CASCADE, null=True)
    request_date = models.DateField(auto_now_add=True)
    status_date = models.CharField(
        max_length=150, null=True, blank=True, default=None)
    reason = models.TextField()
    status = models.CharField(max_length=100, default='pending')
    amount = models.PositiveIntegerField(default=0)
    year = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.customer.user.username


class CustomerLoan(models.Model):
    customer = models.ForeignKey(
        CustomerSignUp, on_delete=models.CASCADE, related_name='loan_user')
    total_loan = models.PositiveIntegerField(default=0)
    payable_loan = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.customer.user.username


class loanTransaction(models.Model):
    customer = models.ForeignKey(
        CustomerSignUp, on_delete=models.CASCADE, related_name='transaction_customer')

    transaction = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.PositiveIntegerField(default=0)
    payment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.customer.user.username


class EMIPayment(models.Model):
    loan = models.ForeignKey(
        loanRequest, on_delete=models.CASCADE, related_name='emi_payments')
    installment_no = models.PositiveIntegerField()
    due_date = models.DateField()
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_component = models.DecimalField(max_digits=12, decimal_places=2)
    interest_component = models.DecimalField(max_digits=12, decimal_places=2)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['installment_no']

    def __str__(self):
        return f"EMI #{self.installment_no} - {self.loan.customer.user.username}"


def _generate_emi_schedule(loan_instance):
    """
    Generate EMI amortization schedule for a loanRequest.
    Uses annual interest rate of 12% (same rate used across the system).
    """
    ANNUAL_RATE = Decimal('0.12')
    principal = Decimal(str(loan_instance.amount))
    months = int(loan_instance.year) * 12
    monthly_rate = ANNUAL_RATE / 12

    # Standard EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)
    if monthly_rate == 0:
        emi = (principal / months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        factor = (1 + monthly_rate) ** months
        emi = (principal * monthly_rate * factor / (factor - 1)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Delete any existing schedule before regenerating
    EMIPayment.objects.filter(loan=loan_instance).delete()

    balance = principal
    start_date = date.today()
    emi_records = []

    for i in range(1, months + 1):
        interest = (balance * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # On last installment adjust for rounding drift
        if i == months:
            principal_component = balance
            emi_amount = balance + interest
        else:
            principal_component = (emi - interest).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            emi_amount = emi

        balance = (balance - principal_component).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        due_date = start_date + relativedelta(months=i)

        emi_records.append(EMIPayment(
            loan=loan_instance,
            installment_no=i,
            due_date=due_date,
            emi_amount=emi_amount,
            principal_component=principal_component,
            interest_component=interest,
            balance=max(balance, Decimal('0.00')),
        ))

    EMIPayment.objects.bulk_create(emi_records)


# Attach the method to loanRequest
loanRequest.generate_emi_schedule = _generate_emi_schedule
