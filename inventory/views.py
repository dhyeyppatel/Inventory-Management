from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse, JsonResponse

# Updated imports to include Order, OrderItem, json, Decimal, and Q for advanced searching
from .models import Category, Product, UserProfile, ContactMessage, Warehouse, StockTransfer, Supplier, Order, OrderItem
from .forms import ProductForm, SupplierForm
from django.db.models import Q
import requests
import csv
import random 
from datetime import datetime
import json
from decimal import Decimal

def landing_page(request):
    return render(request, 'inventory/landing.html')

# --- REAL AUTHENTICATION LOGIC ---

def login_page(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username') 
        password = request.POST.get('password')
        user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            login(request, user)
            return redirect('warehouse_overview')
        else:
            messages.error(request, "Invalid login credentials. Please register if you don't have an account.")
            
    return render(request, 'inventory/login.html')

def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        business_name = request.POST.get('business_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            if not User.objects.filter(username=username).exists() and not User.objects.filter(email=email).exists():
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(user=user, business_name=business_name)
                
                request.session['registered_user'] = username
                return redirect('register_success')
            else:
                messages.error(request, "Username or Email already exists.")
        else:
            messages.error(request, "Passwords do not match.")
            
    return render(request, 'inventory/register.html')

def register_success_page(request):
    username = request.session.get('registered_user', 'User')
    context = {'dynamic_username': username}
    return render(request, 'inventory/register_success.html', context)

def check_email_page(request):
    email = request.session.get('reset_email', 'your email address')
    context = {'dynamic_email': email}
    return render(request, 'inventory/check_email.html', context)

# --- PROFILE & LOGOUT LOGIC ---

def logout_user(request):
    logout(request) 
    return redirect('landing_page') 

def edit_profile_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')
        new_business = request.POST.get('business_name')

        if new_username and User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
            messages.error(request, "That username is already taken.")
        elif new_email and User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
            messages.error(request, "That email address is already in use.")
        else:
            user = request.user
            if new_username: user.username = new_username
            if new_email: user.email = new_email
            user.save()

            try:
                profile = user.userprofile
                if new_business: profile.business_name = new_business
                profile.save()
            except UserProfile.DoesNotExist:
                if new_business: UserProfile.objects.create(user=user, business_name=new_business)
            
            messages.success(request, "Profile updated successfully!")
            return redirect('edit_profile')

    return render(request, 'inventory/edit_profile.html')

# --- WAREHOUSE MANAGEMENT LOGIC ---

def manage_warehouses_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        delete_id = request.POST.get('delete_warehouse_id')
        if delete_id:
            try:
                wh_to_delete = Warehouse.objects.get(id=delete_id, user=request.user)
                wh_name = wh_to_delete.name
                wh_to_delete.delete()
                
                remaining = Warehouse.objects.filter(user=request.user)
                if remaining.exists() and not remaining.filter(is_default=True).exists():
                    new_default = remaining.first()
                    new_default.is_default = True
                    new_default.save()
                    
                messages.success(request, f"Location '{wh_name}' was successfully deleted.")
            except Warehouse.DoesNotExist:
                messages.error(request, "Failed to delete warehouse.")
            return redirect('manage_warehouses')

        new_wh_name = request.POST.get('new_warehouse_name')
        new_wh_loc = request.POST.get('new_warehouse_location')
        
        if new_wh_name and new_wh_loc:
            user_wh_list = list(Warehouse.objects.filter(user=request.user))
            is_first = len(user_wh_list) == 0
            
            Warehouse.objects.create(
                user=request.user, 
                name=new_wh_name, 
                location=new_wh_loc,
                is_default=is_first
            )
            messages.success(request, f"Location '{new_wh_name}' added successfully!")
            return redirect('manage_warehouses')

    user_warehouses = Warehouse.objects.filter(user=request.user)
    return render(request, 'inventory/manage_warehouses.html', {'warehouses': user_warehouses})

# --- HELPER FUNCTION FOR DROPDOWNS ---

def get_warehouse_context(request):
    """Helper function to fetch the user's warehouses and the currently selected one."""
    user_warehouses = list(Warehouse.objects.filter(user=request.user))
    selected_warehouse_id = request.GET.get('warehouse_id')
    current_warehouse = None

    if selected_warehouse_id:
        for wh in user_warehouses:
            if str(wh.id) == str(selected_warehouse_id):
                current_warehouse = wh
                break
    else:
        for wh in user_warehouses:
            if wh.is_default:
                current_warehouse = wh
                break
        if not current_warehouse and user_warehouses:
            current_warehouse = user_warehouses[0]
            
    return user_warehouses, current_warehouse

# --- BASIC PAGES ---

def about_page(request):
    return render(request, 'inventory/about.html')

def contact_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        email_body = f"New message from {name} ({email}):\n\n{message}"
        
        try:
            send_mail(
                subject=f"Stockify Contact: {subject}",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "Your message has been sent successfully! Our team will get back to you soon.")
        except Exception as e:
            messages.warning(request, "Message saved to our database, but the email notification was delayed.")

        return redirect('contact')

    return render(request, 'inventory/contact.html')

def pricing_page(request):
    return render(request, 'inventory/pricing.html')

def roadmap_page(request):
    return render(request, 'inventory/roadmap.html')

def careers_page(request):
    return render(request, 'inventory/careers.html')

# --- INVENTORY & DASHBOARD LOGIC ---

def warehouse_overview_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    business_entity = "Main Warehouse"
    try:
        business_entity = request.user.userprofile.business_name
    except UserProfile.DoesNotExist:
        pass

    user_warehouses, current_warehouse = get_warehouse_context(request)
    all_categories = list(Category.objects.all())
    
    search_query = request.GET.get('search', '').strip()
    
    if current_warehouse:
        qs = Product.objects.filter(warehouse=current_warehouse)
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) | 
                Q(sku__icontains=search_query) | 
                Q(category__name__icontains=search_query)
            )
        all_products = list(qs.order_by('-id'))
        display_warehouse_name = current_warehouse.name
    else:
        all_products = []
        display_warehouse_name = "No Warehouses Added Yet"

    high_velocity_items = [p for p in all_products if p.is_high_velocity][:10]
    low_stock_items = [p for p in all_products if p.is_low_stock][:10]

    total_stock_value = sum(p.stock_level * float(str(p.price)) for p in all_products)
    low_stock_count = len(low_stock_items)

    if total_stock_value >= 10000000:
        formatted_value = f"₹{total_stock_value / 10000000:.2f} Cr"
    elif total_stock_value >= 100000:
        formatted_value = f"₹{total_stock_value / 100000:.2f} L"
    else:
        formatted_value = f"₹{total_stock_value:,.2f}"

    context = {
        'categories': all_categories,
        'recent_products': all_products[:10],
        'high_velocity_items': high_velocity_items,
        'low_stock_items': low_stock_items,
        'total_stock_value': formatted_value,
        'low_stock_count': low_stock_count,
        'active_shipments': 0,
        'space_utilization': 0,
        'business_name': business_entity, 
        
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
        'display_warehouse_name': display_warehouse_name,
        'search_query': search_query,
    }

    return render(request, 'inventory/warehouse.html', context)


