from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from .models import Product, Supplier

class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        users = User.objects.filter(email=email)
        return (u for u in users if u.is_active and u.has_usable_password())

class ProductForm(forms.ModelForm):
    product_image = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*', 'id': 'product-image-input'})
    )

    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'category', 'stock_level', 'unit_type', 'price',
            'brand', 'manufacturer', 'weight', 'dimensions', 'cost_price',
            'is_low_stock', 'is_high_velocity'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'placeholder': 'e.g. SKU-001', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Wireless Mouse', 'class': 'form-control'}),
            'stock_level': forms.NumberInput(attrs={'placeholder': '0', 'min': '0', 'class': 'form-control'}),
            'unit_type': forms.TextInput(attrs={'placeholder': 'e.g. Units, Kg, Litres', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'placeholder': '0.00', 'min': '0', 'step': '0.01', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        # Fields MUST match your updated Supplier model exactly
        fields = [
            'name', 'contact_person', 'category', 
            'phone', 'email', 'website', 
            'street_address', 'city', 'state', 'pin_code',
            'performance_rating', 'payment_terms'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Reliance Logistics'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Rajesh Kumar'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@supplier.com'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.supplier.com'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House No, Street, Area Name'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ahmedabad'}),
            'state': forms.Select(attrs={'class': 'form-control'}, choices=[('Gujarat', 'Gujarat'), ('Maharashtra', 'Maharashtra'), ('Delhi', 'Delhi')]),
            'pin_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '380001'}),
            'performance_rating': forms.HiddenInput(), # Set via the clickable stars in HTML
            'payment_terms': forms.Select(attrs={'class': 'form-control'}, choices=[('Net 30', 'Net 30'), ('Net 60', 'Net 60'), ('Due on Receipt', 'Due on Receipt')]),
        }