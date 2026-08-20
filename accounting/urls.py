# config/urls.py (or your main project urls.py)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Super Admin user creation route
    path('', include('account.urls')),
    path('', include('core.urls')),
]