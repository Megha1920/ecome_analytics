# analytics/models.py

from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver


class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class ProductManager(models.Manager):
    def expensive_products(self, min_price):
        return self.filter(price__gt=min_price)


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    SKU = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, blank=True)

    # Custom manager
    objects = ProductManager()

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=100)
    registration_date = models.DateField()

    def __str__(self):
        return self.name

    def calculate_lifetime_value(self):
        # Assuming each order has a total_amount field
        orders = self.orders.all()
        return orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, related_name='orders', on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

    def calculate_tax(self):
        tax_rates = {
            'USA': 0.1,    # 10%
            'UK': 0.2,     # 20%
            'India': 0.18   # 18%
            # Add more countries as needed
        }
        country_tax_rate = tax_rates.get(self.customer.country, 0)
        return self.total_amount * country_tax_rate


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_time_of_order = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


@receiver(post_save, sender=OrderItem)
def update_inventory(sender, instance, **kwargs):
    inventory = instance.product.inventory
    if inventory:
        inventory.quantity -= instance.quantity
        inventory.save()


class Inventory(models.Model):
    product = models.OneToOneField(Product, related_name='inventory', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    last_restocked_date = models.DateField()

    def __str__(self):
        return f"{self.product.name} - {self.quantity} in stock"

    def save(self, *args, **kwargs):
        # Check if inventory is running low
        if self.quantity < 10:
            # Logic to send a restock alert (e.g., send an email or alert admin)
            print(f"Alert: {self.product.name} is low in stock!")
        super().save(*args, **kwargs)

