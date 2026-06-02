"""
api_client.py — All HTTP calls to Affan's FastAPI backend.
Set USE_MOCK = False in config.py when backend is ready.
"""

import requests
import streamlit as st
from config import API_BASE_URL, USE_MOCK

# ── HELPER ────────────────────────────────────────────────────────
def _headers():
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"}

def _get(endpoint, params=None):
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", headers=_headers(), params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e}")
        return None

def _post(endpoint, payload):
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", headers=_headers(), json=payload, timeout=30)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════

def login(email: str, password: str):
    """Returns {token, user} or None."""
    if USE_MOCK:
        # Mock: accept any non-empty credentials
        if email and password:
            return {
                "token": "mock-jwt-token-abc123",
                "user":  {"full_name": email.split("@")[0].title(), "role": "manager"}
            }
        return None
    return _post("/auth/login", {"email": email, "password": password})


def register(full_name: str, email: str, password: str, company_name: str = "My Company", currency: str = "CAD"):
    """Returns {token, user} or None."""
    if USE_MOCK:
        if full_name and email and password:
            return {
                "token": "mock-jwt-token-abc123",
                "user":  {"full_name": full_name, "role": "manager", "currency": currency}
            }
        return None
    return _post("/auth/register", {
        "full_name":    full_name,
        "email":        email,
        "password":     password,
        "company_name": company_name,
        "currency":     currency,
        "role":         "manager"
    })


def reset_password(email: str, new_password: str):
    """Returns {success: True} or None. None means email not found."""
    if USE_MOCK:
        return {"success": True}
    try:
        res = requests.post(f"{API_BASE_URL}/auth/reset-password",
                            json={"email": email, "new_password": new_password}, timeout=10)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e}")
        return None


def demo_login():
    """Log in as the pre-seeded demo@wouessi.com account. Returns {token, user} or None."""
    if USE_MOCK:
        return {
            "token": "mock-demo-token-xyz",
            "user":  {"full_name": "Demo User", "role": "viewer", "company_id": 1}
        }
    return _post("/auth/demo-login", {})


# ════════════════════════════════════════════════════════════════
# OVERVIEW
# ════════════════════════════════════════════════════════════════

def get_overview():
    if USE_MOCK:
        return {
            "finance": {
                "total_revenue": 125400.00, "total_expenses": 89200.00,
                "net_profit": 36200.00, "profit_margin": 28.9,
                "cash_in_bank": 210000.00, "monthly_burn": 29700.00,
                "cash_runway_months": 2.4,
            },
            "sales": {
                "total_orders": 1414, "avg_order_value": 88.7,
                "top_channel": "website", "revenue_trend": "up_6_percent",
            },
            "marketing": {
                "total_spend": 45200.00, "total_attributed": 134000.00,
                "overall_roi": 1.96, "best_campaign": "Campaign 1",
            },
            "customers": {
                "active_customers": 95, "repeat_rate": 42.1,
                "churn_risk_high": 12,
                "segments": {"Retail": 83, "SME": 46, "Corporate": 3},
            },
            "alerts": [
                {"level": "high",   "message": "Cash runway below 3 months (2.4 mo)"},
                {"level": "medium", "message": "6 marketing rows: conversions exceed clicks"},
                {"level": "low",    "message": "12 finance rows missing category"},
            ],
            "anomaly_summary": {"total": 3, "high": 1, "medium": 2, "low": 0},
        }
    return _get("/api/overview")


# ════════════════════════════════════════════════════════════════
# FINANCE
# ════════════════════════════════════════════════════════════════

