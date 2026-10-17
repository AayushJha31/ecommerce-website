from django.urls import path
from products.views import (
  add_to_cart,
  cart,
  get_product,
  payment_success,
  start_checkout,
  update_cart,
  verify_payment,
)

urlpatterns =[
  path('cart/', cart, name='cart'),
  path('cart/update/', update_cart, name='update_cart'),
  path('checkout/', start_checkout, name='start_checkout'),
  path('checkout/verify/', verify_payment, name='verify_payment'),
  path('checkout/success/', payment_success, name='payment_success'),
  path('<slug:slug>/add-to-cart/', add_to_cart, name='add_to_cart'),
  path('<slug>/', get_product, name='get_product')
]