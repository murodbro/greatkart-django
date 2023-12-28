from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import Http404

from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from orders.models import OrderProduct

from .forms import ReviewForm
from .models import Product, ReviewRating



def store_view(request, category_slug=None):
    products = Product.objects.filter(is_available=True)

    if category_slug is not None:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    paginator = Paginator(products.order_by("-id"), 6)

    context = {
        "products": paginator.get_page(request.GET.get("page")),
        "product_count": products.count()
    }
    return render(request, "store/store.html", context)


def product_detail_view(request, category_slug, product_slug):
    try:
        product = Product.objects.get(
            category__slug=category_slug,
            slug=product_slug
        )
    except Product.DoesNotExist as e:
        raise Http404()
    
    if request.user.is_authenticated:
        orderproduct = OrderProduct.objects.filter(product_id=product.id).exists()
    
    else:
        orderproduct = None

    reviews = ReviewRating.objects.filter(product_id=product.id, status=True)
    
    context = {
        'product': product,
        'reviews':reviews,
        'orderproduct': orderproduct,
        "out_of_stock": product.stock == 0,
        'in_cart': CartItem.objects.filter(
            cart__cart_id=_cart_id(request),
            product=product,
        ).exists()
    }
    return render(request, 'store/product_detail.html', context)


def search_view(request):
    search_term = request.GET.get("keyword")
    if not search_term:
        return redirect("store")

    products = Product.objects.filter(
        Q(description__icontains=search_term)
        | Q(product_name__icontains=search_term)
    ).order_by('-created_date')

    context = {
        "products": products,
        "product_count": products.count()
    }
    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get("HTTP_REFERER")
    if request.method == "POST":
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, "Your review has been updated !")
            return redirect(url)

        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data["subject"]
                data.rating = form.cleaned_data["rating"]
                data.review = form.cleaned_data["review"]
                data.ip = request.META.get("REMOTE_ADDR")
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, "Your review has been updated !")
                return redirect(url)


