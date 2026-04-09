from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from loanApp import views
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib.auth import logout
from django.shortcuts import redirect

# Custom function to ensure session is destroyed and user is sent home
def trigger_logout(request):
    logout(request) 
    # Redirecting to the 'home' name defined in urlpatterns below
    return redirect('home') 

urlpatterns = [
    # 1. Standardizing the logout path to match your sidebar link
    path('account/logout/', trigger_logout, name='logout'), 
    
    # 2. Admin Panel
    path('admin/', admin.site.urls),
    
    # 3. Main Home Page (Landing Page)
    path('', views.home, name='home'),
    
    # 4. Included App URLs
    path('account/', include('loginApp.urls')),
    path('loan/', include('loanApp.urls')),
    path('manager/', include('managerApp.urls')),
]

# Static and Media file configuration
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom 404 Handler
handler404 = 'loanApp.views.error_404_view'