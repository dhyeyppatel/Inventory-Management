# Week 08 - Django Views, Templates, Form Processing
# from django.shortcuts import render, redirect

def home_view(request):
    context = {"title": "Stockify Dashboard", "user": request.user}
    return None  # render(request, "home.html", context)

def product_list_view(request):
    products = []  # Product.objects.all()
    return None  # render(request, "product_list.html", {"products": products})

def add_product_view(request):
    if request.method == "POST":
        name  = request.POST.get("name", "")
        price = request.POST.get("price", 0)
        # product = Product(name=name, price=price); product.save()
        return None  # redirect("product_list")
    return None  # render(request, "add_product.html")
