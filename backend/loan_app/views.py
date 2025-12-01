from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from .models import CustomerProfile, LoanType, LoanApplication
from .serializers import (
    CustomerProfileSerializer, CustomerRegistrationSerializer,
    LoanTypeSerializer, LoanApplicationSerializer
)

def generate_random_password():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(8))

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return []  # No authentication needed for registration
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'], permission_classes=[])
    def register(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            return Response({
                'message': 'Registration successful! Please wait for admin approval.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        customer = self.get_object()
        
        if customer.status != 'approved':
            username = f"{customer.first_name.lower()}{customer.id}"
            password = generate_random_password()
            
            user = User.objects.create_user(
                username=username,
                password=password,
                email=customer.email,
                first_name=customer.first_name,
                last_name=customer.surname
            )
            
            customer.user = user
            customer.status = 'approved'
            customer.approved_by = request.user
            customer.save()
            
            try:
                send_mail(
                    'Your Loan Account Has Been Approved',
                    f'''Dear {customer.first_name} {customer.surname},

Your account has been approved by the admin.

Your login credentials:
Username: {username}
Password: {password}

Please login at your frontend application.

Best regards,
Loan Management System Team''',
                    settings.DEFAULT_FROM_EMAIL,
                    [customer.email],
                    fail_silently=False,
                )
            except Exception as e:
                pass
            
            return Response({
                'message': f'Customer approved! Login credentials sent to {customer.email}'
            })
        
        return Response({'message': 'Customer already approved'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        try:
            customer = CustomerProfile.objects.get(user=request.user)
            serializer = self.get_serializer(customer)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)

class LoanTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAuthenticated]

class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return LoanApplication.objects.all()
        else:
            customer = CustomerProfile.objects.get(user=user)
            return LoanApplication.objects.filter(customer=customer)
    
    def perform_create(self, serializer):
        customer = CustomerProfile.objects.get(user=self.request.user)
        serializer.save(customer=customer)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        application = self.get_object()
        
        if application.status == 'pending':
            approval_score = application.calculate_approval_score()
            if application.should_approve():
                application.status = 'approved'
                application.approved_amount = application.requested_amount
                application.reviewed_by = request.user
                application.save()
                
                return Response({
                    'message': f'Loan approved! Score: {approval_score:.2f}'
                })
            else:
                return Response({
                    'error': f'Loan cannot be approved. Score: {approval_score:.2f} (below threshold)'
                }, status=400)
        
        return Response({'message': 'Application already processed'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        application = self.get_object()
        
        if application.status == 'pending':
            application.status = 'rejected'
            application.reviewed_by = request.user
            application.save()
            
            return Response({'message': 'Loan application rejected'})
        
        return Response({'message': 'Application already processed'})

class AuthViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                customer = CustomerProfile.objects.get(user=user)
                if customer.status == 'approved':
                    login(request, user)
                    return Response({
                        'message': 'Login successful',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'is_admin': user.is_staff
                        }
                    })
                else:
                    return Response({'error': 'Your account is not approved yet.'}, status=400)
            except CustomerProfile.DoesNotExist:
                if user.is_staff:
                    login(request, user)
                    return Response({
                        'message': 'Admin login successful',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'is_admin': True
                        }
                    })
                else:
                    return Response({'error': 'Invalid customer account.'}, status=400)
        else:
            return Response({'error': 'Invalid username or password.'}, status=400)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        from django.contrib.auth import logout
        logout(request)
        return Response({'message': 'Logout successful'})