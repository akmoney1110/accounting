from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse

# Simple Function-Based View
def home_view(request):
    return render(request, "core/home.html")