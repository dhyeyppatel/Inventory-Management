import random
import string
from django.db import models
from django.contrib.auth.models import User

# --- AUTHENTICATION MODELS ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)

    def __str__(self):
        return self.user.username


# --- MULTI-WAREHOUSE MODELS ---

class Warehouse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warehouses')
    name = models.CharField(max_length=100) 
    location = models.CharField(max_length=200) 
    is_default = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.name} ({self.location})"


# --- INVENTORY MODELS ---

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_class = models.CharField(max_length=100, default="fa-solid fa-box")
    icon_color = models.CharField(max_length=20, default="#2563eb")

    def __str__(self):
        return self.name


class Product(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    brand = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    stock_level = models.IntegerField(default=0)
    unit_type = models.CharField(max_length=50, default="Units")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    card_color = models.CharField(max_length=20, default="#334155")
    image_url = models.URLField(max_length=500, blank=True, default='')

    is_low_stock = models.BooleanField(default=False)
    alert_level = models.CharField(
        max_length=20,
        choices=[('LOW', 'LOW'), ('CRITICAL', 'CRITICAL')],
        default='LOW'
    )

    is_high_velocity = models.BooleanField(default=False)
    moved_this_month = models.IntegerField(default=0)
    movement_trend = models.CharField(max_length=10, default="+0%")

    def __str__(self):
        return f"{self.sku} - {self.name}"


# --- CONTACT MODELS ---

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"


# --- STOCK MOVEMENT MODEL ---

class StockTransfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference_id = models.CharField(max_length=50) 
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    source_warehouse = models.ForeignKey(Warehouse, related_name='transfers_out', on_delete=models.CASCADE)
    destination_warehouse = models.ForeignKey(Warehouse, related_name='transfers_in', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('IN TRANSIT', 'IN TRANSIT'), ('COMPLETED', 'COMPLETED'), ('CANCELLED', 'CANCELLED')],
        default='COMPLETED'
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference_id} : {self.quantity}x {self.product.name}"


# --- SUPPLIER MODEL (FINAL UPDATED VERSION) ---

class Supplier(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Basic Information
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Contact Details
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(max_length=500, blank=True, null=True)
    
    # Location Details
    street_address = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, default="Gujarat")
    pin_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Performance & Terms
    performance_rating = models.IntegerField(default=3) # Store 1-5 for stars
    payment_terms = models.CharField(max_length=50, default="Net 30")
    
    # UI Design Helpers
    avatar_color = models.CharField(max_length=20, default="#eff6ff")
    text_color = models.CharField(max_length=20, default="#2563eb")

    def __str__(self):
        return self.name


# --- ORDER MODELS ---

class Order(models.Model):
    ORDER_TYPE_CHOICES = (
        ('PURCHASE', 'Purchase Order'),
        ('SALES', 'Sales Order'),
    )
    
    STATUS_CHOICES = (
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    
    PAYMENT_CHOICES = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='orders')
    
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='PURCHASE')
    order_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processing')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Pending')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-generate a unique Order ID if it doesn't exist (e.g., ORD-A92B)
        if not self.order_id:
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.order_id = f"ORD-{random_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.supplier.name if self.supplier else 'Unknown'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        # Always ensure the total price is mathematically correct
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"