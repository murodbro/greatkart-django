import datetime
import json
import traceback
import stripe

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from carts.models import CartItem
from store.models import Product, Variation
from .models import Order, OrderProduct
from .forms import OrderForm


stripe.api_key = settings.STRIPE_SECRET_KEY

def send_order_recieving_email(recievers, order):
    mail_subject = "Thank you for your order"
    message = render_to_string('orders/order_recieved_email.html', {
        'order': order,
    })
    send_email = EmailMessage(mail_subject, message, to=[recievers])
    send_email.send()


def get_success(request):
    session_id = request.GET.get('session_id', None)
    if not session_id:
        return render(request, "orders/success.html", {"ok": False, "message": "Invalid checkout session"})
    

    session = stripe.checkout.Session.retrieve(session_id)
    order_id = session.get("metadata", {}).get("order_id")

    order = Order.objects.filter(order_number=order_id, is_ordered=False).first()
    if not order:
        return render(request, "orders/success.html", {"ok": False, "message": "Order doesn't exist"})

    order.is_ordered = True
    order.status = order.StatusCategory.COMPLETED
    order.save()

    cart_items = CartItem.objects.filter(user=request.user)

    for cart_item in cart_items:
        product = Product.objects.get(id=cart_item.product_id)
        product.stock -= cart_item.quantity
        product.save()

    CartItem.objects.filter(user=request.user).delete()

    send_order_recieving_email(order.email, order)

    try:
        order = Order.objects.get(order_number=order_id, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

    except (OrderProduct.DoesNotExist, Order.DoesNotExist):
        return redirect("home")
    
    subtotal = 0
    for ordered_product in ordered_products:
        subtotal += ordered_product.product_price * ordered_product.quantity

    context = {
        "order": order,
        "ordered_products": ordered_products,
        "order_number": order_id,
        "subtotal": subtotal,
    }

    return render(request, "orders/success.html", context)


def get_cancel(request):
    session_id = request.GET.get('session_id', None)
    if not session_id:
        return render(request, "orders/success.html", {"ok": False, "message": "Invalid checkout session"})
    

    session = stripe.checkout.Session.retrieve(session_id)
    order_id = session.get("metadata", {}).get("order_id")

    order = Order.objects.filter(order_number=order_id, is_ordered=False).first()
    if not order:
        return render(request, "orders/success.html", {"ok": False, "message": "Order doesn't exist"})

    order.is_ordered = False
    order.status = order.StatusCategory.CANCELLED
    order.save()

    return render(request, "orders/cancelled.html", {"ok": False, "message": "transaction was cancelled!"})


def create_checkout_session(request):
    if request.method == "GET":
        return JsonResponse({"ok": False, "message": "Couldn't get checkout url"})
    
    data = json.loads(request.body)
    order_id = data.get("order_id")
    
    order = Order.objects.filter(order_number=order_id).first()
    if not order:
        return JsonResponse({"ok": False, "message": "Order doesn't exist"})

    domain_url = 'http://localhost:8000/orders/'

    cart_items = CartItem.objects.filter(user=request.user)
    line_items = []

    for cart_item in cart_items:
        grand_total = int(((cart_item.product.price * 2) / 100 + int(cart_item.product.price))*100)
        line_item = {
            'quantity': cart_item.quantity,
            'price_data': {
                'currency': 'usd',
                'unit_amount': int(grand_total),
                'product_data': {
                    'name': cart_item.product.product_name,
                },
            },
        }
        line_items.append(line_item)

        order_product = OrderProduct(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            product_price =(grand_total/100),
            ordered = True
        )
        order_product.save()

        product_variation = cart_item.variations.all()
        order_product = OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variation)
        order_product.save()

        
    try:
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + 'cancelled',
            payment_method_types=['card'],
            mode='payment',
            line_items=line_items,
            metadata={"order_id": order.order_number}
        )
        return JsonResponse({"ok": True, 'session_id': checkout_session['id']})
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return JsonResponse({"ok": False, 'message': "Internal server error"})


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

    order.order_number = "{}{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M"), order.ip,)
    order.save()

    Order.refresh_from_db(order)

    context = {
        "order": order,
        "cart_items": cart_items,
        "total": total,
        "tax": tax,
        "grand_total": grand_total
    }
    return render(request, "orders/payments.html", context)


            

