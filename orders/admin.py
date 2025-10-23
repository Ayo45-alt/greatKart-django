from django.contrib import admin
from .models import Payment, Order, OrderProduct


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'tax', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]
    
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'


class OrderProductAdmin(admin.ModelAdmin):
    list_display = ['order', 'payment', 'user', 'product', 'quantity', 'product_price', 'ordered', 'get_variations']
    list_filter = ['ordered']
    search_fields = ['order__order_number', 'product__product_name', 'user__email']
    
    def get_variations(self, obj):
        variations = obj.variations.all()
        return ', '.join([f"{v.variation_category}: {v.variation_value}" for v in variations])
    get_variations.short_description = 'Variations'


admin.site.register(Payment)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct, OrderProductAdmin)