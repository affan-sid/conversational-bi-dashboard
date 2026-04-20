from fastapi import FastAPI
from sqlalchemy import text
from backend.app.services.db import engine
from backend.app.nlp.text_to_sql import generate_sql, is_safe_sql
from backend.app.services.query_engine import execute_sql

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

@app.post("/query")
def query(user_query: str):
    sql = generate_sql(user_query)
    if not is_safe_sql(sql):
        return {"error": "Unsafe query generated"}
    
    result = execute_sql(sql)

    return {
        "query": user_query,
        "sql": sql,
        "result": result
    }