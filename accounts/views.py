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
from django.shortcuts import redirect, render

from carts.models import Cart, CartItem
from carts.views import _cart_id

from.forms import RegistrationForm
from .models import Account


@transaction.atomic()
def register_account(data: dict) -> Account:
    first_name = data['first_name']
    last_name = data['last_name']
    email = data['email']
    phone_number = data['phone_number']
    password = data['password']
    username = data['email'].split('@')[0]

    user = Account.objects.create_user(
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        password=password,
                        username=username
                        )
    user.phone_number = phone_number
    user.save()

    return user


def send_account_verification_email(user: Account, host_site: str, form_email):
    mail_subject = "Please activate your account!"
    message = render_to_string('accounts/account_verification_email.html', {
        'user': user,
        'domain': host_site,
        'uid': urlsafe_base64_encode(force_bytes(user.id)),
        'token': default_token_generator.make_token(user),
    })
    send_email = EmailMessage(mail_subject, message, to=[form_email])
    send_email.send()


def register(request):
    form = RegistrationForm()

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = register_account(data=form.cleaned_data)
            site = get_host_site(request)
            send_account_verification_email(user=user, host_site=site, form_email=form.cleaned_data['email'])
                    
            messages.success(request, 'Thank you for registering with us. We have s sent email verification to your email address. Please verify it.')
            return redirect('/accounts/login/?command=verification&email='+form.cleaned_data['email'])
        
        messages.error(request, 'An error occurred during registration.')
        return redirect('register')

    context = {
        "form": form
    }

    return render(request, 'accounts/register.html', context)


def login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        user = auth.authenticate(email=email, password=password)

        if not user:
            messages.error(request, "Invalid login credentials")
            return redirect("login")

        try:
            cart = Cart.objects.get(cart_id = _cart_id(request))
            is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
            if is_cart_item_exists:
                cart_item = CartItem.objects.filter(cart=cart)

                for item in cart_item:
                    item.user = user
                    item.save()

        except Cart.DoesNotExist:
            pass
        auth.login(request, user)
        messages.success(request, 'You are now logged in!')
        return redirect('dashboard')
            
    return render(request, 'accounts/login.html')


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
    return render(request, 'accounts/dashboard.html')


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
