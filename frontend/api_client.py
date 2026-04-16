"""
api_client.py — All HTTP calls to Affan's FastAPI backend.

HOW TO USE:
  - While USE_MOCK = True in config.py, all functions return realistic
    mock data shaped from your real CSV files.
  - When Affan's backend is ready, set USE_MOCK = False in config.py.
    The function signatures stay identical — pages need zero changes.

IMPORT IN PAGES:
  from api_client import get_overview, get_finance, get_sales, ...
"""

import requests
import streamlit as st
from config import API_BASE_URL, USE_MOCK


# ── HELPER ────────────────────────────────────────────────────────
def _headers():
    """Attach JWT token to every request."""
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"}


def _get(endpoint: str, params: dict = None):
    """Generic GET with error handling."""
    try:
        res = requests.get(
            f"{API_BASE_URL}{endpoint}",
            headers=_headers(),
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e}")
        return None


def _post(endpoint: str, payload: dict):
    """Generic POST with error handling."""
    try:
        res = requests.post(
            f"{API_BASE_URL}{endpoint}",
            headers=_headers(),
            json=payload,
            timeout=30
        )
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════

def login(email: str, password: str):
    """Returns token + user dict, or None on failure."""
    if USE_MOCK:
        if email and password:
            return {"token": "mock-jwt-token-abc123", "user": {"full_name": "Demo User", "role": "manager"}}
        return None
    return _post("/auth/login", {"email": email, "password": password})


# ════════════════════════════════════════════════════════════════
# OVERVIEW  —  GET /api/overview
# ════════════════════════════════════════════════════════════════

def get_overview():
    """Top-level KPIs for the Executive Overview page."""
    if USE_MOCK:
        return {
            "finance": {
                "total_revenue":    125400.00,
                "total_expenses":    89200.00,
                "net_profit":        36200.00,
                "profit_margin":        28.9,
                "cash_in_bank":     210000.00,
                "monthly_burn":      29700.00,
                "cash_runway_months":   2.4,
            },
            "sales": {
                "total_orders":        1414,
                "avg_order_value":      88.7,
                "top_channel":       "website",
                "revenue_trend":     "up_6_percent",
            },
            "marketing": {
                "total_spend":       45200.00,
                "total_attributed": 134000.00,
                "overall_roi":           1.96,
                "best_campaign":   "Campaign 1",
            },
            "customers": {
                "active_customers":      95,
                "repeat_rate":         42.1,
                "churn_risk_high":       12,
                "segments": {
                    "Retail":   83,
                    "SME":      46,
                    "Corporate": 3,
                },
            },
            "alerts": [
                {"level": "high",   "message": "Cash runway below 3 months (2.4 mo)"},
                {"level": "medium", "message": "6 marketing rows: conversions exceed clicks"},
                {"level": "low",    "message": "12 finance rows missing category"},
            ],
        }
    return _get("/api/overview")


# ════════════════════════════════════════════════════════════════
# FINANCE  —  GET /api/finance/*
# ════════════════════════════════════════════════════════════════