def get_finance(period="last_3_months"):
    if USE_MOCK:
        return {
            "kpis": {
                "total_revenue": 125400.00, "total_expenses": 89200.00,
                "gross_profit": 75240.00,   "net_profit": 36200.00,
                "profit_margin": 28.9,      "monthly_burn": 29700.00,
                "cash_in_bank": 210000.00,  "cash_runway_months": 2.4,
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
# SALES
# ════════════════════════════════════════════════════════════════

def get_sales(period="last_3_months"):
    if USE_MOCK:
        return {
            "kpis": {
                "total_orders": 1414, "returned_orders": 31,
                "avg_order_value": 88.7, "total_revenue": 125400.0,
                "conversion_rate": 97.9, "return_rate": 2.1,
            },
            "revenue_by_channel": [
                {"channel": "website",     "revenue": 62400, "orders": 777},
                {"channel": "whatsapp",    "revenue": 28900, "orders": 307},
                {"channel": "sales_rep",   "revenue": 21800, "orders": 220},
                {"channel": "marketplace", "revenue": 12300, "orders": 141},
            ],
            "top_products": [
                {"product_name": "Eco Bottle",         "units_sold": 420, "revenue": 10500},
                {"product_name": "Travel Mug",         "units_sold": 380, "revenue": 12160},
                {"product_name": "Lunch Box",          "units_sold": 290, "revenue":  8120},
                {"product_name": "Bamboo Cutlery Set", "units_sold": 210, "revenue":  3780},
            ],
            "monthly_revenue": [
                {"month": "Oct 2025", "revenue": 38200},
                {"month": "Nov 2025", "revenue": 41500},
                {"month": "Dec 2025", "revenue": 45700},
            ],
        }
    return _get("/api/sales/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# MARKETING
# ════════════════════════════════════════════════════════════════

def get_marketing(period="last_3_months"):
    if USE_MOCK:
        return {
            "kpis": {
                "total_spend": 45200.0, "total_attributed": 134000.0,
                "overall_roi": 1.96,    "total_impressions": 850000,
                "total_clicks": 62400,  "total_leads": 18200,
                "total_conversions": 4100, "ctr": 7.34, "cpa": 11.02,
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
# CUSTOMERS
# ════════════════════════════════════════════════════════════════

def get_customers(period="last_3_months"):
    if USE_MOCK:
        return {
            "kpis": {
                "total_customers": 132, "active_customers": 95,
                "repeat_rate": 42.1,    "churn_rate": 18.2,
                "avg_clv": 2400.0,      "new_this_period": 18,
            },
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
                {"customer_id": 12, "full_name": "Customer 12", "churn_risk_score": 0.92, "last_order_days_ago": 78},
                {"customer_id": 45, "full_name": "Customer 45", "churn_risk_score": 0.87, "last_order_days_ago": 65},
                {"customer_id": 78, "full_name": "Customer 78", "churn_risk_score": 0.81, "last_order_days_ago": 61},
            ],
            "growth_trend": [
                {"month": "Oct 2025", "new_customers": 8,  "churned": 3},
                {"month": "Nov 2025", "new_customers": 6,  "churned": 4},
                {"month": "Dec 2025", "new_customers": 4,  "churned": 5},
            ],
        }
    return _get("/api/customers/summary", {"period": period})


# ════════════════════════════════════════════════════════════════
# CHAT
# ════════════════════════════════════════════════════════════════

def ask_question(question: str):
    if USE_MOCK:
        return {
            "answer":     f"Mock answer for: '{question}'. Connect backend for real AI responses.",
            "result":     {"metric": "net_profit", "value": -18.0, "unit": "percent", "trend": "down"},
            "reason":     "Ad spend increased 31% while sales rose only 6%.",
            "evidence":   [
                {"source": "transactions",          "detail": "Dec expenses: $30,900 vs Nov: $30,200"},
                {"source": "marketing_performance", "detail": "Campaign 2: $15,800 with 1.41x ROI"},
            ],
            "action":     "Review Campaign 2 and reallocate to Campaign 1 (2.93x ROI).",
            "confidence": 0.87,
            "charts":     [],
        }
    return _post("/api/chat", {"question": question})


# ════════════════════════════════════════════════════════════════
# ANOMALIES & RECOMMENDATIONS
# ════════════════════════════════════════════════════════════════

def get_anomalies():
    if USE_MOCK:
        return {
            "summary": {"total": 3, "high": 1, "medium": 2, "low": 0},
            "anomalies": [
                {
                    "domain": "sales", "type": "daily_revenue_drop", "severity": "high",
                    "message": "Daily Revenue drop of 42.3% on 2025-12-14",
                    "date": "2025-12-14", "value": 1204.0, "expected": 2088.5,
                    "deviation_pct": -42.3, "z_score": 3.12, "method": "zscore", "unit": "$",
                    "recommendation": "Investigate sales trends, campaigns, or seasonality changes.",
                    "explanation": (
                        "On 2025-12-14, your daily sales dropped 42% below the usual level "
                        "($1,204 vs $2,089 typical). This is a significant one-day dip — "
                        "check whether an outage, holiday effect, or channel issue caused the shortfall."
                    ),
                    "shap_top_features": None,
                },
                {
                    "domain": "marketing", "type": "pattern_anomaly", "severity": "medium",
                    "message": "Unusual marketing activity on 2025-11-22",
                    "date": "2025-11-22", "value": 9800.0, "expected": None,
                    "deviation_pct": None, "z_score": None, "method": "isolation_forest", "unit": "$",
                    "recommendation": "Review campaign performance and targeting.",
                    "explanation": (
                        "On 2025-11-22, an unusual combination of spend, conversions, and attributed "
                        "revenue was detected. This anomaly was mainly driven by: advertising spend "
                        "was unusually high ($9,800); number of conversions was unusually low (12); "
                        "revenue from campaigns was unusually low ($4,200)."
                    ),
                    "shap_top_features": [["spend", -0.42], ["conversions", -0.31], ["revenue_attributed", -0.18]],
                    "feature_values": {"spend": 9800.0, "conversions": 12.0, "revenue_attributed": 4200.0},
                    "feature_means":  {"spend": 4200.0, "conversions": 38.5, "revenue_attributed": 11800.0},
                },
                {
                    "domain": "finance", "type": "cashflow_change_drop", "severity": "medium",
                    "message": "Cashflow Change drop of 38.1% on 2025-12-01",
                    "date": "2025-12-01", "value": -18200.0, "expected": -11200.5,
                    "deviation_pct": -38.1, "z_score": 2.4, "method": "zscore", "unit": "$",
                    "recommendation": "Monitor liquidity and upcoming liabilities.",
                    "explanation": (
                        "On 2025-12-01, your cash balance fell further than usual "
                        "($18,200 outflow vs a normal $11,200). This may indicate a large "
                        "unexpected payment going out — review your accounts payable for that date."
                    ),
                    "shap_top_features": None,
                },
            ],
        }
    return _get("/api/anomalies")


def get_recommendations(anomalies: list):
    if USE_MOCK:
        return [
            {
                "type": "data_quality",
                "confidence": 0.95,
                "recommendation": (
                    "Data quality issues were found in your marketing records — rows where conversions "
                    "exceed clicks are mathematically impossible and indicate a tracking or import error. "
                    "Export the affected rows, identify the source of the discrepancy (often a "
                    "double-count in your CRM or ad platform), and correct the data before using it "
                    "for campaign decisions."
                ),
            },
            {
                "type": "revenue_drop",
                "confidence": 0.88,
                "recommendation": (
                    "Revenue is declining — compare this period's figures by channel and product "
                    "against last quarter to pinpoint exactly where the drop is occurring. "
                    "Once you identify the underperforming segment, check whether the cause is "
                    "lower volume, lower prices, or higher returns, as each requires a different fix."
                ),
            },
            {
                "type": "cashflow",
                "confidence": 0.82,
                "recommendation": (
                    "Cash flow volatility has been detected — calculate your current runway by "
                    "dividing your cash balance by your average monthly burn rate to understand "
                    "how much time you have. If runway is below three months, immediately contact "
                    "your top customers with outstanding invoices and offer an early-payment discount."
                ),
            },
        ]
    if not anomalies:
        return []
    return _post("/recommendations", anomalies)


# ════════════════════════════════════════════════════════════════
# UPLOAD
# ════════════════════════════════════════════════════════════════

def upload_csv(file_bytes, filename, domain):
    if USE_MOCK:
        return {
            "job_id": "mock-job-001", "status": "success",
            "quality_report": {
                "file_name": filename, "domain": domain,
                "records_received": 1445, "records_accepted": 1420,
                "records_rejected": 3,    "duplicates_found": 22,
                "anomalies_found": 8,
            },
        }
    files = {"file": (filename, file_bytes, "text/csv")}
    try:
        res = requests.post(f"{API_BASE_URL}/upload/csv", headers=_headers(),
                            files=files, data={"domain": domain}, timeout=60)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


def get_upload_history():
    if USE_MOCK:
        return [
            {"job_id": "job-001", "file": "sales_export.csv",    "domain": "sales",     "status": "success", "records_accepted": 1420, "timestamp": "2025-12-01"},
            {"job_id": "job-002", "file": "customers_export.csv","domain": "customers", "status": "success", "records_accepted":  120, "timestamp": "2025-12-01"},
            {"job_id": "job-003", "file": "finance_export.csv",  "domain": "finance",   "status": "partial", "records_accepted":  618, "timestamp": "2025-12-01"},
            {"job_id": "job-004", "file": "marketing_export.csv","domain": "marketing", "status": "success", "records_accepted":  683, "timestamp": "2025-12-01"},
            {"job_id": "job-005", "file": "products_export.csv", "domain": "products",  "status": "success", "records_accepted":    6, "timestamp": "2025-12-01"},
        ]
    return _get("/upload/history")
