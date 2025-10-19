from django.shortcuts import render, redirect
from store.models import Product, Variation
from .models import Cart, CartItem
from django.shortcuts import get_object_or_404
from django.http import HttpResponse


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):
    product = Product.objects.get(id=product_id) 
    product_variation = []
    
    if request.method == 'POST':  
        for item in request.POST:
            key = item
            value = request.POST[key]
            
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                product_variation.append(variation)
            except:
                pass

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist: 
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # Check if cart item with same variations exists
    cart_item_qs = CartItem.objects.filter(product=product, cart=cart)
    
    if product_variation:
        # Look for existing item with same variations
        cart_item = None
        for item in cart_item_qs:
            if set(item.variations.all()) == set(product_variation):
                cart_item = item
                break
        
        if cart_item:
            # Found matching item, increase quantity
            cart_item.quantity += 1
            cart_item.save()
        else:
            # No matching variations, create new item
            cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
            for variation in product_variation:
                cart_item.variations.add(variation)
            cart_item.save()
    else:
        # No variations selected
        if cart_item_qs.exists():
            cart_item = cart_item_qs.first()  # Get the first one instead of .get()
            cart_item.quantity += 1
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
            cart_item.save()
    
    return redirect('cart')


def remove_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')


def remove_cart_item(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True).order_by('id')
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total) / 100
        grand_total = total + tax
    except Cart.DoesNotExist:
        pass

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)