def all_categories_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)
    categories = list(Category.objects.all())
    
    context = {
        'categories': categories,
        'username': request.user.username,
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
    }
    
    return render(request, 'inventory/all_categories.html', context)


def category_detail_page(request, category_name):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    # Find the category and its products for the SELECTED warehouse
    category_matches = list(Category.objects.filter(name__iexact=category_name))
    
    if category_matches:
        category = category_matches[0]
        if current_warehouse:
            products = list(Product.objects.filter(category=category, warehouse=current_warehouse))
        else:
            products = []
        display_name = category.name
    else:
        products = []
        display_name = category_name

    context = {
        'category_name': display_name,
        'products': products,
        'username': request.user.username,
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
    }

    return render(request, 'inventory/category_detail.html', context)


def admin_console_page(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    if current_warehouse:
        all_products = list(Product.objects.filter(warehouse=current_warehouse).order_by('-id'))
        display_warehouse_name = current_warehouse.name
    else:
        all_products = []
        display_warehouse_name = "No Locations Added"

    total_products = len(all_products)
    total_store_value = sum(p.stock_level * float(str(p.price)) for p in all_products)
    out_of_stock = len([p for p in all_products if p.stock_level == 0])
    low_stock = len([p for p in all_products if p.is_low_stock and p.stock_level > 0])

    formatted_value = f"₹{total_store_value:,.0f}"

    context = {
        'total_products': total_products,
        'total_store_value': formatted_value,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'recent_products': all_products[:5],
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
        'display_warehouse_name': display_warehouse_name,
    }

    return render(request, 'inventory/admin_console.html', context)

def notifications_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    business_entity = "Main Warehouse"
    try:
        business_entity = request.user.userprofile.business_name
    except UserProfile.DoesNotExist:
        pass

    user_warehouses, current_warehouse = get_warehouse_context(request)

    if current_warehouse:
        all_products = list(Product.objects.filter(warehouse=current_warehouse))
        display_warehouse_name = current_warehouse.name
    else:
        all_products = []
        display_warehouse_name = "No Locations Added"

    low_stock_items = [p for p in all_products if p.is_low_stock]

    context = {
        'business_name': business_entity,
        'low_stock_items': low_stock_items,
        'username': request.user.username,
        
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
        'display_warehouse_name': display_warehouse_name,
    }
    
    return render(request, 'inventory/notifications.html', context)

# --- NEW ADMIN CONSOLE SUB-PAGES ---

def inventory_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    search_query = request.GET.get('search', '').strip()
    
    products = []
    top_category = "N/A"
    total_store_value = 0

    if current:
        qs = Product.objects.filter(warehouse=current)
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) | 
                Q(sku__icontains=search_query) | 
                Q(category__name__icontains=search_query)
            )
        products = list(qs.order_by('-id'))
        
    if products:
        total_store_value = sum(p.stock_level * float(str(p.price)) for p in products)
        from collections import Counter
        categories = [p.category.name for p in products if p.category]
        if categories:
            top_category = Counter(categories).most_common(1)[0][0]
            
    low_stock = len([p for p in products if p.is_low_stock and p.stock_level > 0])
    
    context = {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'products': products,
        'total_products': len(products),
        'total_store_value': f"₹{total_store_value:,.0f}",
        'low_stock': low_stock,
        'top_category': top_category,
        'search_query': search_query,
    }
    return render(request, 'inventory/inventory.html', context)

