# config/urls.py (or your main project urls.py)
from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include



urlpatterns = [
    path('admin/', admin.site.urls),  # Super Admin user creation route
    path('', include('account.urls')),
    path('', include('core.urls')),
    path("eatery/", include("eatery.urls")),
]

handler404 = 'account.views.custom_page_not_found_view'
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
