import datetime

from django.http import HttpResponse
from django.shortcuts import redirect, render

from carts.models import CartItem
from .models import Order
from .forms import OrderForm



def payments(request):
    return render(request, "orders/payments.html")


def place_order(request, total=0, quantity=0,):
    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items.exists():
        return redirect('store')
    
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2 * total)/100
    grand_total = tax + total

    if request.method != "POST":
        return redirect("checkout")

    form = OrderForm(request.POST)
    if not form.is_valid():
        return redirect("checkout")

    order = Order(
        **form.cleaned_data,
        user = request.user,
        order_total = grand_total,
        tax = tax,
        ip = request.META.get("REMOTE_ADDR"),
    )
    order.save()

    order.order_number = "{}{}".format(datetime.date.today().strftime("%Y%m%d"), order.ip,)
    order.save()

    Order.refresh_from_db(order)

    context = {
        "order": order,
        "cart_item": cart_item,
        "total": total,
        "tax": tax,
        "grand_total": grand_total
    }
    return render(request, "orders/payments.html", context)


            

