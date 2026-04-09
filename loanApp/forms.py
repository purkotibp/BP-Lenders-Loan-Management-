from django import forms
from .models import loanRequest, loanTransaction

class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = loanRequest
        # Added 'document' to the fields tuple
        fields = ('category', 'reason', 'amount', 'year', 'document')
        
        # Optional: You can add custom widgets here to help widget_tweaks
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
            'document': forms.FileInput(),
            'amount': forms.NumberInput(attrs={
                'placeholder': 'Enter amount in Rs.',
                'help_text': 'Amount in Nepalese Rupees (Rs.)'
            }),
            'year': forms.NumberInput(attrs={
                'placeholder': 'Enter loan duration in years'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(LoanRequestForm, self).__init__(*args, **kwargs)
        # Add help text to amount field
        self.fields['amount'].help_text = 'Enter the loan amount in Nepalese Rupees (Rs.)'
        self.fields['amount'].label = 'Loan Amount (Rs.)'
        self.fields['year'].label = 'Duration (Years)'
        self.fields['category'].label = 'Loan Category'
        self.fields['reason'].label = 'Reason for Loan'
        self.fields['document'].label = 'Supporting Document'

class LoanTransactionForm(forms.ModelForm):
    class Meta:
        model = loanTransaction
        fields = ('payment',)
        widgets = {
            'payment': forms.NumberInput(attrs={
                'placeholder': 'Enter payment amount in Rs.',
                'help_text': 'Amount in Nepalese Rupees (Rs.)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(LoanTransactionForm, self).__init__(*args, **kwargs)
        # Add help text and label to payment field
        self.fields['payment'].help_text = 'Enter the payment amount in Nepalese Rupees (Rs.)'
        self.fields['payment'].label = 'Payment Amount (Rs.)'