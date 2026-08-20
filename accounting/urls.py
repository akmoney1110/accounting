# config/urls.py (or your main project urls.py)
from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Super Admin user creation route
    path('', include('account.urls')),
    path('', include('core.urls')),
]