def get_finance(period: str = "last_3_months"):
    """All finance KPIs and trend data for the Finance dashboard page."""
    if USE_MOCK:
        return {
            "kpis": {
                "total_revenue":      125400.00,
                "total_expenses":      89200.00,
                "gross_profit":        75240.00,
                "net_profit":          36200.00,
                "profit_margin":           28.9,
                "monthly_burn":        29700.00,
                "cash_in_bank":       210000.00,
                "cash_runway_months":     2.4,
            },
            "monthly_trend": [
                {"month": "Oct 2025", "revenue": 38200, "expenses": 28100, "profit": 10100},
                {"month": "Nov 2025", "revenue": 41500, "expenses": 30200, "profit": 11300},
                {"month": "Dec 2025", "revenue": 45700, "expenses": 30900, "profit": 14800},
            ],
            "expense_breakdown": [
                {"category": "Shipping",  "amount": 24800},
                {"category": "Marketing", "amount": 21400},
                {"category": "Payroll",   "amount": 18600},
                {"category": "Rent",      "amount":  8400},
                {"category": "Utilities", "amount":  5200},
                {"category": "Supplies",  "amount":  4800},
                {"category": "Software",  "amount":  3200},
                {"category": "Sales",     "amount":  2800},
            ],
            "cash_trend": [
                {"date": "2025-10-01", "closing_balance": 230000},
                {"date": "2025-11-01", "closing_balance": 221000},
                {"date": "2025-12-01", "closing_balance": 210000},
            ],
        }
    return _get("/api/finance/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# SALES  —  GET /api/sales/*
# ════════════════════════════════════════════════════════════════

def get_sales(period: str = "last_3_months"):
    """All sales KPIs and trend data for the Sales & Marketing page."""
    if USE_MOCK:
        return {
            "kpis": {
                "total_orders":       1414,
                "returned_orders":      31,
                "avg_order_value":      88.7,
                "total_revenue":    125400.0,
                "conversion_rate":      97.9,
                "return_rate":           2.1,
            },
            "revenue_by_channel": [
                # from your real CSV: website, whatsapp, sales_rep, marketplace
                {"channel": "website",     "revenue": 62400, "orders": 777},
                {"channel": "whatsapp",    "revenue": 28900, "orders": 307},
                {"channel": "sales_rep",   "revenue": 21800, "orders": 220},
                {"channel": "marketplace", "revenue": 12300, "orders": 141},
            ],
            "top_products": [
                {"product_name": "Eco Bottle",        "units_sold": 420, "revenue": 10500},
                {"product_name": "Travel Mug",        "units_sold": 380, "revenue": 12160},
                {"product_name": "Lunch Box",         "units_sold": 290, "revenue":  8120},
                {"product_name": "Bamboo Cutlery Set","units_sold": 210, "revenue":  3780},
            ],
            "monthly_revenue": [
                {"month": "Oct 2025", "revenue": 38200},
                {"month": "Nov 2025", "revenue": 41500},
                {"month": "Dec 2025", "revenue": 45700},
            ],
        }
    return _get("/api/sales/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# MARKETING  —  GET /api/marketing/*
# ════════════════════════════════════════════════════════════════

def get_marketing(period: str = "last_3_months"):
    """All marketing KPIs for the Sales & Marketing page."""
    if USE_MOCK:
        return {
            "kpis": {
                "total_spend":          45200.0,
                "total_attributed":    134000.0,
                "overall_roi":              1.96,
                "total_impressions":     850000,
                "total_clicks":           62400,
                "total_leads":            18200,
                "total_conversions":       4100,
                "ctr":                     7.34,
                "cpa":                    11.02,
            },
            "campaign_performance": [
                {"campaign_name": "Campaign 1", "spend": 12200, "revenue": 48000, "roi": 2.93, "conversions": 1420},
                {"campaign_name": "Campaign 2", "spend": 15800, "revenue": 38000, "roi": 1.41, "conversions": 1180},
                {"campaign_name": "Campaign 3", "spend":  9400, "revenue": 28000, "roi": 1.98, "conversions":  840},
                {"campaign_name": "Campaign 4", "spend":  7800, "revenue": 20000, "roi": 1.56, "conversions":  660},
            ],
            "spend_trend": [
                {"month": "Oct 2025", "spend": 14200, "revenue": 42000},
                {"month": "Nov 2025", "spend": 15400, "revenue": 44000},
                {"month": "Dec 2025", "spend": 15600, "revenue": 48000},
            ],
        }
    return _get("/api/marketing/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# CUSTOMERS  —  GET /api/customers/*
# ════════════════════════════════════════════════════════════════

def get_customers(period: str = "last_3_months"):
    """All customer KPIs for the Customers dashboard page."""
    if USE_MOCK:
        return {
            "kpis": {
                "total_customers":    132,
                "active_customers":    95,
                "repeat_rate":       42.1,
                "churn_rate":        18.2,
                "avg_clv":          2400.0,
                "new_this_period":     18,
            },
            # real segments from your customers_export.csv
            "revenue_by_segment": [
                {"segment": "Retail",    "revenue": 68200, "customers": 83},
                {"segment": "SME",       "revenue": 51400, "customers": 46},
                {"segment": "Corporate", "revenue":  5800, "customers":  3},
            ],
            "top_customers": [
                {"customer_id": 57,  "full_name": "Customer 57",  "total_revenue": 8200, "total_orders": 14, "segment": "SME"},
                {"customer_id": 23,  "full_name": "Customer 23",  "total_revenue": 7100, "total_orders": 11, "segment": "Retail"},
                {"customer_id": 89,  "full_name": "Customer 89",  "total_revenue": 6400, "total_orders":  9, "segment": "SME"},
                {"customer_id": 114, "full_name": "Customer 114", "total_revenue": 5900, "total_orders":  8, "segment": "Retail"},
                {"customer_id": 40,  "full_name": "Customer 40",  "total_revenue": 5200, "total_orders":  7, "segment": "Corporate"},
            ],
            "churn_risk_list": [
                {"customer_id": 12,  "full_name": "Customer 12",  "churn_risk_score": 0.92, "last_order_days_ago": 78},
                {"customer_id": 45,  "full_name": "Customer 45",  "churn_risk_score": 0.87, "last_order_days_ago": 65},
                {"customer_id": 78,  "full_name": "Customer 78",  "churn_risk_score": 0.81, "last_order_days_ago": 61},
            ],
            "growth_trend": [
                {"month": "Oct 2025", "new_customers": 8,  "churned": 3},
                {"month": "Nov 2025", "new_customers": 6,  "churned": 4},
                {"month": "Dec 2025", "new_customers": 4,  "churned": 5},
            ],
        }
    return _get("/api/customers/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# CHAT  —  POST /api/chat
# ════════════════════════════════════════════════════════════════

def ask_question(question: str, company_id: int = 1):
    """Send a natural language question, get back a structured answer."""
    if USE_MOCK:
        return {
            "answer": f"This is a mock answer for: '{question}'. Connect the backend to get real AI responses.",
            "result": {"metric": "net_profit", "value": -18.0, "unit": "percent", "trend": "down"},
            "reason": "Ad spend increased 31% while sales rose only 6%.",
            "evidence": [
                {"source": "transactions",          "detail": "Dec expenses: $30,900 vs Nov: $30,200"},
                {"source": "marketing_performance", "detail": "Campaign 2 spend: $15,800 with 1.41x ROI"},
            ],
            "action": "Review Campaign 2 budget and consider reallocating to Campaign 1 (2.93x ROI).",
            "confidence": 0.87,
            "charts": [],
        }
    return _post("/api/chat", {"question": question, "company_id": company_id})


# ════════════════════════════════════════════════════════════════
# UPLOAD  —  POST /upload/csv
# ════════════════════════════════════════════════════════════════

def upload_csv(file_bytes: bytes, filename: str, domain: str):
    """Upload a CSV file for ETL processing."""
    if USE_MOCK:
        return {
            "job_id":           "mock-job-001",
            "status":           "success",
            "quality_report": {
                "file_name":          filename,
                "domain":             domain,
                "records_received":   1445,
                "records_accepted":   1420,
                "records_rejected":      3,
                "duplicates_found":     22,
                "anomalies_found":       8,
            },
        }
    files   = {"file": (filename, file_bytes, "text/csv")}
    data    = {"domain": domain}
    try:
        res = requests.post(
            f"{API_BASE_URL}/upload/csv",
            headers=_headers(),
            files=files,
            data=data,
            timeout=60
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


def get_upload_history():
    """List past upload jobs."""
    if USE_MOCK:
        return [
            {"job_id": "job-001", "file": "sales_export.csv",     "domain": "sales",     "status": "success",  "records_accepted": 1420, "timestamp": "2025-12-01"},
            {"job_id": "job-002", "file": "customers_export.csv",  "domain": "customers", "status": "success",  "records_accepted":  120, "timestamp": "2025-12-01"},
            {"job_id": "job-003", "file": "finance_export.csv",    "domain": "finance",   "status": "partial",  "records_accepted":  618, "timestamp": "2025-12-01"},
            {"job_id": "job-004", "file": "marketing_export.csv",  "domain": "marketing", "status": "success",  "records_accepted":  683, "timestamp": "2025-12-01"},
            {"job_id": "job-005", "file": "products_export.csv",   "domain": "products",  "status": "success",  "records_accepted":    6, "timestamp": "2025-12-01"},
        ]
    return _get("/upload/history")