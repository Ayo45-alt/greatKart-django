from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
    if 'admin' in request.path:
        return {}
    cart_count = 0
    try:
        cart = Cart.objects.filter(cart_id=_cart_id(request)).first()  # ✅ replaces [:1]
        if cart:
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            for item in cart_items:
                cart_count += item.quantity
    except Cart.DoesNotExist:
        cart_count = 0
    return {'cart_count': cart_count}


