import copy
import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from products.models import Payment, Product

logger = logging.getLogger(__name__)


def _cart_key(product_id, size_id=None):
  return f'{product_id}:{size_id or 0}'


def _get_cart(request):
  return request.session.get('cart', {})


def _get_cart_summary(request):
  cart_items = _get_cart(request)
  product_ids = {item.get('product_id') for item in cart_items.values()}
  products = Product.objects.filter(pk__in=product_ids).prefetch_related(
    'product_images', 'size_variant'
  )
  products_by_id = {str(product.pk): product for product in products}
  items = []
  subtotal = Decimal('0.00')

  for key, cart_item in cart_items.items():
    product = products_by_id.get(str(cart_item.get('product_id')))
    if not product:
      continue
    size_id = cart_item.get('size_id')
    size = next(
      (variant for variant in product.size_variant.all() if str(variant.pk) == size_id),
      None,
    )
    unit_price = product.price
    if size:
      unit_price = product.get_product_price_by_size(size)
    quantity = cart_item.get('quantity', 1)
    line_total = unit_price * quantity
    subtotal += line_total
    items.append({
      'key': key,
      'product': product,
      'size': size,
      'quantity': quantity,
      'unit_price': unit_price,
      'line_total': line_total,
    })

  return items, subtotal


def _create_razorpay_order(amount):
  credentials = f'{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}'
  authorization = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
  payload = json.dumps({
    'amount': amount,
    'currency': 'USD',
    'receipt': f'cart-{uuid4().hex[:20]}',
  }).encode('utf-8')
  request = Request(
    'https://api.razorpay.com/v1/orders',
    data=payload,
    headers={
      'Authorization': f'Basic {authorization}',
      'Content-Type': 'application/json',
    },
    method='POST',
  )

  try:
    with urlopen(request, timeout=15) as response:
      order = json.loads(response.read().decode('utf-8'))
  except HTTPError as error:
    logger.error('Razorpay order creation failed with HTTP status %s.', error.code)
    raise RuntimeError('The payment provider could not create an order.') from error
  except (URLError, TimeoutError, json.JSONDecodeError) as error:
    logger.exception('Could not create a Razorpay order.')
    raise RuntimeError('The payment provider could not be reached.') from error

  if not isinstance(order, dict) or not order.get('id'):
    logger.error('Razorpay returned an invalid order response.')
    raise RuntimeError('The payment provider returned an invalid order.')
  return order


def get_product(request, slug):
  product = get_object_or_404(Product, slug=slug)
  context = {'product': product}
  selected_size = request.GET.get('size')
  if selected_size:
    size = product.size_variant.filter(size_name=selected_size).first()
    if size:
      context['selected_size'] = size.size_name
      context['updated_price'] = product.get_product_price_by_size(size)
      context['selected_size_id'] = size.pk

  return render(request, 'products/products.html', context=context)


def add_to_cart(request, slug):
  if request.method != 'POST':
    return redirect('get_product', slug=slug)

  product = get_object_or_404(Product, slug=slug)
  try:
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
      raise ValueError
  except (TypeError, ValueError):
    messages.error(request, 'Please enter a valid quantity.')
    return redirect('get_product', slug=slug)

  size_id = request.POST.get('size')
  size = None
  if product.size_variant.exists():
    if not size_id:
      messages.error(request, 'Please select a size.')
      return redirect('get_product', slug=slug)
    size = product.size_variant.filter(pk=size_id).first()
    if not size:
      messages.error(request, 'Please select a valid size.')
      return redirect('get_product', slug=slug)

  cart = _get_cart(request).copy()
  key = _cart_key(product.pk, size.pk if size else None)
  existing_item = cart.get(key, {})
  cart[key] = {
    'product_id': str(product.pk),
    'size_id': str(size.pk) if size else None,
    'quantity': existing_item.get('quantity', 0) + quantity,
  }
  request.session['cart'] = cart
  request.session['cart_count'] = sum(item['quantity'] for item in cart.values())
  messages.success(request, f'{product.product_name} added to your cart.')
  return redirect('cart')


