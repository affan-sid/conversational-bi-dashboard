from fastapi import FastAPI, Query
from sqlalchemy import text
from backend.app.services.db import engine
from backend.app.nlp.text_to_sql import generate_sql, is_safe_sql
from backend.app.services.query_engine import execute_sql
from backend.app.analytics.anomaly_detection import run_all_detectors
from backend.app.semantic.kpis import KPI_DEFINITIONS, map_to_kpi
from backend.app.services.explainer import explain_result
from backend.app.services.insights import get_revenue_insight

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

#REMOVE ENDPOINT
@app.get("/api/anomalies")
def get_anomalies(company_id: int = Query(default=1)):
    return run_all_detectors(company_id=company_id)


@app.post("/query")
def query(user_query: str):

    if "revenue insight" in user_query.lower():
        return get_revenue_insight()
    
    if "anomaly" in user_query.lower():
        return run_all_detectors()

    kpi = map_to_kpi(user_query)
    if kpi:
        sql = KPI_DEFINITIONS[kpi]["sql"]
    else:
        sql = generate_sql(user_query)

    if not is_safe_sql(sql):
        return {"error": "Unsafe query generated"}
    
    result = execute_sql(sql)
    explanation = explain_result(user_query, result)

    return {
        "query": user_query,
        "sql": sql,
        "result": result,
        "explanation": explanation
    }