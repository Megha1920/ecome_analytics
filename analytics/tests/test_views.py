from datetime import datetime
import io
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase,APIClient
from django.utils import timezone
from analytics.models import Product, OrderItem, Order, Category, Customer, Inventory  # Ensure you import the Inventory model
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
class SalesDataViewTests(APITestCase):

    def setUp(self):
        # Create a category for the product
        self.category = Category.objects.create(name='Test Category')

        # Create products for testing
        self.product1 = Product.objects.create(
            name='Test Product 1',
            SKU='TEST001',
            price=10.00,
            category=self.category  # Reference the created category
        )
        self.product2 = Product.objects.create(
            name='Test Product 2',
            SKU='TEST002',
            price=20.00,
            category=self.category  # Reference the created category
        )

        # Create inventory for the products
        self.inventory1 = Inventory.objects.create(
            product=self.product1,
            quantity=100,
            last_restocked_date=timezone.now()
        )
        self.inventory2 = Inventory.objects.create(
            product=self.product2,
            quantity=100,
            last_restocked_date=timezone.now()
        )

        # Create customers for the orders
        self.customer1 = Customer.objects.create(
            name='Customer One',
            email='customer1@example.com',
            country='USA',
            registration_date=timezone.now()
        )
        self.customer2 = Customer.objects.create(
            name='Customer Two',
            email='customer2@example.com',
            country='UK',
            registration_date=timezone.now()
        )

        # Create orders with a total_amount for existing customers
        self.order1 = Order.objects.create(customer=self.customer1, order_date=timezone.now(), total_amount=50.00)
        self.order_item1 = OrderItem.objects.create(
            order=self.order1,
            product=self.product1,
            quantity=2,
            price_at_time_of_order=self.product1.price
        )
        self.order_item2 = OrderItem.objects.create(
            order=self.order1,
            product=self.product2,
            quantity=3,
            price_at_time_of_order=self.product2.price
        )

        # Create another order with a total_amount for another customer
        self.order2 = Order.objects.create(customer=self.customer2, order_date=timezone.now(), total_amount=30.00)
        self.order_item3 = OrderItem.objects.create(
            order=self.order2,
            product=self.product1,
            quantity=1,
            price_at_time_of_order=self.product1.price
        )

        # Set the URL for the sales data view
        self.url = reverse('sales_data')  # Adjust this if your URL name is different

    def test_sales_data_view(self):
        """Test the SalesDataView returns correct aggregated sales data."""
        response = self.client.get(self.url)

        # Check that the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response data
        expected_data = [
            {'product__name': 'Test Product 1', 'total_quantity': 3, 'total_revenue': 30.00},
            {'product__name': 'Test Product 2', 'total_quantity': 3, 'total_revenue': 60.00},
        ]

        # Check if the response data matches expected data
        self.assertCountEqual(response.data, expected_data)



class InventoryUpdateViewTests(APITestCase):

    def setUp(self):
        category = Category.objects.create(name="Electronics")
        product = Product.objects.create(
            name="Laptop", description="A high-end laptop", SKU="LAP123", price=1200.00, category=category
        )
        self.inventory = Inventory.objects.create(product=product, quantity=100, last_restocked_date="2024-01-01")
        self.url = reverse('inventory_update', kwargs={'pk': self.inventory.pk})

    def test_update_inventory_quantity(self):
        # Prepare the update data
        data = {
            'quantity': 150,  # Updating quantity
            'last_restocked_date': '2024-01-01',
            'product': self.inventory.product.pk
        }

        # Make the PUT request
        response = self.client.put(self.url, data, format='json')

        # Debugging output
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print("Response data:", response.data)  # Print error message for debugging

        # Assert the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the quantity was updated
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 150)



