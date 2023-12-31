from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import Http404

from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id

from .models import Product



def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True)

    if category_slug is not None:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    products = products.order_by("-id")
    paginator = Paginator(products, 6)
    paged_products = paginator.get_page(request.GET.get("page"))
    product_count = products.count()

    context = {
        "products": paged_products,
        "product_count": product_count
    }
    return render(request, "store/store.html", context)


def product_detail(request, category_slug, product_slug):
    try:
        product = Product.objects.get(
            category__slug=category_slug,
            slug=product_slug
        )
    except Product.DoesNotExist as e:
        raise Http404()
    
    context = {
        'product': product,
        "out_of_stock": product.stock == 0,
        'in_cart': CartItem.objects.filter(
            cart__cart_id=_cart_id(request),
            product=product,
        ).exists()
    }
    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        "products": products,
        "product_count": product_count
    }
    return render(request, 'store/store.html', context)