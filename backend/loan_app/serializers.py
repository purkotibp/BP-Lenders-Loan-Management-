from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CustomerProfile, LoanType, LoanApplication

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'approved_at', 'approved_by']

class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'first_name', 'middle_name', 'surname', 'gender', 'date_of_birth',
            'nationality', 'address', 'phone_number', 'email', 'id_document',
            'father_name', 'mother_name', 'profession', 'annual_income',
            'password', 'confirm_password'
        ]
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        customer = CustomerProfile.objects.create(**validated_data)
        return customer

class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = '__all__'

class LoanApplicationSerializer(serializers.ModelSerializer):
    loan_type_name = serializers.CharField(source='loan_type.name', read_only=True)
    approval_score = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanApplication
        fields = '__all__'
        read_only_fields = ['customer', 'application_date', 'status', 'reviewed_by', 'reviewed_date']
    
    def get_approval_score(self, obj):
        return obj.calculate_approval_score()