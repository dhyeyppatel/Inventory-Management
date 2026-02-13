# Week 09 - MongoDB Integration with Python (PyMongo)
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["stockify_db"]

products_col   = db["products"]
categories_col = db["categories"]
users_col      = db["users"]

def insert_product(data: dict) -> str:
    result = products_col.insert_one(data)
    return str(result.inserted_id)

def get_all_products() -> list:
    return list(products_col.find({}, {"_id": 0}))

def update_product(sku: str, updates: dict) -> int:
    return products_col.update_one({"sku": sku}, {"$set": updates}).modified_count

def delete_product(sku: str) -> int:
    return products_col.delete_one({"sku": sku}).deleted_count
