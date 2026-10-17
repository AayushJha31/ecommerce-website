from django.contrib import admin
from .models import *

admin.site.register(Category)

class ProductImageAdmin(admin.StackedInline):
  model = ProductImage

class ProductAdmin(admin.ModelAdmin):
  list_display = ('product_name', 'category', 'price')
  inlines = [ProductImageAdmin]

admin.site.register(Product, ProductAdmin)

admin.site.register(ProductImage)

@admin.register(colorVariant)
class colorVariantAdmin(admin.ModelAdmin):
  list_display = ('color_name', 'price')
  model = colorVariant

@admin.register(sizeVariant) 
class sizeVariantAdmin(admin.ModelAdmin):
  list_display = ('size_name', 'price')
  model = sizeVariant
