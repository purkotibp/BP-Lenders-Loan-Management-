from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from loanApp import views
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib.auth import logout, views as auth_views # Import this,
from django.shortcuts import redirect

# Custom function to ensure session is destroyed
def trigger_logout(request):
    logout(request) # This flushes the session data completely
    return redirect('/admin/login/') # Redirects to the page you asked about

urlpatterns = [
# Put this at the very top
    path('admin/logout/', trigger_logout, name='logout'),
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('account/', include('loginApp.urls')),
    path('loan/', include('loanApp.urls')),
    path('manager/', include('managerApp.urls')),
    # Add this line ABOVE admin.site.urls to override the logout behavior
    

]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = 'loanApp.views.error_404_view'

