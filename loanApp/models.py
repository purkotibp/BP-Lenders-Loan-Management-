from django.db import models
from django.contrib.auth.models import User
from loginApp.models import CustomerSignUp
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    amount = models.PositiveIntegerField(
        default=0,
        help_text="Enter amount in Rs.",
        verbose_name="Amount (Rs.)"
    )
    year = models.PositiveIntegerField(default=1)

    document = models.FileField(upload_to='loan_docs/', null=True, blank=True)
    
    def __str__(self):
        return self.customer.user.username


class CustomerLoan(models.Model):
    customer = models.ForeignKey(
        CustomerSignUp, on_delete=models.CASCADE, related_name='loan_user')
    total_loan = models.PositiveIntegerField(
        default=0,
        help_text="Total loan amount in Rs.",
        verbose_name="Total Loan (Rs.)"
    )
    payable_loan = models.PositiveIntegerField(
        default=0,
        help_text="Total payable amount including interest in Rs.",
        verbose_name="Payable Loan (Rs.)"
    )

    def __str__(self):
        return self.customer.user.username


class loanTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('out', 'Loan Disbursement (Out)'),
        ('in', 'EMI Collection (In)'),
    )

    PAYMENT_CATEGORIES = (
        ('interest', 'Interest Payment'),
        ('principal', 'Loan Repayment (Principal)'),
    )

    customer = models.ForeignKey(
        CustomerSignUp, on_delete=models.CASCADE, related_name='transaction_customer')

    transaction = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    
    category = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='in')
    
    payment_type = models.CharField(
        max_length=20, 
        choices=PAYMENT_CATEGORIES, 
        default='interest'
    )
    
    payment = models.PositiveIntegerField(
        default=0,
        help_text="Enter payment amount in Rs.",
        verbose_name="Payment Amount (Rs.)"
    )
    payment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.get_payment_type_display()}"
    

class EMIPayment(models.Model):
    loan = models.ForeignKey(
        loanRequest, on_delete=models.CASCADE, related_name='emi_payments')
    installment_no = models.PositiveIntegerField()
    due_date = models.DateField()
    emi_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="EMI amount in Rs.",
        verbose_name="EMI Amount (Rs.)"
    )
    principal_component = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Principal component in Rs.",
        verbose_name="Principal (Rs.)"
    )
    interest_component = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Interest component in Rs.",
        verbose_name="Interest (Rs.)"
    )
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Remaining balance in Rs.",
        verbose_name="Balance (Rs.)"
    )
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['installment_no']

    def __str__(self):
        return f"EMI #{self.installment_no} - {self.loan.customer.user.username}"


def _generate_emi_schedule(loan_instance):
    ANNUAL_RATE = Decimal('0.12')
    principal = Decimal(str(loan_instance.amount))
    months = int(loan_instance.year) * 12
    monthly_rate = ANNUAL_RATE / 12

    if monthly_rate == 0:
        emi = (principal / months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        factor = (1 + monthly_rate) ** months
        emi = (principal * monthly_rate * factor / (factor - 1)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)

    EMIPayment.objects.filter(loan=loan_instance).delete()

    balance = principal
    start_date = date.today()
    emi_records = []

    for i in range(1, months + 1):
        interest = (balance * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
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

loanRequest.generate_emi_schedule = _generate_emi_schedule

@receiver(post_save, sender=EMIPayment)
def delete_loan_on_completion(sender, instance, **kwargs):
    loan = instance.loan
    if instance.is_paid:
        has_pending_emi = EMIPayment.objects.filter(loan=loan, is_paid=False).exists()
        if not has_pending_emi:
            print(f"Loan ID {loan.id} fully paid. Deleting record...")
            loan.delete()


# At the very bottom of models.py

@receiver(post_save, sender=loanTransaction)
def update_schedule_on_payment(sender, instance, created, **kwargs):
    if created:
        # 1. Find the first 'Pending' installment for this customer
        # We order by installment_no so it pays them in order (1, 2, 3...)
        next_emi = EMIPayment.objects.filter(
            loan__customer=instance.customer, 
            is_paid=False
        ).order_by('installment_no').first()

        # 2. If we find one, mark it as Paid and save it
        if next_emi:
            next_emi.is_paid = True
            next_emi.paid_date = instance.payment_date # Marks the date of payment
            next_emi.save() # This is the part that changes the status in your table