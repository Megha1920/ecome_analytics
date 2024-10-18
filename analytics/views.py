from rest_framework import generics
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.views import APIView
from io import BytesIO
from rest_framework import status

from django.db.models import Sum, F
from django.shortcuts import get_object_or_404
from .models import Customer, Inventory, OrderItem
from .serializers import  CustomerSerializer, InventorySerializer
from .analytics import SalesAnalytics  
from .recommendation import RecommendationEngine  
from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated



class SalesDataView(generics.ListAPIView):
    permission_classes =  [IsAuthenticated] 

    def get_queryset(self):
        
        return OrderItem.objects.values('product__name').annotate(total_quantity=Sum('quantity'), total_revenue=Sum(F('price_at_time_of_order') * F('quantity')))

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)


class InventoryUpdateView(generics.UpdateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]


class CustomerListView(generics.ListAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class GenerateMonthlySalesReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, year, month):
        try:
           
            if not (1 <= month <= 12):
                return Response({"error": "Invalid month provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            start_date = timezone.datetime(year, month, 1)
            end_date = timezone.datetime(year, month + 1, 1) if month < 12 else timezone.datetime(year + 1, 1, 1)
            
            
            sales_data = (
                OrderItem.objects.filter(order__order_date__range=(start_date, end_date))
                .values('product__name', 'quantity', 'price_at_time_of_order')
            )

            
            if not sales_data.exists():
                return Response({"error": "No sales data found for the given month."}, status=status.HTTP_404_NOT_FOUND)

            
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = f'Sales Report {year}-{month:02d}'

            headers = ['Product Name', 'Quantity Sold', 'Price at Time of Order', 'Total Revenue']
            sheet.append(headers)

            for item in sales_data:
                total_revenue = item['quantity'] * item['price_at_time_of_order']
                sheet.append([item['product__name'], item['quantity'], item['price_at_time_of_order'], total_revenue])

            total_revenue_row = ['Total Revenue', '', '', sum(item['quantity'] * item['price_at_time_of_order'] for item in sales_data)]
            sheet.append(total_revenue_row)

            
            buffer = BytesIO()
            workbook.save(buffer)
            buffer.seek(0)

            response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="monthly_sales_report_{year}_{month:02d}.xlsx"'

            return response

        except ValueError as ve:
            
            return Response({"error": f"Invalid input: {str(ve)}"}, status=status.HTTP_400_BAD_REQUEST)

        except OrderItem.DoesNotExist:
            
            return Response({"error": "No sales data found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AnalyticsOverviewView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
       
        start_date = timezone.datetime(2023, 1, 1, tzinfo=timezone.get_current_timezone())
        end_date = timezone.datetime(2023, 12, 31, tzinfo=timezone.get_current_timezone())

        
        sales_analytics = SalesAnalytics(start_date, end_date)

        
        revenue_by_category = sales_analytics.calculate_revenue_by_category()

        
        top_products_by_country = sales_analytics.top_selling_products_by_country()

        
        churn_rate = sales_analytics.compute_customer_churn_rate()

        
        customer_id = request.query_params.get('customer_id') 
        customer = get_object_or_404(Customer, id=customer_id)  
        recommender = RecommendationEngine(customer)

        
        recommendations = {
    "order_history": [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "SKU": product.SKU,
            "price": product.price,
            "category_id": product.category.id,
        } for product in recommender.recommend_based_on_order_history()
    ],
    "similar_customers": [
        {
            "id": similar_customer.id,
            "name": similar_customer.name,
            "email": similar_customer.email,
        } for similar_customer in recommender.recommend_based_on_similar_customers()  
    ],
    "in_stock": [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "SKU": product.SKU,
            "price": product.price,
            "category_id": product.category.id,
        } for product in recommender.recommend_based_on_inventory()
    ],
}

       
        return Response({
            "revenue_by_category": list(revenue_by_category),
            "top_products_by_country": list(top_products_by_country),
            "churn_rate": churn_rate,
            "recommendations": recommendations,
        })