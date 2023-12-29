from pickletools import read_uint1
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site as get_host_site
from django.contrib.auth.tokens import default_token_generator

from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes

from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect, render
import accounts

from carts.models import Cart, CartItem
from carts.views import _cart_id
from orders.models import Order, OrderProduct

from.forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile


@transaction.atomic()
def register_account(data: dict) -> Account:
    password = data.pop("password")
    username = data['email'].split('@')[0]

    user = Account(
        **data,
        username=username
    )
    user.set_password(password)
    user.save()
    return user


def send_account_verification_email(user: Account, host_site: str, receivers):
    mail_subject = "Please activate your account!"
    message = render_to_string('accounts/account_verification_email.html', {
        'user': user,
        'domain': host_site,
        'uid': urlsafe_base64_encode(force_bytes(user.id)),
        'token': default_token_generator.make_token(user),
    })
    send_email = EmailMessage(mail_subject, message, to=receivers)
    send_email.send()


def register(request):
    form = RegistrationForm()

    if request.method != "POST":
        return render(request, 'accounts/register.html', {"form": form})

    form = RegistrationForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'An error occurred during registration.')
        return redirect('register')

    user = register_account(data=form.cleaned_data)
    email = form.cleaned_data['email']

    send_account_verification_email(
        user=user,
        host_site=get_host_site(request),
        receivers=[email]
    )

    messages.success(
        request,
        'Thank you for registering with us. \
        We have s sent email verification to your email\
         address. Please verify it.'
    )
    return redirect(f'/accounts/login/?command=verification&email={email}')


def login(request):
    if request.method != "POST":
        return render(request, 'accounts/login.html')

    # user = auth.authenticate(**request.POST)
    user = auth.authenticate(email=request.POST['email'], password=request.POST['password'])


    if not user:
        messages.error(request, "Invalid login credentials")
        return redirect("login")

    cart = Cart.objects.filter(cart_id=_cart_id(request)).first()

    if cart:
        cart_items = CartItem.objects.filter(cart=cart)
        if cart_items.exists():

            product_variation = []
            for item in cart_items:
                variations = item.variations.all()
                product_variation.append(list(variations))

            cart_items = CartItem.objects.filter(user=user)
            exist_variations = []
            id = []

            for item in cart_items:
                existing_variations = item.variations.all()
                exist_variations.append(list(existing_variations))
                id.append(item.id)
            
            for i in product_variation:
                if i in exist_variations:
                    index = exist_variations.index(i)
                    item_id = id[index]
                    item = CartItem.objects.get(id=item_id)
                    item.quantity += 1
                    item.user = user
                    item.save()

                else:
                    cart_items = CartItem.objects.filter(cart=cart)
                    for item in cart_items:
                        item.user = user
                        item.save()

    auth.login(request, user)
    messages.success(request, 'You are now logged in!')
    url = request.META.get('HTTP_REFERER')

    parts = url.split("?")[-1].split("&")
    for part in parts:
        if "next" in part:
            return redirect(part.split("=")[-1])
    
    return redirect('dashboard')
        



def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(Account.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user is None and not default_token_generator.check_token(user, token):
        messages.error(request, 'Invalid activation link!')
        return redirect('register')
    
    user.is_active = True
    user.save()
    messages.success(request, 'Congratulations! Your account is activated.')
    return redirect('login')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, "You are logged out!")
    return redirect("login")
    

@login_required(login_url='login')
def dashboard(request):
    user_profile = UserProfile.objects.filter(user=request.user).first()
    orders = Order.objects.order_by("-created_at").filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()

    context = {
        "orders_count": orders_count,
        "user_profile": user_profile
    }

    return render(request, 'accounts/dashboard.html', context)


def forgot_password(request):
    if request.method == "POST":
        email = request.POST["email"]
        is_current_user = Account.objects.filter(email=email).exists()

        if not is_current_user:
            messages.error(request, "Account does not exist!")
            return redirect('forgotPassword')

        user = Account.objects.get(email__exact=email)

        site = get_host_site(request)
        mail_subject = "Reset your password"
        message = render_to_string('accounts/reset_password_email.html', {
            'user': user,
            'domain': site,
            'uid': urlsafe_base64_encode(force_bytes(user.id)),
            'token': default_token_generator.make_token(user),
        })
        send_email = EmailMessage(mail_subject, message, to=[email])
        send_email.send()

        messages.success(request, 'Password reset email has been sent to your email address.')
        return redirect('login')

    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(Account.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user is None and not default_token_generator.check_token(user, token):
        messages.error(request, 'This link has been expired!')
        return redirect('login')

    request.session['uid'] = uid
    messages.success(request, "Please reset your password!")
    return redirect('resetPassword')


def reset_password(request):
    if request.method == "POST":
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, "Password reset successful!")
            return redirect("login")

        else:
            messages.error(request, "Password does not match!")
            return redirect("resetPassword")
    
    return render(request, 'accounts/resetPassword.html')


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.order_by("-created_at").filter(user=request.user, is_ordered=True)

    context = {
        "orders": orders
    }

    return render(request, "accounts/my_orders.html", context)


@login_required(login_url='login')
def edit_profile(request):
    user_profile = UserProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated")
            return redirect("edit_profile")
        
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "user_profile": user_profile
    }

    return render(request, "accounts/edit_profile.html", context)


@login_required(login_url='login')
def change_password(request):
    if request.method == "POST":
        current_password = request.POST["current_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]

        user = Account.objects.filter(username__exact=request.user.username).first()

        if new_password == confirm_password:
            success = user.check_password(current_password)

            if success:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password update successfully")
                return redirect("change_password")
            
            else:
                messages.error(request, "Please enter valid current password")
                return redirect("change_password")
            
        else:
            messages.error(request, "Password does not match")
            return redirect("change_password")

    return render(request, "accounts/change_password.html")



@login_required(login_url="login")
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)

    subtotal = 0

    for i in order_detail:
        subtotal += i.product_price * i.quantity

    context = {
        "order_detail": order_detail,
        "order": order,
        "subtotal": subtotal
    }

    return render(request, "accounts/order_detail.html", context)
