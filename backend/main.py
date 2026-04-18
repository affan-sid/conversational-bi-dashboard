from fastapi import FastAPI
from sqlalchemy import text
from backend.app.services.db import engine

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Conversational BI API running"}

@app.get("/revenue")
def get_revenue():
    query = text("SELECT SUM(total_amount) AS revenue FROM orders")
    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    return {"revenue": float(result[0])}

@app.get("/top-products")
def top_products():
    query = text("""
        SELECT product_id, SUM(line_total) as revenue
        FROM order_items
        GROUP BY product_id
        ORDER BY revenue DESC
        LIMIT 5
    """)
    with engine.connect() as conn:
        result = conn.execute(query).fetchall()

    return [{"product_id": r[0], "revenue": float(r[1])} for r in result]