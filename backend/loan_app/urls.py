from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, LoanTypeViewSet, LoanApplicationViewSet, AuthViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'loan-types', LoanTypeViewSet)
router.register(r'loan-applications', LoanApplicationViewSet)
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]