class CustomerListViewTests(APITestCase):

    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()

        # Create customers
        self.customer1 = Customer.objects.create(name="John Doe", email="john@example.com", country="USA", registration_date="2023-01-01")
        self.customer2 = Customer.objects.create(name="Jane Smith", email="jane@example.com", country="UK", registration_date="2023-02-01")

        # Obtain JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

    def test_customer_list_view_authenticated(self):
        # Set the token in the header
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        # Make a GET request to the customer list view
        response = self.client.get(reverse('customer_list'))

        # Assert the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if the response contains the customers
        self.assertEqual(len(response.data), 2)

    def test_customer_list_view_unauthenticated(self):
        # Logout the client to make the request unauthenticated
        self.client.credentials()  # Remove authentication credentials

        # Make a GET request to the customer list view
        response = self.client.get(reverse('customer_list'))

        # Assert the response status is 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestGenerateMonthlySalesReportView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('GenerateMonthlySalesReportView', kwargs={'year': 2023, 'month': 9})
        
        # Create a test category
        self.category = Category.objects.create(name='Test Category')
        
        # Creating required data
        product = Product.objects.create(
            name="Product X", 
            price=50.00, 
            SKU="SKU1001", 
            category=self.category  # Associate with the category
        )

        # Create inventory for the product
        Inventory.objects.create(
            product=product,
            quantity=20,  # Set an initial quantity
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

    def test_generate_monthly_sales_report(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename', response['Content-Disposition'])


class AnalyticsOverviewViewTest(TestCase):
    def setUp(self):
        # Create necessary test data
        self.category = Category.objects.create(
            name="Test Category"
        )
        
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
            category=self.category  # Assigning the created category
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

        self.url = reverse('analytics_overview')  # Adjust according to your URL patterns

    @patch('analytics.views.SalesAnalytics')  # Mocking SalesAnalytics
    @patch('analytics.views.RecommendationEngine')  # Mocking RecommendationEngine
    def test_get_analytics_overview(self, MockRecommendationEngine, MockSalesAnalytics):
        # Setting up the mock behavior
        mock_sales_analytics_instance = MockSalesAnalytics.return_value
        mock_sales_analytics_instance.calculate_revenue_by_category.return_value = [
            {'category_name': 'Test Category', 'total_revenue': 200}
        ]
        mock_sales_analytics_instance.top_selling_products_by_country.return_value = [
            {'country': 'UK', 'product_name': 'Test Product', 'total_sales': 2}
        ]
        mock_sales_analytics_instance.compute_customer_churn_rate.return_value = 5.0
        
        # Set up the recommender mock
        mock_recommender_instance = MockRecommendationEngine.return_value
        mock_recommender_instance.recommend_based_on_order_history.return_value = [self.product]
        mock_recommender_instance.recommend_based_on_similar_customers.return_value = [self.customer]
        mock_recommender_instance.recommend_based_on_inventory.return_value = [self.product]
        
        # Simulate a GET request
        response = self.client.get(self.url, {'customer_id': self.customer.id})

        # Check response status and content
        self.assertEqual(response.status_code, 200)
        self.assertIn('revenue_by_category', response.data)
        self.assertIn('top_products_by_country', response.data)
        self.assertIn('churn_rate', response.data)
        self.assertIn('recommendations', response.data)

        # Assert the structure of recommendations
        self.assertIn('order_history', response.data['recommendations'])
        self.assertIn('similar_customers', response.data['recommendations'])
        self.assertIn('in_stock', response.data['recommendations'])
        
        # Assertions on the content
        self.assertEqual(len(response.data['recommendations']['order_history']), 1)
        self.assertEqual(len(response.data['recommendations']['similar_customers']), 1)
        self.assertEqual(len(response.data['recommendations']['in_stock']), 1)
        
        # Assert that the mock methods were called with the expected datetime values
        expected_start_date = timezone.make_aware(datetime(2023, 1, 1, 0, 0))  # Use make_aware to create an aware datetime
        expected_end_date = timezone.make_aware(datetime(2023, 12, 31, 0, 0))  # Use make_aware to create an aware datetime

        # Assert the actual call parameters
        MockSalesAnalytics.assert_called_once_with(expected_start_date, expected_end_date)

        # Optionally check if the recommendation engine was called
        MockRecommendationEngine.assert_called_once_with(self.customer)