def cart(request):
  items, subtotal = _get_cart_summary(request)

  return render(request, 'products/cart.html', {
    'cart_items': items,
    'subtotal': subtotal,
    'cart_count': sum(item['quantity'] for item in items),
    'payment_configured': bool(
      settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET
    ),
  })


def update_cart(request):
  if request.method != 'POST':
    return redirect('cart')

  cart_items = _get_cart(request).copy()
  key = request.POST.get('item_key', '')
  if key not in cart_items:
    messages.error(request, 'That item is no longer in your cart.')
    return redirect('cart')

  action = request.POST.get('action')
  if action == 'remove':
    del cart_items[key]
    messages.success(request, 'Item removed from your cart.')
  else:
    try:
      quantity = int(request.POST.get('quantity', ''))
      if quantity < 1:
        raise ValueError
    except (TypeError, ValueError):
      messages.error(request, 'Please enter a valid quantity.')
      return redirect('cart')
    cart_items[key]['quantity'] = quantity
    messages.success(request, 'Cart updated.')

  request.session['cart'] = cart_items
  request.session['cart_count'] = sum(
    item.get('quantity', 0) for item in cart_items.values()
  )
  return redirect('cart')


@require_POST
def start_checkout(request):
  if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
    messages.error(request, 'Online payment is not configured yet.')
    return redirect('cart')

  items, subtotal = _get_cart_summary(request)
  if not items or subtotal <= 0:
    messages.error(request, 'Your cart is empty.')
    return redirect('cart')

  amount = int((subtotal * 100).to_integral_value())
  try:
    order = _create_razorpay_order(amount)
  except RuntimeError as error:
    messages.error(request, str(error))
    return redirect('cart')

  request.session['pending_payment'] = {
    'order_id': order['id'],
    'amount': amount,
    'cart': copy.deepcopy(_get_cart(request)),
  }
  Payment.objects.create(
    razorpay_order_id=order['id'],
    amount=subtotal,
    currency='USD',
    cart_snapshot=[
      {
        'product_id': str(item['product'].pk),
        'product_name': item['product'].product_name,
        'size': item['size'].size_name if item['size'] else None,
        'quantity': item['quantity'],
        'unit_price': str(item['unit_price']),
        'line_total': str(item['line_total']),
      }
      for item in items
    ],
  )
  return render(request, 'products/checkout.html', {
    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    'razorpay_order_id': order['id'],
    'amount': amount,
    'total': subtotal,
  })


@require_POST
def verify_payment(request):
  pending_payment = request.session.get('pending_payment')
  order_id = request.POST.get('razorpay_order_id', '')
  payment_id = request.POST.get('razorpay_payment_id', '')
  signature = request.POST.get('razorpay_signature', '')

  if (
    not pending_payment
    or not order_id
    or not payment_id
    or not signature
    or not hmac.compare_digest(order_id, pending_payment['order_id'])
  ):
    return JsonResponse({'error': 'Payment details could not be verified.'}, status=400)

  message = f'{order_id}|{payment_id}'.encode('utf-8')
  expected_signature = hmac.new(
    settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
    message,
    hashlib.sha256,
  ).hexdigest()
  if not hmac.compare_digest(expected_signature, signature):
    return JsonResponse({'error': 'Payment signature is invalid.'}, status=400)

  payment = Payment.objects.filter(
    razorpay_order_id=order_id,
    status=Payment.Status.PENDING,
  ).first()
  if not payment or int(payment.amount * 100) != pending_payment['amount']:
    return JsonResponse({'error': 'Payment order could not be verified.'}, status=400)

  payment.razorpay_payment_id = payment_id
  payment.status = Payment.Status.PAID
  payment.save(update_fields=['razorpay_payment_id', 'status', 'updated_at'])

  if _get_cart(request) == pending_payment['cart']:
    request.session['cart'] = {}
    request.session['cart_count'] = 0
  request.session.pop('pending_payment', None)
  request.session['completed_payment'] = {
    'payment_id': payment_id,
    'order_id': order_id,
    'amount': pending_payment['amount'],
  }
  return JsonResponse({'redirect_url': reverse('payment_success')})


def payment_success(request):
  payment = request.session.pop('completed_payment', None)
  if not payment:
    return redirect('cart')
  return render(request, 'products/payment_success.html', {'payment': payment})