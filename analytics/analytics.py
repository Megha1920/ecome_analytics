from django.db.models import Sum, Count, F, Q, Max  
from datetime import timedelta
from .models import OrderItem, Customer

class SalesAnalytics:
    
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    
    def calculate_revenue_by_category(self):
        revenue_by_category = (
            OrderItem.objects.filter(order__order_date__range=[self.start_date, self.end_date])
            .values(category_name=F('product__category__name'))
            .annotate(total_revenue=Sum(F('price_at_time_of_order') * F('quantity')))
        )
        return revenue_by_category

    
    def top_selling_products_by_country(self):
        top_products_by_country = (
            OrderItem.objects.filter(order__order_date__range=[self.start_date, self.end_date])
            .values(country=F('order__customer__country'), product_name=F('product__name'))
            .annotate(total_sales=Sum('quantity'))
            .order_by('-total_sales')
        )
        return top_products_by_country

    # Computing customer churn rate
    def compute_customer_churn_rate(self):
        churned_customers = (
            Customer.objects.annotate(
                last_order_date=Max('orders__order_date')
            ).filter(
                last_order_date__lt=self.end_date - timedelta(days=180)  # Assuming churn if no order in last 6 months
            ).count()
        )
        total_customers = Customer.objects.count()
        if total_customers == 0:
            return 0
        churn_rate = (churned_customers / total_customers) * 100
        return churn_rate
