from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
    if 'admin' in request.path:
        return {}
    
    cart_count = 0
    try:
        if request.user.is_authenticated:
            # For logged-in users
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            # For guest users
            cart = Cart.objects.filter(cart_id=_cart_id(request)).first()
            if cart:
                cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            else:
                cart_items = []
        
        for item in cart_items:
            cart_count += item.quantity
    except:
        cart_count = 0
    
    return {'cart_count': cart_count}

