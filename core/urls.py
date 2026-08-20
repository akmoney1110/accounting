from django.urls import path
from . import views

urlpatterns = [
    # path(route, view_function, name_for_reverse_lookup)
    path('', views.home_view, name='home'),
]