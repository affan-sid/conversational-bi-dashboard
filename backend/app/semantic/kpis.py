import json
from pathlib import Path

SEMANTIC_FILE = Path("notebooks/semantic_layer.json")

with open(SEMANTIC_FILE, "r") as f:
    semantic_data = json.load(f)

KPI_DEFINITIONS = semantic_data["kpis"]

def map_to_kpi(user_query: str):
    
    query = user_query.lower()
    synonym_map = {
        "revenue": ["total revenue", "revenue", "income", "how much revenue", "sales revenue"],
        "gross_profit": ["gross profit"],
        "net_profit": ["net profit", "net income", "profit margin", "why is profit"],
        "cash_runway": ["cash runway", "months of cash", "runway", "burn rate", "how many months", "cash left"],
        "top_products": ["top products", "best selling", "best product", "popular product", "which product", "sell best", "sells best", "products sell"],
        "marketing_roi": ["marketing roi", "return on investment", "campaign", "wasting money", "wasting", "best campaign", "worst campaign", "campaign performance", "which campaign"],
        "customer_retention_rate": ["customer retention", "retention rate", "retention"],
        "churn_risk": ["churn risk", "customer churn", "churn"],
        "avg_order_value": ["average order value", "avg order value", "aov", "order value"],
        "order_fulfillment_time": ["order fulfillment", "fulfillment time"],
        "revenue_by_segment": ["segment", "spends the most", "segment spend", "segment revenue", "which segment", "by segment", "retail", "sme", "corporate"],
        "revenue_by_channel": ["by channel", "channel revenue", "channel performance", "which channel"],
        "revenue_by_city": ["by city", "city revenue", "city performance", "which city", "cities"],
        "expense_breakdown": ["expense breakdown", "expense category", "where are we spending", "spending on", "cost breakdown"],
        "top_customers": ["top customer", "best customer", "who are my best", "highest spending", "biggest customer"],
        "orders_by_city": ["orders from each city", "orders by city", "orders per city", "how many orders from"],
    }

    for kpi_key, keywords in synonym_map.items():
        for keyword in keywords:
            if keyword in query or kpi_key in query:
                return kpi_key

    return None