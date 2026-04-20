import pandas as pd
from backend.app.services.db import engine

def load_data():
    products = pd.read_csv("data/raw/products.csv")
    orders = pd.read_csv("data/raw/orders.csv")
    order_items = pd.read_csv("data/raw/order_items.csv")

    products.to_sql("products", engine, if_exists="append", index=False)
    orders.to_sql("orders", engine, if_exists="append", index=False)
    order_items.to_sql("order_items", engine, if_exists="append", index=False)

if __name__ == "__main__":
    load_data()