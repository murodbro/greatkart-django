from email.policy import default
from tabnanny import verbose
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Count

from accounts.models import Account
from category.models import Category



class Product(models.Model):
    product_name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.product_name
    
    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])
    
    def average_rating(self):
        review = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg("rating"))
        avg = 0
        if review["average"] is not None:
            avg = float(review["average"])
        return avg

    def count_review(self):
        review = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Count("id"))
        count = 0
        if review["average"] is not None:
            count = int(review["average"])
        return count
    

class VariationManager(models.Manager):
    def colors(self):
        return super(VariationManager, self).filter(variation_category='color', is_active=True)

    def sizes(self):
        return super(VariationManager, self).filter(variation_category='size', is_active=True)
    

class Variation(models.Model):
    class VariationCategory(models.TextChoices):
        COLOR = ("color", _("Rang"))
        SIZE =  ("size", _("O'lcham"))

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=255, choices=VariationCategory.choices)
    variation_value = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    objects = VariationManager()

    def __str__(self) -> str:
        return self.variation_value
    

class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=50, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.subject
    

class ProductGallery(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="store/products", max_length=255)

    def __str__(self) -> str:
        return self.product.product_name
    
    class Meta:
        verbose_name = "productgallery"
        verbose_name_plural = "product gallery"