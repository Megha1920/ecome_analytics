from django.db.models import Q
from .models import Product, Customer, OrderItem

class RecommendationEngine:
    def __init__(self, customer):
        self.customer = customer

    
    def recommend_based_on_order_history(self):
    
        ordered_product_ids = OrderItem.objects.filter(order__customer=self.customer).values_list('product_id', flat=True).distinct()

        
        ordered_products = Product.objects.filter(id__in=ordered_product_ids)
        return ordered_products

    
    def recommend_based_on_similar_customers(self):
    
        similar_customers = Customer.objects.filter(
        orders__items__product__in=self.customer.orders.values_list('items__product', flat=True)
    ).exclude(id=self.customer.id).distinct()

        return similar_customers  
    
    def recommend_based_on_inventory(self):
       
        in_stock_products = Product.objects.filter(inventory__quantity__gt=0).distinct()
        return in_stock_products
