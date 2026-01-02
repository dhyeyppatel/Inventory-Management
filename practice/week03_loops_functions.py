# Week 03 - Loops, Functions, File Handling
def calculate_total(prices):
    return sum(p for p in prices if p > 0)

def read_products(filename):
    try:
        with open(filename) as f:
            return [line.strip() for line in f]
    except FileNotFoundError:
        return []

prices = [100, 250, 75, 320, 0, 150]
print(f"Total: {calculate_total(prices)}")
