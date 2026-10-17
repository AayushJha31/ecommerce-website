import hashlib
import hmac
from unittest.mock import patch

from django.test import TestCase, override_settings

from products.models import Category, Payment, Product, sizeVariant


class ProductModelTests(TestCase):
    def test_get_product_price_by_size_uses_product_size_variant(self):
        category = Category.objects.create(category_name='Electronics')
        product = Product.objects.create(
            product_name='Laptop',
            category=category,
            price=1000,
            product_description='A great laptop.',
        )
        size = sizeVariant.objects.create(size_name='Large', price=120)
        product.size_variant.add(size)

        self.assertEqual(product.get_product_price_by_size('Large'), 1120)
        self.assertEqual(product.get_product_price_by_size(size), 1120)

    def test_slug_only_generated_when_missing(self):
        category = Category.objects.create(category_name='Home Essentials', slug='custom-slug')
        self.assertEqual(category.slug, 'custom-slug')

        category.category_name = 'Updated home essentials'
        category.save()
        self.assertEqual(category.slug, 'custom-slug')

        product = Product.objects.create(
            product_name='Office Chair',
            category=category,
            price=150,
            product_description='Comfortable seating.',
        )
        self.assertEqual(product.slug, 'office-chair')


class CartViewTests(TestCase):
    def setUp(self):
        category = Category.objects.create(category_name='Electronics')
        self.product = Product.objects.create(
            product_name='Laptop',
            category=category,
            price=1000,
            product_description='A great laptop.',
        )
        self.size = sizeVariant.objects.create(size_name='Large', price=120)
        self.product.size_variant.add(self.size)

    def test_add_to_cart_stores_selected_size_and_quantity(self):
        response = self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '2', 'size': str(self.size.pk)},
        )

        self.assertRedirects(response, '/products/cart/')
        self.assertEqual(
            self.client.session['cart'],
            {
                f'{self.product.pk}:{self.size.pk}': {
                    'product_id': str(self.product.pk),
                    'size_id': str(self.size.pk),
                    'quantity': 2,
                }
            },
        )
        self.assertEqual(self.client.session['cart_count'], 2)

    def test_cart_shows_variant_price_and_subtotal(self):
        self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '2', 'size': str(self.size.pk)},
        )

        response = self.client.get('/products/cart/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Laptop')
        self.assertContains(response, '1120')
        self.assertContains(response, '2240')

    def test_cart_can_update_and_remove_item(self):
        self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '1', 'size': str(self.size.pk)},
        )
        item_key = f'{self.product.pk}:{self.size.pk}'

        response = self.client.post(
            '/products/cart/update/',
            {'item_key': item_key, 'quantity': '3'},
        )
        self.assertRedirects(response, '/products/cart/')
        self.assertEqual(self.client.session['cart'][item_key]['quantity'], 3)
        self.assertEqual(self.client.session['cart_count'], 3)

        response = self.client.post(
            '/products/cart/update/',
            {'item_key': item_key, 'action': 'remove'},
        )
        self.assertRedirects(response, '/products/cart/')
        self.assertEqual(self.client.session['cart'], {})
        self.assertEqual(self.client.session['cart_count'], 0)

    def test_size_is_required_for_products_with_size_variants(self):
        response = self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '1'},
        )

        self.assertRedirects(response, f'/products/{self.product.slug}/')
        self.assertEqual(self.client.session.get('cart', {}), {})


class RazorpayCheckoutTests(CartViewTests):
    @override_settings(RAZORPAY_KEY_ID='rzp_test_key', RAZORPAY_KEY_SECRET='test_secret')
    @patch('products.views._create_razorpay_order', return_value={'id': 'order_test_123'})
    def test_checkout_creates_payment_record_and_renders_gateway(self, create_order):
        self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '2', 'size': str(self.size.pk)},
        )

        response = self.client.post('/products/checkout/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rzp_test_key')
        self.assertContains(response, 'order_test_123')
        create_order.assert_called_once_with(224000)
        payment = Payment.objects.get(razorpay_order_id='order_test_123')
        self.assertEqual(payment.amount, 2240)
        self.assertEqual(payment.currency, 'USD')
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.cart_snapshot[0]['quantity'], 2)

    @override_settings(RAZORPAY_KEY_ID='rzp_test_key', RAZORPAY_KEY_SECRET='test_secret')
    @patch('products.views._create_razorpay_order', return_value={'id': 'order_test_123'})
    def test_valid_payment_signature_marks_payment_paid_and_clears_cart(self, _create_order):
        self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '2', 'size': str(self.size.pk)},
        )
        self.client.post('/products/checkout/')
        payment_id = 'pay_test_123'
        signature = hmac.new(
            b'test_secret',
            b'order_test_123|pay_test_123',
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post('/products/checkout/verify/', {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect_url'], '/products/checkout/success/')
        payment = Payment.objects.get(razorpay_order_id='order_test_123')
        self.assertEqual(payment.razorpay_payment_id, payment_id)
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(self.client.session['cart'], {})
        self.assertEqual(self.client.session['cart_count'], 0)

    @override_settings(RAZORPAY_KEY_ID='rzp_test_key', RAZORPAY_KEY_SECRET='test_secret')
    @patch('products.views._create_razorpay_order', return_value={'id': 'order_test_123'})
    def test_invalid_signature_does_not_mark_payment_paid(self, _create_order):
        self.client.post(
            f'/products/{self.product.slug}/add-to-cart/',
            {'quantity': '1', 'size': str(self.size.pk)},
        )
        self.client.post('/products/checkout/')

        response = self.client.post('/products/checkout/verify/', {
            'razorpay_order_id': 'order_test_123',
            'razorpay_payment_id': 'pay_test_123',
            'razorpay_signature': 'invalid',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Payment.objects.get(razorpay_order_id='order_test_123').status,
            Payment.Status.PENDING,
        )
        self.assertTrue(self.client.session['cart'])

    def test_checkout_requires_provider_credentials(self):
        response = self.client.post('/products/checkout/')

        self.assertRedirects(response, '/products/cart/')
        self.assertFalse(Payment.objects.exists())
