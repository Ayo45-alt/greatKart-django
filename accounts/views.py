from django.shortcuts import render, redirect
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from django.shortcuts import get_object_or_404
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from orders.models import OrderProduct

# Verification imports
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.http import HttpResponseRedirect
from django.urls import reverse

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from cart.views import _cart_id

from orders.models import Order
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email, username=username, password=password)
            user.is_active = False
            user.phone_number = phone_number
            user.save()
            # USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, from_email='noreply@greatkart.com', to=[to_email])
            send_email.send()
            # messages.success(request, 'Registration Successful! Please check your email to activate your account.')
            return HttpResponseRedirect(reverse('login') + '?command=verification&email=' + email)
        else:
            context = {
                'form': form,
            }
            return render(request, 'accounts/register.html', context)
    else:
        form = RegistrationForm()
        context = {
            'form': form,
        }
        return render(request, 'accounts/register.html', context)


def login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                # get the user's session cart
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart)

                # get user's existing cart items (if any)
                user_cart_items = CartItem.objects.filter(user=user)

                for item in cart_items:
                    product_variations = list(item.variations.all())

                    found_match = False
                    for user_item in user_cart_items:
                        user_variations = list(user_item.variations.all())

                        # if same product + same variations → increase quantity
                        if item.product == user_item.product and product_variations == user_variations:
                            user_item.quantity += item.quantity
                            user_item.save()
                            found_match = True
                            break

                    if not found_match:
                        # reassign this guest item to the logged-in user
                        item.user = user
                        item.cart = None  # unlink from session cart
                        item.save()

            except Cart.DoesNotExist:
                pass  # guest had no cart

            auth.login(request, user)
            messages.success(request, 'You are now logged in.')

            # If they came from checkout page, go back there
            url = request.META.get('HTTP_REFERER')
            if url and 'checkout' in url:
                return redirect('checkout')

            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out')
    return redirect('login')


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated successfully!')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')
    
@login_required(login_url='login')
def dashboard(request):
    userprofile = UserProfile.objects.get(user=request.user)
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    orders_count = orders.count()
    
    context = {
        'orders': orders,
        'orders_count': orders_count,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/dashboard.html', context)
    

def forgotpassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        
        # Check if user exists
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email=email)
            
            # Generate reset token
            current_site = get_current_site(request)
            mail_subject = 'Reset your password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            
            send_email = EmailMessage(mail_subject, message, from_email='noreply@greatkart.com', to=[email])
            send_email.send()
            
            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgotpassword')
    
    return render(request, 'accounts/forgotpassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('resetpassword')
    else:
        messages.error(request, 'Invalid reset link')
        return redirect('forgotpassword')
    

def resetpassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        password2 = request.POST['password2']
        
        if password == password2:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful!')
            return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('resetpassword')
    
    return render(request, 'accounts/resetpassword.html')


def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders,
    }

    return render(request, 'accounts/my_orders.html', context)


@login_required(login_url='login')
def edit_profile(request):
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_profile': userprofile,
    }
    return render(request, 'accounts/edit_profile.html', context)



@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!') # The text "Password does not match!" is inferred from the visible code structure and typical functionality.
            return redirect('change_password')

    return render(request, 'accounts/change_password.html') # The return is inferred to be outside the initial if block


@login_required(login_url='login')
def order_detail(request, order_number):
    order = Order.objects.get(order_number=order_number, user=request.user)
    ordered_products = OrderProduct.objects.filter(order=order)
    
    subtotal = 0
    for item in ordered_products:
        subtotal += (item.product_price * item.quantity)
    
    context = {
        'order': order,
        'ordered_products': ordered_products,
        'subtotal': subtotal,
    }
    return render(request, 'accounts/order_detail.html', context)