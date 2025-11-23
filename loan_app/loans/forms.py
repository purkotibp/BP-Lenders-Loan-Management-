from django import forms
from .models import CustomerProfile, LoanApplication

class CustomerRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = CustomerProfile
        fields = [
            'first_name', 'middle_name', 'surname', 'gender', 'date_of_birth',
            'nationality', 'address', 'phone_number', 'email', 'id_document',
            'father_name', 'mother_name', 'profession', 'annual_income'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'id_document': forms.FileInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = ['loan_type', 'requested_amount', 'purpose', 'credit_score']
        widgets = {
            'loan_type': forms.Select(attrs={'class': 'form-control'}),
            'requested_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'credit_score': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '850'}),
        }