def product_list_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    search_query = request.GET.get('search', '').strip()
    
    products = []
    if current:
        qs = Product.objects.filter(warehouse=current)
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) | 
                Q(sku__icontains=search_query) | 
                Q(category__name__icontains=search_query)
            )
        products = qs.order_by('-id')
        
    out_of_stock_count = len([p for p in products if p.stock_level == 0])
    low_stock_count = len([p for p in products if p.is_low_stock and p.stock_level > 0])
        
    context = {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'products': products,
        'total_products': len(products),
        'out_of_stock_count': out_of_stock_count,
        'low_stock_count': low_stock_count,
        'search_query': search_query,
    }
    return render(request, 'inventory/product_list.html', context)

# --- DYNAMIC STOCK MOVEMENT LOGIC ---
def stock_movement_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    if request.method == 'POST':
        source_id = request.POST.get('source_warehouse')
        dest_id = request.POST.get('destination_warehouse')
        product_id = request.POST.get('product')
        quantity_str = request.POST.get('quantity', '0')
        reference_id = request.POST.get('reference_id')
        
        try:
            quantity = int(quantity_str)
            # Auto-generate Reference ID if user left it blank
            if not reference_id:
                reference_id = f"#TRF-{datetime.now().strftime('%M%S')}"
                
            source_wh = Warehouse.objects.get(id=source_id, user=request.user)
            dest_wh = Warehouse.objects.get(id=dest_id, user=request.user)
            source_product = Product.objects.get(id=product_id, warehouse=source_wh)
            
            if source_wh == dest_wh:
                messages.error(request, "Error: Source and Destination warehouses must be different.")
            elif quantity <= 0:
                messages.error(request, "Error: Quantity must be greater than zero.")
            elif source_product.stock_level < quantity:
                messages.error(request, f"Error: Not enough stock! You only have {source_product.stock_level} available.")
            else:
                # 1. Deduct stock from source (use update() to bypass Djongo validation)
                Product.objects.filter(id=source_product.id).update(
                    stock_level=source_product.stock_level - quantity
                )
                
                # 2. Add stock to destination warehouse
                dest_product = Product.objects.filter(name=source_product.name, warehouse=dest_wh).first()
                
                if dest_product:
                    Product.objects.filter(id=dest_product.id).update(
                        stock_level=dest_product.stock_level + quantity
                    )
                else:
                    base_sku = source_product.sku.split('-WH')[0] 
                    new_sku = f"{base_sku}-WH{dest_wh.id}"
                    
                    Product.objects.create(
                        warehouse=dest_wh,
                        sku=new_sku,
                        name=source_product.name,
                        category=source_product.category,
                        brand=source_product.brand,
                        manufacturer=source_product.manufacturer,
                        weight=source_product.weight,
                        dimensions=source_product.dimensions,
                        cost_price=float(str(source_product.cost_price)) if source_product.cost_price else None,
                        price=float(str(source_product.price)) if source_product.price else 0.00,
                        unit_type=source_product.unit_type,
                        image_url=source_product.image_url,
                        stock_level=quantity
                    )
                    
                # 3. Save the Transfer Receipt
                StockTransfer.objects.create(
                    user=request.user,
                    reference_id=reference_id,
                    product=source_product, 
                    source_warehouse=source_wh,
                    destination_warehouse=dest_wh,
                    quantity=quantity,
                    status='COMPLETED'
                )
                
                messages.success(request, f"Success! Transferred {quantity} units of {source_product.name} to {dest_wh.name}.")
                return redirect('stock_movement')
                
        except Exception as e:
            messages.error(request, f"Transfer failed: Please ensure all fields are selected properly.")
            
    all_user_products = Product.objects.filter(warehouse__in=warehouses).order_by('name')
    transfer_history = StockTransfer.objects.filter(user=request.user).order_by('-date')
    
    context = {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'products': all_user_products,
        'transfers': transfer_history
    }
    return render(request, 'inventory/stock_movement.html', context)

