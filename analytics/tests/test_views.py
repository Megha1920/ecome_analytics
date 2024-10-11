from datetime import datetime
import io
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase,APIClient
from django.utils import timezone
from analytics.models import Product, OrderItem, Order, Category, Customer, Inventory  
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

class SalesDataViewJWTTests(APITestCase):

    def setUp(self):
        
        self.user = User.objects.create_user(username='testuser', password='testpass')

       
        self.category = Category.objects.create(name='Test Category')
        self.product1 = Product.objects.create(name='Test Product 1', SKU='TEST001', price=10.00, category=self.category)
        self.product2 = Product.objects.create(name='Test Product 2', SKU='TEST002', price=20.00, category=self.category)

        now = timezone.now()  
        self.inventory1 = Inventory.objects.create(product=self.product1, quantity=100, last_restocked_date=now)
        self.inventory2 = Inventory.objects.create(product=self.product2, quantity=100, last_restocked_date=now)

        self.customer1 = Customer.objects.create(name='Customer One', email='customer1@example.com', country='USA', registration_date=now)
        self.customer2 = Customer.objects.create(name='Customer Two', email='customer2@example.com', country='UK', registration_date=now)

        self.order1 = Order.objects.create(customer=self.customer1, order_date=now, total_amount=50.00)
        self.order_item1 = OrderItem.objects.create(order=self.order1, product=self.product1, quantity=2, price_at_time_of_order=self.product1.price)
        self.order_item2 = OrderItem.objects.create(order=self.order1, product=self.product2, quantity=3, price_at_time_of_order=self.product2.price)

        self.order2 = Order.objects.create(customer=self.customer2, order_date=now, total_amount=30.00)
        self.order_item3 = OrderItem.objects.create(order=self.order2, product=self.product1, quantity=1, price_at_time_of_order=self.product1.price)

        self.url = reverse('sales_data')  

    def get_jwt_tokens_for_user(self, user):
        """Helper method to generate JWT tokens for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    def test_sales_data_view_authenticated_with_jwt(self):
        """Test that an authenticated user can access the sales data view using JWT."""
        
        tokens = self.get_jwt_tokens_for_user(self.user)
        access_token = tokens['access']

        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = [
            {'product__name': 'Test Product 1', 'total_quantity': 3, 'total_revenue': 30.00},
            {'product__name': 'Test Product 2', 'total_quantity': 3, 'total_revenue': 60.00},
        ]
        self.assertCountEqual(response.data, expected_data)

    def test_sales_data_view_with_expired_access_token_refresh(self):
        """Test access token refresh with a refresh token."""
        
        tokens = self.get_jwt_tokens_for_user(self.user)
        refresh_token = tokens['refresh']

        
        refresh_url = reverse('token_refresh')  
        response = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        
        new_access_token = response.data['access']

        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = [
            {'product__name': 'Test Product 1', 'total_quantity': 3, 'total_revenue': 30.00},
            {'product__name': 'Test Product 2', 'total_quantity': 3, 'total_revenue': 60.00},
        ]
        self.assertCountEqual(response.data, expected_data)

class InventoryUpdateViewTests(APITestCase):

    def setUp(self):
        
        self.user = User.objects.create_user(username='testuser', password='testpass')

        
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        
        category = Category.objects.create(name="Electronics")
        product = Product.objects.create(
            name="Laptop", description="A high-end laptop", SKU="LAP123", price=1200.00, category=category
        )
        self.inventory = Inventory.objects.create(product=product, quantity=100, last_restocked_date="2024-01-01")

        
        self.url = reverse('inventory_update', kwargs={'pk': self.inventory.pk})

    def test_update_inventory_quantity_unauthenticated(self):
        """Test that an unauthenticated user cannot update inventory."""
        data = {
            'quantity': 150,  
            'last_restocked_date': '2024-01-01',
            'product': self.inventory.product.pk
        }

        
        response = self.client.put(self.url, data, format='json')

        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_inventory_quantity_authenticated(self):
        """Test that an authenticated user can update inventory."""
        data = {
            'quantity': 150,  
            'last_restocked_date': '2024-01-01',
            'product': self.inventory.product.pk
        }

       
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        
        response = self.client.put(self.url, data, format='json')

        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 150)



class CustomerListViewTests(APITestCase):

    def setUp(self):
       
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()

        self.customer1 = Customer.objects.create(name="John Doe", email="john@example.com", country="USA", registration_date="2023-01-01")
        self.customer2 = Customer.objects.create(name="Jane Smith", email="jane@example.com", country="UK", registration_date="2023-02-01")

       
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

    def test_customer_list_view_authenticated(self):
      
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

      
        response = self.client.get(reverse('customer_list'))

       
        self.assertEqual(response.status_code, status.HTTP_200_OK)

       
        self.assertEqual(len(response.data), 2)

    def test_customer_list_view_unauthenticated(self):
       
        self.client.credentials()  

        
        response = self.client.get(reverse('customer_list'))

        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)





class TestGenerateMonthlySalesReportView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('GenerateMonthlySalesReportView', kwargs={'year': 2023, 'month': 9})
        
        
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.category = Category.objects.create(name='Test Category')
        product = Product.objects.create(
            name="Product X", 
            price=50.00, 
            SKU="SKU1001", 
            category=self.category 
        )

        Inventory.objects.create(
            product=product,
            quantity=20,  
            last_restocked_date=datetime.now().date()
        )
        
        customer = Customer.objects.create(
            name="Client A", 
            email="clientA@example.com", 
            country="UK", 
            registration_date="2023-01-01"
        )
        
        order = Order.objects.create(
            customer=customer, 
            status="delivered", 
            total_amount=500.00, 
            order_date=timezone.make_aware(datetime(2023, 9, 15))
        )
        
        OrderItem.objects.create(
            order=order, 
            product=product, 
            quantity=5, 
            price_at_time_of_order=100
        )

    def test_generate_monthly_sales_report_authenticated(self):
        """Test that an authenticated user can access the sales report view."""
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        
        response = self.client.get(self.url)
        
      
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename', response['Content-Disposition'])

    def test_generate_monthly_sales_report_unauthenticated(self):
        """Test that an unauthenticated user cannot access the sales report view."""
       
        response = self.client.get(self.url)
        
       
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AnalyticsOverviewViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        
        self.category = Category.objects.create(name="Test Category")
        
        self.customer = Customer.objects.create(
            name="Test Customer",
            email="test@example.com",
            country="UK",
            registration_date="2023-01-01"
        )
        
        self.product = Product.objects.create(
            name="Test Product",
            description="Description of Test Product",
            SKU="SKU123",
            price=100.00,
            category=self.category
        )
        
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=50,
            last_restocked_date="2023-01-01"
        )

        self.order = Order.objects.create(
            customer=self.customer,
            status="delivered",
            total_amount=200.00,
            order_date=timezone.make_aware(datetime(2023, 1, 10))
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price_at_time_of_order=100.00
        )

        self.url = reverse('analytics_overview')  

    @patch('analytics.views.SalesAnalytics')
    @patch('analytics.views.RecommendationEngine')
    def test_get_analytics_overview_authenticated(self, MockRecommendationEngine, MockSalesAnalytics):
       
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
       
        mock_sales_analytics_instance = MockSalesAnalytics.return_value
        mock_sales_analytics_instance.calculate_revenue_by_category.return_value = [
            {'category_name': 'Test Category', 'total_revenue': 200}
        ]
        mock_sales_analytics_instance.top_selling_products_by_country.return_value = [
            {'country': 'UK', 'product_name': 'Test Product', 'total_sales': 2}
        ]
        mock_sales_analytics_instance.compute_customer_churn_rate.return_value = 5.0

        
        mock_recommender_instance = MockRecommendationEngine.return_value
        mock_recommender_instance.recommend_based_on_order_history.return_value = [self.product]
        mock_recommender_instance.recommend_based_on_similar_customers.return_value = [self.customer]
        mock_recommender_instance.recommend_based_on_inventory.return_value = [self.product]

        
        response = self.client.get(self.url, {'customer_id': self.customer.id})

        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('revenue_by_category', response.data)
        self.assertIn('top_products_by_country', response.data)
        self.assertIn('churn_rate', response.data)
        self.assertIn('recommendations', response.data)

        
        self.assertIn('order_history', response.data['recommendations'])
        self.assertIn('similar_customers', response.data['recommendations'])
        self.assertIn('in_stock', response.data['recommendations'])
        
       
        expected_start_date = timezone.make_aware(datetime(2023, 1, 1, 0, 0))
        expected_end_date = timezone.make_aware(datetime(2023, 12, 31, 0, 0))

        MockSalesAnalytics.assert_called_once_with(expected_start_date, expected_end_date)
        MockRecommendationEngine.assert_called_once_with(self.customer)

    def test_get_analytics_overview_unauthenticated(self):
        
        response = self.client.get(self.url, {'customer_id': self.customer.id})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
