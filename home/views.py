from django.shortcuts import render
from products.models import Product

def index(request):
  products = Product.objects.all()
  return render(request, 'home/index.html', {'products': products})