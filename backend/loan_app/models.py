from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CustomerProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    surname = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    id_document = models.FileField(upload_to='id_documents/')
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_customers')
    
    def __str__(self):
        return f"{self.first_name} {self.surname}"

class LoanType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.IntegerField(default=12)
    
    def __str__(self):
        return self.name

class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
    ]
    
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    application_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    credit_score = models.IntegerField(default=0)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    
    def calculate_approval_score(self):
        credit_weight = 0.4
        income_weight = 0.4
        amount_weight = 0.2
        
        credit_score_norm = min(self.credit_score / 850 * 100, 100)
        income_norm = min((self.customer.annual_income / 100000) * 100, 100)
        amount_norm = 100 - (self.requested_amount / self.loan_type.max_amount * 100)
        
        final_score = (
            credit_score_norm * credit_weight +
            income_norm * income_weight +
            amount_norm * amount_weight
        )
        return final_score
    
    def should_approve(self):
        score = self.calculate_approval_score()
        return score >= 60
    
    def __str__(self):
        return f"{self.customer.first_name} - {self.loan_type.name}"