import json
from pathlib import Path

SEMANTIC_FILE = Path("notebooks/semantic_layer.json")

with open(SEMANTIC_FILE, "r") as f:
    semantic_data = json.load(f)

KPI_DEFINITIONS = semantic_data["kpis"]

def map_to_kpi(user_query: str):
    
    query = user_query.lower()
    synonym_map = {
        "revenue": ["revenue", "income", "total revenue"],
        "gross_profit": ["gross profit", "profit"],
        "net_profit": ["net profit", "net income:", "margin"],
        "cash_runway": ["cash runway", "runway", "burn rate"],
        "top_products": ["top products", "best selling products", "popular products"],
        "marketing_roi": ["marketing roi", "return on investment"],
        "customer_retention_rate": ["customer retention rate", "retention"],
        "churn_risk": ["churn risk", "customer churn"],
        "avg_order_value": ["average order value", "avg order value", "aov"],
        "order_fulfillment_time": ["order fulfillment time", "fulfillment time"]
    }

    for kpi_key, keywords in synonym_map.items():
        for keyword in keywords:
            if keyword in query or kpi_key in query:
                return kpi_key

    return None