from fastapi import FastAPI, Query
from sqlalchemy import text
from backend.app.services.db import engine
from backend.app.nlp.text_to_sql import generate_sql, is_safe_sql
from backend.app.services.query_engine import execute_sql
from backend.app.analytics.anomaly_detection import run_all_detectors
from backend.app.semantic.kpis import KPI_DEFINITIONS, map_to_kpi
from backend.app.services.explainer import explain_result
from backend.app.services.insights import get_revenue_insight
from backend.app.services.recommendations import generate_recommendations

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Conversational BI API running"}

@app.get("/revenue")
def get_revenue():
    query = text("SELECT SUM(line_total) AS revenue FROM fact_sales WHERE status = 'completed' ")
    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    return {"revenue": float(result[0])}

@app.get("/top-products")
def top_products():
    query = text("""
        SELECT
        dp.product_name,
        SUM(fs.line_total) as revenue
        FROM fact_sales fs
        JOIN dim_products dp
        ON fs.product_id = dp.product_id
        WHERE fs.status = 'completed'
        GROUP BY dp.product_name
        ORDER BY revenue DESC
        LIMIT 5
        """)
    with engine.connect() as conn:
        result = conn.execute(query).fetchall()

    return [{"product_name": r[0], "revenue": float(r[1])} for r in result]

#REMOVE ENDPOINT
@app.get("/api/anomalies")
def get_anomalies(company_id: int = Query(default=1)):
    return run_all_detectors(company_id=company_id)

@app.post("/recommendations")
def get_recommendations(anomalies: list):
    return generate_recommendations(anomalies)
        
        

@app.get("/api/anomalies")
def get_anomalies(company_id: int = Query(default=1)):
    return run_all_detectors(company_id=company_id)


@app.post("/query")
def query(user_query: str):

    # FIX THIS LATER
    if "revenue insight" in user_query.lower():
        return get_revenue_insight()
    
    if "anomaly" in user_query.lower() or "anomalies" in user_query.lower():
        try:
            return run_all_detectors()
        except Exception as e:
            return {"error": f"{str(e)}. Anomaly data not available yet"}

    kpi = map_to_kpi(user_query)
    if kpi:
        sql = KPI_DEFINITIONS[kpi]["sql"]
    else:
        sql = generate_sql(user_query)

    if not is_safe_sql(sql):
        return {"error": "Unsafe query generated"}
    
    try:
        result = execute_sql(sql)
    except Exception as e:
        return {"query:": user_query, "sql": sql, "error": str(e)}
    
    explanation = explain_result(user_query, result)

    return {
        "query": user_query,
        "sql": sql,
        "result": result,
        "explanation": explanation
    }