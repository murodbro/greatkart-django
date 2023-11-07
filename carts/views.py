from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from store.models import Product, Variation
from .models import Cart, CartItem


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    product_variation = []
    if request.method == "POST":
        for item in request.POST:
            key = item
            value = request.POST[key]

            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass

    if not request.user.is_authenticated:

        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))

        cart.save()

        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()

        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, cart=cart)
            ex_cart_val = []
            id = []

            for item in cart_item:
                existing_variations = item.variations.all()
                ex_cart_val.append(list(existing_variations))
                id.append(item.id)

            if product_variation in ex_cart_val:
                index = ex_cart_val.index(product_variation)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()

            else:
                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
            item.save()

        else:
            cart_item = CartItem.objects.create(
                product=product,
                cart=cart,
                quantity = 1
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation) 
            cart_item.save()

        return redirect('cart')

    is_cart_item_exists = CartItem.objects.filter(product=product, user=request.user).exists()

    if is_cart_item_exists:
        cart_item = CartItem.objects.filter(product=product, user=request.user)
        ex_cart_val = []
        id = []

        for item in cart_item:
            existing_variations = item.variations.all()
            ex_cart_val.append(list(existing_variations))
            id.append(item.id)

        if product_variation in ex_cart_val:
            index = ex_cart_val.index(product_variation)
            item_id = id[index]
            item = CartItem.objects.get(product=product, id=item_id)
            item.quantity += 1
            item.save()

        else:
            item = CartItem.objects.create(product=product, quantity=1, user=request.user)
            if len(product_variation) > 0:
                item.variations.clear()
                item.variations.add(*product_variation)
        item.save()

    else:
        cart_item = CartItem.objects.create(
            product=product,
            user=request.user,
            quantity = 1
        )
        if len(product_variation) > 0:
            cart_item.variations.clear()
            cart_item.variations.add(*product_variation)  
        cart_item.save()

    return redirect('cart')        
        

def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if not request.user.is_authenticated:
            cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(cart=cart, product=product, id=cart_item_id)
        
        cart_item = CartItem.objects.get(user=request.user, product=product, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    
    return redirect('cart')


def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)

    if not request.user.is_authenticated:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(cart=cart, product=product, id=cart_item_id)
        cart_item.delete()

    cart_item = CartItem.objects.get(user=request.user, product=product, id=cart_item_id)
    cart_item.delete()

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        grand_total = 0
        tax = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)

        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        grand_total = tax + total

    except Cart.DoesNotExist:
        pass

    context = {
        "total": total,
        "cart_items": cart_items,
        "quantity": quantity,
        "grand_total": grand_total,
        "tax": tax
    }

    return render(request, 'store/cart.html', context)


@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    try:
        grand_total = 0
        tax = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)

        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        grand_total = tax + total

    except Cart.DoesNotExist:
        pass

    context = {
        "total": total,
        "cart_items": cart_items,
        "quantity": quantity,
        "grand_total": grand_total,
        "tax": tax
    }

    return render(request, 'store/checkout.html', context)