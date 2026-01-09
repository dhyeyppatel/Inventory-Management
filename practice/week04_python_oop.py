# Week 04 - Object-Oriented Programming in Python
class Product:
    def __init__(self, name, price, stock):
        self.name = name; self.price = price; self.stock = stock
    def is_available(self): return self.stock > 0
    def __str__(self): return f"{self.name} Rs.{self.price} ({'In Stock' if self.is_available() else 'Out of Stock'})"

class Inventory:
    def __init__(self): self.products = []
    def add(self, p): self.products.append(p)
    def total_value(self): return sum(p.price * p.stock for p in self.products)

inv = Inventory()
inv.add(Product("Widget A", 100, 50))
inv.add(Product("Widget B", 250, 0))
for p in inv.products: print(p)
print(f"Total Value: Rs.{inv.total_value()}")
