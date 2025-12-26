# Week 02 - Python Basics: Variables, Data Types, Control Flow
project = "Stockify"; version = 1.0; is_active = True
items = ["product", "category", "warehouse"]
for i, item in enumerate(items, 1):
    print(f"{i}. {item}")
if is_active:
    print(f"{project} v{version} is running")
