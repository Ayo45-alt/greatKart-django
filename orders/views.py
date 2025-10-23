from django.shortcuts import render, redirect
from django.http import HttpResponse
from cart.models import CartItem
from .forms import OrderForm
from .models import Order
import datetime

import json
import uuid
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from store.models import Product
from .models import Order, Payment, OrderProduct
from django.utils.html import strip_tags
from django.contrib.sites.shortcuts import get_current_site


@login_required
def payments(request):
    user = request.user
    order = Order.objects.filter(user=user, is_ordered=False).first()

    if not order:
        return redirect('store')

    # --- Simulate successful payment ---
    payment = Payment.objects.create(
        user=user,
        payment_id=str(uuid.uuid4()),
        payment_method="Simulated Payment",
        amount_paid=order.order_total,
        status="Completed"
    )

    # --- Update order status ---
    order.payment = payment
    order.is_ordered = True
    order.save()

    # --- Move cart items to OrderProduct ---
    cart_items = CartItem.objects.filter(user=user)
    for item in cart_items:
        order_product = OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.product.price,
            ordered=True
        )
        # Assign variations (if you have them)
        order_product.variations.set(item.variations.all())
        order_product.save()

        # Reduce stock
        product = item.product
        product.stock -= item.quantity
        product.save()

    # --- Clear cart ---
    cart_items.delete()

    # --- Send confirmation email ---
    current_site = get_current_site(request)
    mail_subject = 'Thank you for your order!'

    message = render_to_string('orders/order_received_email.html', {
        'user': user,
        'order': order,
        'domain': current_site.domain,  # used for image URLs
    })
    plain_message = strip_tags(message)

    email = EmailMessage(
        mail_subject,
        message,
        to=[user.email]
    )
    email.content_subtype = "html"  # ✅ This makes it send HTML
    email.send(fail_silently=True)

    # --- Redirect to order complete page ---
    return redirect('order_complete', order_number=order.order_number)


def place_order(request, total=0, quantity=0):
    current_user = request.user
    
    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()
            
            # Pass order to payments page
            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'cart_count': cart_count,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')
    

@login_required
def order_complete(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order=order)
        
        subtotal = 0
        for item in ordered_products:
            subtotal += (item.product_price * item.quantity)
        
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except Order.DoesNotExist:
        return redirect('store')

    

