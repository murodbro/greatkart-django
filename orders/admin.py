from django.contrib import admin
from .models import OrderProduct, Order



class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ["quantity", "product_price", "product", "ordered", "variations"]
    extra  = 0



class OrderAdmin(admin.ModelAdmin):
    list_display = ["first_name", "email", "order_total", "is_ordered", "created_at"]
    list_filter = ["status", "is_ordered"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    list_per_page = 20
    inlines = [OrderProductInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)