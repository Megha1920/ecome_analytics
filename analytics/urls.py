from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    SalesDataView,
    InventoryUpdateView,
    CustomerListView,
    GenerateMonthlySalesReportView,
    AnalyticsOverviewView,
)

urlpatterns = [
    
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('sales-data/', SalesDataView.as_view(), name='sales_data'),

   
    path('inventory-update/<int:pk>/', InventoryUpdateView.as_view(), name='inventory_update'),

    
    path('customers/', CustomerListView.as_view(), name='customer_list'),

    
    path('generate-monthly-sales-report/<int:year>/<int:month>/', GenerateMonthlySalesReportView.as_view(), name='GenerateMonthlySalesReportView'),

    
    path('analytics-overview/', AnalyticsOverviewView.as_view(), name='analytics_overview'),
]