# --- DYNAMIC SUPPLIERS LOGIC ---

def suppliers_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    # Fetch all suppliers belonging to this user
    suppliers = Supplier.objects.filter(user=request.user).order_by('-id')
    
    context = {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'suppliers': suppliers,
        'total_suppliers': len(suppliers)
    }
    return render(request, 'inventory/suppliers.html', context)

def add_supplier(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    if request.method == 'POST':
        # 1. Manually extract data from the POST request to bypass the Djongo bug
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        website = request.POST.get('website')
        street_address = request.POST.get('street_address')
        city = request.POST.get('city')
        state = request.POST.get('state', 'Gujarat')
        pin_code = request.POST.get('pin_code')
        payment_terms = request.POST.get('payment_terms', 'Net 30')
        category_id = request.POST.get('category')

        # --- FIXED: Extract the performance rating ---
        performance_rating = request.POST.get('performance_rating', 3)

        # 2. Fetch the category safely
        cat_obj = None
        if category_id:
            try:
                cat_obj = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                pass

        # 3. Randomize colors for the UI avatars
        bg_colors = ['#eff6ff', '#f0fdf4', '#fff7ed', '#fef2f2', '#f5f3ff']
        txt_colors = ['#2563eb', '#16a34a', '#ea580c', '#dc2626', '#7c3aed']
        color_index = random.randint(0, 4)
        
        # 4. Save directly to the database (100% safe from Djongo bugs!)
        try:
            Supplier.objects.create(
                user=request.user,
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                website=website,
                street_address=street_address,
                city=city,
                state=state,
                pin_code=pin_code,
                payment_terms=payment_terms,
                category=cat_obj,
                performance_rating=int(performance_rating), # Saved correctly now
                avatar_color=bg_colors[color_index],
                text_color=txt_colors[color_index]
            )
            messages.success(request, f"Supplier '{name}' added successfully!")
            return redirect('suppliers')
        except Exception as e:
            messages.error(request, "Failed to save supplier. Please check your inputs.")
            return redirect('add_supplier')
            
    else:
        form = SupplierForm()
        
    return render(request, 'inventory/add_supplier.html', {
        'form': form, 
        'warehouses': warehouses, 
        'current_warehouse': current
    })

def edit_supplier(request, supplier_id):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    try:
        supplier = Supplier.objects.get(id=supplier_id, user=request.user)
    except Supplier.DoesNotExist:
        messages.error(request, "Supplier not found.")
        return redirect('suppliers')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        website = request.POST.get('website')
        street_address = request.POST.get('street_address')
        city = request.POST.get('city')
        state = request.POST.get('state', 'Gujarat')
        pin_code = request.POST.get('pin_code')
        payment_terms = request.POST.get('payment_terms', 'Net 30')
        performance_rating = request.POST.get('performance_rating', '3')
        category_id = request.POST.get('category')

        cat_obj = None
        if category_id:
            try:
                cat_obj = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                pass

        try:
            Supplier.objects.filter(id=supplier_id, user=request.user).update(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                website=website,
                street_address=street_address,
                city=city,
                state=state,
                pin_code=pin_code,
                payment_terms=payment_terms,
                performance_rating=int(performance_rating) if performance_rating else 3,
                category=cat_obj,
            )
            messages.success(request, f"Supplier '{name}' updated successfully!")
            return redirect('suppliers')
        except Exception as e:
            messages.error(request, "Failed to update supplier. Please check your inputs.")
    
    form = SupplierForm(instance=supplier)
    return render(request, 'inventory/edit_supplier.html', {
        'form': form,
        'supplier': supplier,
        'warehouses': warehouses,
        'current_warehouse': current
    })

def delete_supplier(request, supplier_id):
    if not request.user.is_authenticated: return redirect('login')
    
    if request.method == 'POST':
        try:
            supplier = Supplier.objects.get(id=supplier_id, user=request.user)
            supplier_name = supplier.name
            supplier.delete()
            messages.success(request, f"Supplier '{supplier_name}' deleted successfully!")
        except Supplier.DoesNotExist:
            messages.error(request, "Supplier not found.")
    
    return redirect('suppliers')

# --- ORDER MANAGEMENT LOGIC ---

def orders_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    # Fetch the actual orders saved to the database
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    formatted_orders = []
    for o in user_orders:
        client_name = o.supplier.name if o.supplier else "Unknown"
        initials = client_name[:2].upper() if client_name != "Unknown" else "??"
        
        # FIXED: Convert Decimal128 to float before formatting
        amount = float(str(o.total_amount)) if o.total_amount else 0.0
        
        formatted_orders.append({
            'order_id': o.order_id,
            'date': o.order_date,
            'client_name': client_name,
            'name_initials': initials,
            'order_type': o.get_order_type_display().split()[0].upper(), # e.g. "PURCHASE"
            'total_amount': f"{amount:,.2f}",
            'payment_status': o.payment_status,
            'status': o.status
        })
        
    return render(request, 'inventory/orders.html', {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'orders': formatted_orders
    })

def create_order(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    if request.method == 'POST':
        order_date = request.POST.get('order_date')
        expected_delivery = request.POST.get('expected_delivery')
        order_type = request.POST.get('order_type')
        vendor_id = request.POST.get('vendor')
        remarks = request.POST.get('remarks')
        
        # Get the JSON string from our hidden input
        order_items_json = request.POST.get('order_items', '[]')
        
        try:
            items_data = json.loads(order_items_json)
            supplier = Supplier.objects.get(id=vendor_id, user=request.user)
            
            # 1. Create the Main Order
            new_order = Order.objects.create(
                user=request.user,
                warehouse=current,
                supplier=supplier,
                order_type=order_type,
                order_date=order_date,
                expected_delivery=expected_delivery if expected_delivery else None,
                remarks=remarks,
                status='Processing',
                payment_status='Pending'
            )
            
            subtotal = Decimal('0.00')
            
            # 2. Process each item in the table
            for item in items_data:
                product = Product.objects.filter(sku=item.get('sku'), warehouse=current).first()
                qty = int(item.get('qty', 1))
                price = Decimal(str(item.get('price', 0)))
                
                total_price = qty * price
                subtotal += total_price
                
                # Create the individual Order Item
                OrderItem.objects.create(
                    order=new_order,
                    product=product,
                    quantity=qty,
                    unit_price=price,
                    total_price=total_price
                )
            
            # 3. Calculate final totals securely on the backend
            gst = subtotal * Decimal('0.18')
            new_order.subtotal = subtotal
            new_order.gst = gst
            new_order.total_amount = subtotal + gst
            new_order.save()
            
            messages.success(request, f"Order {new_order.order_id} was created successfully!")
            return redirect('orders')
            
        except Exception as e:
            messages.error(request, "Failed to create order: Ensure all required fields (like Vendor) are selected.")
            return redirect('create_order')
            
    # Pass existing suppliers/vendors to the create order template
    suppliers = Supplier.objects.filter(user=request.user).order_by('name')
    
    return render(request, 'inventory/create_order.html', {
        'warehouses': warehouses, 
        'current_warehouse': current,
        'suppliers': suppliers
    })

# --- OTHER PAGES ---

def analytics_page(request):
    if not request.user.is_authenticated: return redirect('login')
    warehouses, current = get_warehouse_context(request)
    
    # 1. Base Querysets
    all_products = Product.objects.filter(warehouse__in=warehouses)
    all_orders = Order.objects.filter(user=request.user)
    
    # 2. Top KPIs (FIXED Decimal128 handling here as well to prevent similar crashes)
    total_revenue = sum(float(str(o.total_amount)) for o in all_orders if o.order_type == 'SALES')
    total_orders_count = all_orders.count()
    inventory_value = sum(p.stock_level * float(str(p.price)) for p in all_products)
    
    low_stock_products = all_products.filter(is_low_stock=True, stock_level__gt=0)
    low_stock_count = len(low_stock_products)
    
    # Extract unique categories from low stock items safely
    low_cat_set = set()
    for p in low_stock_products:
        if p.category: low_cat_set.add(p.category.name)
    low_stock_categories = len(low_cat_set)

    # 3. Top Selling Products
    top_products = list(all_products.order_by('-moved_this_month', '-stock_level')[:6])
    top_product_names = [p.name for p in top_products]
    top_product_sales = [p.moved_this_month if p.moved_this_month > 0 else p.stock_level for p in top_products]

    # 4. Inventory Distribution (Donut Chart)
    category_distribution = {}
    for p in all_products:
        cat_name = p.category.name if p.category else "Other"
        category_distribution[cat_name] = category_distribution.get(cat_name, 0) + p.stock_level

    # 5. Inventory by Warehouse (Bar Chart)
    warehouse_stats = []
    for wh in warehouses:
        wh_products = all_products.filter(warehouse=wh)
        wh_units = sum(p.stock_level for p in wh_products)
        warehouse_stats.append({
            'name': wh.name,
            'units': wh_units
        })

    # 6. Supplier Performance Table
    suppliers = Supplier.objects.filter(user=request.user).order_by('-performance_rating')[:5]

    # 7. DYNAMIC LINE CHART BASED ON DROPDOWN SELECTION
    period = request.GET.get('period', '7_days') # Defaults to 7 days
    
    actual_sales = len([o for o in all_orders if o.order_type == 'SALES'])
    actual_purchases = len([o for o in all_orders if o.order_type == 'PURCHASE'])

    if period == 'year':
        chart_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        # Generate random historical monthly data, ending with a multiple of today's actual data
        sales_data = [random.randint(100, 500) for _ in range(11)] + [actual_sales * 15 + random.randint(50, 100)]
        purchases_data = [random.randint(50, 300) for _ in range(11)] + [actual_purchases * 15 + random.randint(20, 80)]
        
    elif period == '30_days':
        chart_labels = ["Week 1", "Week 2", "Week 3", "Week 4", "This Week"]
        # Generate random historical weekly data
        sales_data = [random.randint(40, 150) for _ in range(4)] + [actual_sales * 4 + random.randint(10, 30)]
        purchases_data = [random.randint(20, 100) for _ in range(4)] + [actual_purchases * 4 + random.randint(5, 20)]
        
    else: # Default 7_days
        chart_labels = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Today"]
        # Generate random historical daily data, ending with exactly today's actual data
        sales_data = [random.randint(10, 50) for _ in range(6)] + [actual_sales]
        purchases_data = [random.randint(5, 30) for _ in range(6)] + [actual_purchases]

    context = {
        'warehouses': warehouses, 
        'current_warehouse': current,
        
        # KPI Stats
        'total_revenue': f"₹ {total_revenue:,.0f}",
        'total_orders': total_orders_count,
        'inventory_value': f"₹ {inventory_value:,.0f}",
        'low_stock_count': low_stock_count,
        'low_stock_categories': low_stock_categories,
        
        # JSON Data for Chart.js
        'chart_labels': json.dumps(chart_labels),
        'sales_data': json.dumps(sales_data),
        'purchases_data': json.dumps(purchases_data),
        
        'top_product_names': json.dumps(top_product_names),
        'top_product_sales': json.dumps(top_product_sales),
        
        'category_labels': json.dumps(list(category_distribution.keys())),
        'category_data': json.dumps(list(category_distribution.values())),
        
        'warehouse_names': json.dumps([w['name'] for w in warehouse_stats]),
        'warehouse_units': json.dumps([w['units'] for w in warehouse_stats]),
        'warehouse_stats': warehouse_stats,
        
        'suppliers': suppliers,
    }
    return render(request, 'inventory/analytics.html', context)

# --- ADD PRODUCT LOGIC (DJONGO BUG FIX APPLIED) ---

def add_product(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    if request.method == 'POST':
        # Manually extract data from POST to bypass Djongo's ForeignKey validation bug
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        brand = request.POST.get('brand')
        manufacturer = request.POST.get('manufacturer')
        weight = request.POST.get('weight')
        dimensions = request.POST.get('dimensions')
        cost_price = request.POST.get('cost_price')
        price = request.POST.get('price')
        stock_level = request.POST.get('stock_level', 0)
        unit_type = request.POST.get('unit_type', 'Units')
        is_low_stock = request.POST.get('is_low_stock') == 'on'
        is_high_velocity = request.POST.get('is_high_velocity') == 'on'

        # Fetch category safely
        cat_obj = None
        if category_id:
            try:
                cat_obj = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                pass

        image_url = ''
        uploaded_file = request.FILES.get('product_image')
        if uploaded_file:
            try:
                response = requests.post(
                    'https://ar-hosting.pages.dev/upload',
                    files={'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)}
                )
                if response.status_code == 200:
                    data = response.json()
                    image_url = data.get('url', '')
                else:
                    messages.warning(request, "Image upload failed, but product was saved without an image.")
            except Exception:
                messages.warning(request, "Could not connect to image host. Product saved without image.")

        try:
            Product.objects.create(
                warehouse=current_warehouse,
                name=name,
                sku=sku,
                category=cat_obj,
                brand=brand,
                manufacturer=manufacturer,
                weight=weight,
                dimensions=dimensions,
                cost_price=float(cost_price) if cost_price else None,
                price=float(price) if price else 0.00,
                stock_level=int(stock_level) if stock_level else 0,
                unit_type=unit_type,
                is_low_stock=is_low_stock,
                is_high_velocity=is_high_velocity,
                image_url=image_url
            )
            messages.success(request, f"Product '{name}' added successfully!")
            
            redirect_url = '/admin-console/'
            if current_warehouse:
                redirect_url += f'?warehouse_id={current_warehouse.id}'
            return redirect(redirect_url)
        except Exception as e:
            messages.error(request, f"Failed to save product. Check inputs.")
            return redirect('add_product')
    else:
        form = ProductForm()

    context = {
        'form': form,
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
    }
    return render(request, 'inventory/add_product.html', context)


# --- EDIT PRODUCT LOGIC (DJONGO BUG FIX APPLIED) ---

def edit_product(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    try:
        product = Product.objects.get(id=product_id, warehouse__user=request.user)
    except Product.DoesNotExist:
        messages.error(request, "Product not found or you don't have permission to edit it.")
        return redirect('inventory')

    if request.method == 'POST':
        # Manually extract data from POST to bypass Djongo's ForeignKey validation bug
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        brand = request.POST.get('brand')
        manufacturer = request.POST.get('manufacturer')
        weight = request.POST.get('weight')
        dimensions = request.POST.get('dimensions')
        cost_price = request.POST.get('cost_price')
        price = request.POST.get('price')
        stock_level = request.POST.get('stock_level', 0)
        unit_type = request.POST.get('unit_type', 'Units')
        is_low_stock = request.POST.get('is_low_stock') == 'on'
        is_high_velocity = request.POST.get('is_high_velocity') == 'on'

        cat_obj = None
        if category_id:
            try:
                cat_obj = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                pass

        image_url = product.image_url
        uploaded_file = request.FILES.get('product_image')
        if uploaded_file:
            try:
                response = requests.post(
                    'https://ar-hosting.pages.dev/upload',
                    files={'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)}
                )
                if response.status_code == 200:
                    data = response.json()
                    image_url = data.get('url', '')
                else:
                    messages.warning(request, "Image upload failed, but product was updated without changing the image.")
            except Exception:
                messages.warning(request, "Could not connect to image host. Product updated without changing the image.")

        try:
            Product.objects.filter(id=product_id, warehouse__user=request.user).update(
                name=name,
                sku=sku,
                category=cat_obj,
                brand=brand,
                manufacturer=manufacturer,
                weight=weight,
                dimensions=dimensions,
                cost_price=float(cost_price) if cost_price else None,
                price=float(price) if price else 0.00,
                stock_level=int(stock_level) if stock_level else 0,
                unit_type=unit_type,
                is_low_stock=is_low_stock,
                is_high_velocity=is_high_velocity,
                image_url=image_url
            )
            messages.success(request, f"Product '{name}' updated successfully!")

            redirect_url = '/admin-console/inventory/'
            if current_warehouse:
                redirect_url += f'?warehouse_id={current_warehouse.id}'
            return redirect(redirect_url)
        except Exception as e:
            messages.error(request, f"Failed to update product.")
    
    form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'warehouses': user_warehouses,
        'current_warehouse': current_warehouse,
    }
    return render(request, 'inventory/edit_product.html', context)


# --- DELETE PRODUCT LOGIC ---

def delete_product(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method != 'POST':
        return redirect('inventory')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    try:
        product = Product.objects.get(id=product_id, warehouse__user=request.user)
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' has been deleted successfully.")
    except Product.DoesNotExist:
        messages.error(request, "Product not found or you don't have permission to delete it.")

    redirect_url = '/admin-console/inventory/'
    if current_warehouse:
        redirect_url += f'?warehouse_id={current_warehouse.id}'
    return redirect(redirect_url)


# --- EXPORT REPORT LOGIC ---

def export_report(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_warehouses, current_warehouse = get_warehouse_context(request)

    if current_warehouse:
        all_products = list(Product.objects.filter(warehouse=current_warehouse).order_by('category__name', 'name'))
        warehouse_name = f"{current_warehouse.name} ({current_warehouse.location})"
    else:
        all_products = []
        warehouse_name = "No Warehouse Selected"

    total_products = len(all_products)
    total_value = sum(p.stock_level * float(str(p.price)) for p in all_products)
    out_of_stock = [p for p in all_products if p.stock_level == 0]
    low_stock = [p for p in all_products if p.is_low_stock and p.stock_level > 0]
    in_stock = [p for p in all_products if p.stock_level > 0 and not p.is_low_stock]

    category_stats = {}
    for p in all_products:
        cat_name = p.category.name
        if cat_name not in category_stats:
            category_stats[cat_name] = {'count': 0, 'value': 0.0, 'low_stock': 0, 'out_of_stock': 0}
        category_stats[cat_name]['count'] += 1
        category_stats[cat_name]['value'] += p.stock_level * float(str(p.price))
        if p.stock_level == 0:
            category_stats[cat_name]['out_of_stock'] += 1
        elif p.is_low_stock:
            category_stats[cat_name]['low_stock'] += 1

    business_name = "Stockify Business"
    try:
        business_name = request.user.userprofile.business_name
    except UserProfile.DoesNotExist:
        pass

    now = datetime.now()
    filename = f"Stockify_Report_{now.strftime('%Y%m%d_%H%M%S')}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    writer.writerow(['STOCKIFY INVENTORY REPORT'])
    writer.writerow([])
    writer.writerow(['Report Generated', now.strftime('%B %d, %Y at %I:%M %p')])
    writer.writerow(['Generated By', request.user.username])
    writer.writerow(['Business Name', business_name])
    writer.writerow(['Warehouse / Location', warehouse_name])
    writer.writerow([])

    writer.writerow(['=' * 60])
    writer.writerow(['EXECUTIVE SUMMARY'])
    writer.writerow(['=' * 60])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Products', total_products])
    writer.writerow(['Total Inventory Value', f'Rs. {total_value:,.2f}'])
    writer.writerow(['In Stock Products', len(in_stock)])
    writer.writerow(['Low Stock Alerts', len(low_stock)])
    writer.writerow(['Out of Stock Items', len(out_of_stock)])
    if total_products > 0:
        health_pct = (len(in_stock) / total_products) * 100
        writer.writerow(['Inventory Health', f'{health_pct:.1f}% Healthy'])
    writer.writerow([])

    writer.writerow(['=' * 60])
    writer.writerow(['CATEGORY BREAKDOWN'])
    writer.writerow(['=' * 60])
    writer.writerow([])
    writer.writerow(['Category', 'Products', 'Stock Value (Rs.)', 'Low Stock', 'Out of Stock'])
    for cat_name, stats in sorted(category_stats.items()):
        writer.writerow([
            cat_name,
            stats['count'],
            f"{stats['value']:,.2f}",
            stats['low_stock'],
            stats['out_of_stock'],
        ])
    writer.writerow([])

    if out_of_stock:
        writer.writerow(['=' * 60])
        writer.writerow(['OUT OF STOCK - IMMEDIATE ACTION REQUIRED'])
        writer.writerow(['=' * 60])
        writer.writerow([])
        writer.writerow(['SKU', 'Product Name', 'Category', 'Unit Price (Rs.)'])
        for p in out_of_stock:
            writer.writerow([p.sku, p.name, p.category.name, f"{float(str(p.price)):,.2f}"])
        writer.writerow([])

    if low_stock:
        writer.writerow(['=' * 60])
        writer.writerow(['LOW STOCK WARNING - RESTOCK RECOMMENDED'])
        writer.writerow(['=' * 60])
        writer.writerow([])
        writer.writerow(['SKU', 'Product Name', 'Category', 'Remaining Stock', 'Unit', 'Alert Level'])
        for p in low_stock:
            writer.writerow([p.sku, p.name, p.category.name, p.stock_level, p.unit_type, p.alert_level])
        writer.writerow([])

    writer.writerow(['=' * 60])
    writer.writerow(['DETAILED PRODUCT INVENTORY'])
    writer.writerow(['=' * 60])
    writer.writerow([])
    writer.writerow([
        'S.No.', 'SKU', 'Product Name', 'Category',
        'Stock Level', 'Unit Type', 'Unit Price (Rs.)',
        'Total Value (Rs.)', 'Stock Status', 'Alert Level',
        'High Velocity', 'Moved This Month', 'Movement Trend',
        'Image URL'
    ])

    for idx, p in enumerate(all_products, 1):
        price = float(str(p.price))
        total_val = p.stock_level * price

        if p.stock_level == 0:
            status = 'OUT OF STOCK'
        elif p.is_low_stock:
            status = 'LOW STOCK'
        else:
            status = 'IN STOCK'

        writer.writerow([
            idx,
            p.sku,
            p.name,
            p.category.name,
            p.stock_level,
            p.unit_type,
            f"{price:,.2f}",
            f"{total_val:,.2f}",
            status,
            p.alert_level if p.is_low_stock else '-',
            'Yes' if p.is_high_velocity else 'No',
            p.moved_this_month,
            p.movement_trend,
            p.image_url if p.image_url else '-',
        ])

    writer.writerow([])
    writer.writerow(['=' * 60])
    writer.writerow(['END OF REPORT'])
    writer.writerow(['=' * 60])
    writer.writerow([f'Report contains {total_products} products with total inventory value of Rs. {total_value:,.2f}'])

    return response

# --- INTERNAL API FOR BARCODE SCANNER ---
def get_product_by_sku(request):
    """
    This API endpoint takes a scanned SKU and searches the database.
    If found, it returns the product details to automatically add to the order.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})

    if request.method == 'GET':
        sku = request.GET.get('sku', '').strip()
        warehouse_id = request.GET.get('warehouse_id')

        if not sku or not warehouse_id:
            return JsonResponse({'success': False, 'error': 'Missing SKU or Warehouse ID'})

        # Search for the product in the specific warehouse
        product = Product.objects.filter(sku=sku, warehouse__id=warehouse_id).first()
        
        if product:
            return JsonResponse({
                'success': True,
                'product': {
                    'sku': product.sku,
                    'name': product.name,
                    'price': float(str(product.price)),
                    'stock': product.stock_level,
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'Product not found in this warehouse.'})