import json
from pathlib import Path

SEMANTIC_FILE = Path("notebooks/semantic_layer.json")

with open(SEMANTIC_FILE, "r") as f:
    semantic_data = json.load(f)

KPI_DEFINITIONS = semantic_data["kpis"]

def map_to_kpi(user_query: str):

    query = user_query.lower()

    # NOTE: order matters — more specific intents must come before generic "revenue"
    # so "revenue by segment" is caught before the bare "revenue" keyword fires.
    synonym_map = {
        # ── Specific revenue breakdowns (checked BEFORE generic revenue) ──────
        "revenue_by_segment": [
            "by segment", "segment revenue", "segment spend", "which segment",
            "spends the most", "retail", "sme", "corporate", "revenue by segment",
        ],
        "revenue_by_channel": [
            "by channel", "channel revenue", "channel performance", "which channel",
            "revenue by channel",
        ],
        "revenue_by_city": [
            "by city", "city revenue", "city performance", "which city", "cities",
            "revenue by city",
        ],
        # ── Service-specific (checked before generic revenue) ─────────────────
        "top_services": [
            "top services", "best service", "popular service", "which service",
            "service performance",
        ],
        "service_revenue": [
            "service revenue", "revenue from services", "how much from services",
            "service revenue breakdown",
        ],
        # ── Customers (before revenue, "by revenue" suffix must not confuse) ──
        "top_customers": [
            "top customer", "best customer", "who are my best",
            "highest spending", "biggest customer", "top customers",
        ],
        # ── Generic revenue (after all specific revenue intents) ─────────────
        "revenue": [
            "total revenue", "how much revenue", "sales revenue", "total sales",
            "how much did we sell", "how much have we made", "total income",
            "income for", "income this", "income last",
        ],
        # ── Profit ───────────────────────────────────────────────────────────
        "gross_profit": ["gross profit"],
        "net_profit": ["net profit", "net income", "profit margin", "why is profit"],
        # ── Cash ─────────────────────────────────────────────────────────────
        "cash_runway": [
            "cash runway", "months of cash", "runway", "burn rate",
            "how many months", "cash left", "cash is left",
        ],
        # ── Products ─────────────────────────────────────────────────────────
        "top_products": [
            "top products", "best selling", "best-selling", "best product",
            "popular product", "which product", "sell best", "sells best",
            "products sell", "top 5 product", "top 10 product",
        ],
        # ── Marketing ────────────────────────────────────────────────────────
        "worst_campaign": [
            "wasting money", "worst campaign", "losing money", "negative roi",
            "pausing campaign", "should i pause", "pause campaign", "waste",
            "worst performing", "which campaign to cut", "cut campaign",
        ],
        "marketing_roi": [
            "marketing roi", "return on investment", "best campaign",
            "campaign performance", "which campaign", "campaign roi",
            "top campaign", " roi", "campaign has the best",
        ],
        # ── Customers ────────────────────────────────────────────────────────
        "customer_retention_rate": ["customer retention", "retention rate", "retention"],
        "churn_risk": ["churn risk", "customer churn", "churn"],
        # ── Orders / AOV ─────────────────────────────────────────────────────
        "avg_order_value": ["average order value", "avg order value", "aov", "order value"],
        "orders_by_city": ["orders from each city", "orders by city", "orders per city", "how many orders from"],
        # ── Expenses ─────────────────────────────────────────────────────────
        "expense_breakdown": [
            "expense breakdown", "expense category", "where are we spending",
            "spending on", "cost breakdown",
        ],
    }

    for kpi_key, keywords in synonym_map.items():
        for keyword in keywords:
            if keyword in query or kpi_key in query:
                return kpi_key

    return None