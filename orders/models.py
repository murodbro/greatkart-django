from django.utils.translation import gettext_lazy as _
from django.db import models

from accounts.models import Account
from store.models import Product, Variation

    
class Order(models.Model):
    class StatusCategory(models.TextChoices):
        NEW = ("New", _("Yangi"))
        ACCEPTED = ("Accepted", _("Qabul qilindi"))
        COMPLETED = ("Completed", _("Yakunlandi"))
        CANCELLED = ("Cancelled", _("Inkor qilindi"))
        

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=50)
    address_line_1 = models.CharField(max_length=50)
    address_line_2 = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    order_note = models.CharField(max_length=120)
    order_total = models.FloatField()
    tax = models.FloatField()
    status = models.CharField(max_length=10, choices=StatusCategory.choices, default=StatusCategory.NEW)
    ip = models.CharField(max_length=20, blank=True)
    is_ordered = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def full_address(self):
        return f"{self.address_line_1} {self.address_line_2}"

    def __str__(self) -> str:
        return self.first_name


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.product.product_name


