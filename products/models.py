from django.db import models
from base.models import BaseModel
from django.utils.text import slugify

class Category(BaseModel):
  category_name = models.CharField(max_length=100)
  slug = models.SlugField(unique=True, null=True, blank=True)
  category_image = models.ImageField(upload_to = "categories")

  def save(self, *args, **kwargs):
    if not self.slug:
      self.slug = slugify(self.category_name)
    super(Category, self).save(*args, **kwargs)

  def __str__(self)-> str:
    return self.category_name

class colorVariant(BaseModel):
  color_name = models.CharField(max_length=100)
  price = models.DecimalField(default=0, max_digits=10, decimal_places=2)

  def __str__ (self)-> str:
    return self.color_name

class sizeVariant(BaseModel):
  size_name = models.CharField(max_length=100)
  price = models.DecimalField(default=0, max_digits=10, decimal_places=2)

  def __str__ (self)-> str:
      return self.size_name

class Product(BaseModel):
  product_name = models.CharField(max_length=100)
  category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
  slug = models.SlugField(unique=True, null=True, blank=True)
  price = models.DecimalField(max_digits=10, decimal_places=2)
  product_description = models.TextField()
  color_variant = models.ManyToManyField(colorVariant, blank=True)
  size_variant = models.ManyToManyField(sizeVariant, blank=True)

  def save(self, *args, **kwargs):
    if not self.slug:
      self.slug = slugify(self.product_name)
    super(Product, self).save(*args, **kwargs)

  def __str__(self)-> str:
    return self.product_name

  def get_product_price_by_size(self, size):
    if isinstance(size, sizeVariant):
      size_obj = size
    else:
      size_obj = self.size_variant.get(size_name=size)
    return self.price + size_obj.price

class ProductImage(BaseModel):
  product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_images")
  image = models.ImageField(upload_to="media/products")


class Payment(BaseModel):
  class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'

  razorpay_order_id = models.CharField(max_length=100, unique=True)
  razorpay_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
  amount = models.DecimalField(max_digits=12, decimal_places=2)
  currency = models.CharField(max_length=3, default='USD')
  status = models.CharField(
    max_length=10,
    choices=Status.choices,
    default=Status.PENDING,
  )
  cart_snapshot = models.JSONField(default=list)

  def __str__(self):
    return f'{self.razorpay_order_id} ({self.status})'
