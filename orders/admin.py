from django.contrib import admin
from .models import OrderProduct, Payment, Order


admin.site.register(Payment)
admin.site.register(Order)
admin.site.register(OrderProduct)