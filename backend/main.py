from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from pydantic import BaseModel
import hashlib, io, uuid, pandas as pd
from datetime import datetime

from backend.app.services.db import engine
from backend.app.nlp.text_to_sql import generate_sql, is_safe_sql
from backend.app.services.query_engine import execute_sql
from backend.app.analytics.anomaly_detection import run_all_detectors
from backend.app.semantic.kpis import KPI_DEFINITIONS, map_to_kpi
from backend.app.services.explainer import explain_result, generate_insight, enrich_anomalies_with_explanations
from backend.app.services.insights import get_revenue_insight
from backend.app.services.recommendations import generate_recommendations

app = FastAPI(title="Conversational BI API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ── TOKEN STORE (in-memory; survives for the life of the server process) ──────
_TOKENS: dict = {}        # token -> {user_id, company_id, full_name, role}
_upload_history: list = []


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _scalar(sql: str, params: dict = None) -> float:
    try:
        with engine.connect().execution_options(timeout=8) as conn:
            val = conn.execute(text(sql), params or {}).scalar()
        return float(val) if val is not None else 0.0
    except Exception:
        return 0.0


def _rows(sql: str, params: dict = None) -> list:
    try:
        with engine.connect().execution_options(timeout=8) as conn:
            result = conn.execute(text(sql), params or {})
            cols = list(result.keys())
            return [dict(zip(cols, row)) for row in result.fetchall()]
    except Exception:
        return []


def _period_interval(period: str) -> str:
    return {
        "last_7_days":   "7 days",
        "last_30_days":  "30 days",
        "last_3_months": "3 months",
        "last_6_months": "6 months",
        "all_time":      "100 years",
    }.get(period, "3 months")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_company_id(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    info = _TOKENS.get(token)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid or expired session — please log in again")
    return info["company_id"]


# ─────────────────────────────────────────────────────────────────────────────
# ROOT + STARTUP
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Conversational BI API running"}


@app.on_event("startup")
def _startup():
    pass  # dim_users and dim_companies already exist from ETL


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    company_name: str = "My Company"
    role: str = "manager"
    currency: str = "CAD"


@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT u.user_id, u.full_name, u.role, u.company_id, u.password_hash,
                           COALESCE(c.currency, 'CAD') AS currency
                    FROM dim_users u
                    LEFT JOIN dim_companies c ON c.company_id = u.company_id
                    WHERE u.email = :email LIMIT 1
                """),
                {"email": req.email}
            ).fetchone()
        if not row or row[4] != _hash(req.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = f"tok-{uuid.uuid4().hex}"
        _TOKENS[token] = {"user_id": row[0], "company_id": row[3], "full_name": row[1], "role": row[2]}
        return {"token": token, "user": {"full_name": row[1], "role": row[2], "company_id": row[3], "currency": row[5]}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/register")
def register_user(req: RegisterRequest):
    try:
        with engine.connect() as conn:
            # Check email uniqueness
            existing = conn.execute(
                text("SELECT user_id FROM dim_users WHERE email = :e"), {"e": req.email}
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")

            # Create company — use max+1 since company_id is bigint (no sequence)
            company_id = int(conn.execute(
                text("SELECT COALESCE(MAX(company_id), 0) + 1 FROM dim_companies")
            ).scalar())
            conn.execute(
                text("INSERT INTO dim_companies (company_id, company_name, industry, country, currency, created_at) VALUES (:cid, :name, 'General', 'General', :cur, NOW())"),
                {"cid": company_id, "name": req.company_name, "cur": req.currency.upper()}
            )
            conn.commit()

            # Create user
            user_id = int(conn.execute(
                text("SELECT COALESCE(MAX(user_id), 0) + 1 FROM dim_users")
            ).scalar())
            conn.execute(
                text("""
                    INSERT INTO dim_users (user_id, company_id, full_name, email, role, password_hash, created_at)
                    VALUES (:uid, :cid, :name, :email, :role, :hash, :ts)
                """),
                {"uid": user_id, "cid": company_id, "name": req.full_name,
                 "email": req.email, "role": req.role, "hash": _hash(req.password),
                 "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            )
            conn.commit()

        token = f"tok-{uuid.uuid4().hex}"
        _TOKENS[token] = {"user_id": user_id, "company_id": company_id,
                          "full_name": req.full_name, "role": req.role}
        return {"token": token, "user": {"full_name": req.full_name, "role": req.role,
                                         "company_id": company_id, "currency": req.currency.upper()}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/demo-login")
def demo_login():
    """Return a session token for the read-only demo@wouessi.com account.
    Creates the account on first call if it does not yet exist in the DB."""
    DEMO_EMAIL = "demo@wouessi.com"
    DEMO_NAME  = "Demo User"
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT u.user_id, u.full_name, u.role, u.company_id,
                           COALESCE(c.currency, 'CAD') AS currency
                    FROM dim_users u
                    LEFT JOIN dim_companies c ON c.company_id = u.company_id
                    WHERE u.email = :e LIMIT 1
                """),
                {"e": DEMO_EMAIL}
            ).fetchone()

            if not row:
                company_row = conn.execute(
                    text("SELECT company_id, COALESCE(currency, 'CAD') FROM dim_companies ORDER BY company_id LIMIT 1")
                ).fetchone()
                demo_cid = int(company_row[0]) if company_row else 1
                demo_currency = company_row[1] if company_row else "CAD"

                uid = int(conn.execute(
                    text("SELECT COALESCE(MAX(user_id), 0) + 1 FROM dim_users")
                ).scalar())
                conn.execute(
                    text("""INSERT INTO dim_users
                            (user_id, company_id, full_name, email, role, password_hash, created_at)
                            VALUES (:uid, :cid, :name, :email, :role, :hash, :ts)"""),
                    {"uid": uid, "cid": demo_cid, "name": DEMO_NAME, "email": DEMO_EMAIL,
                     "role": "viewer", "hash": _hash("WouessDemo2024!"),
                     "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                )
                conn.commit()
                user_id, full_name, role, company_id, currency = uid, DEMO_NAME, "viewer", demo_cid, demo_currency
            else:
                user_id, full_name, role, company_id, currency = row[0], row[1], row[2], row[3], row[4]

        token = f"tok-demo-{uuid.uuid4().hex}"
        _TOKENS[token] = {"user_id": user_id, "company_id": company_id,
                          "full_name": full_name, "role": role}
        return {"token": token, "user": {"full_name": full_name, "role": role,
                                         "company_id": company_id, "currency": currency}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT user_id FROM dim_users WHERE email = :email LIMIT 1"),
                {"email": req.email}
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No account found with that email")
            conn.execute(
                text("UPDATE dim_users SET password_hash = :hash WHERE email = :email"),
                {"hash": _hash(req.new_password), "email": req.email}
            )
            conn.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/overview")
def get_overview(company_id: int = Depends(get_company_id)):
    p = {"cid": company_id}

    has_sales = _scalar("SELECT COUNT(*) FROM fact_sales WHERE company_id=:cid", p) > 0
    has_fin   = _scalar("SELECT COUNT(*) FROM fact_expenses WHERE company_id=:cid", p) > 0
    if not has_sales and not has_fin:
        return {"has_data": False}

    revenue      = _scalar("SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid", p)
    expenses     = _scalar("SELECT SUM(amount) FROM fact_expenses WHERE company_id=:cid", p)
    gross_profit = _scalar("SELECT SUM(gross_profit) FROM fact_sales WHERE status='completed' AND company_id=:cid", p)
    net_profit   = revenue - expenses
    profit_margin = round((net_profit / revenue * 100), 1) if revenue else 0

    cash = _scalar("SELECT signed_amount FROM fact_cash_flow WHERE company_id=:cid ORDER BY date DESC LIMIT 1", p)
    monthly_burn = _scalar("""
        SELECT AVG(monthly_total) FROM (
            SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS m, SUM(amount) AS monthly_total
            FROM fact_expenses WHERE company_id=:cid
            GROUP BY m ORDER BY m DESC LIMIT 3
        ) t
    """, p)
    cash_runway = round(cash / monthly_burn, 1) if monthly_burn else 0

    total_orders = _scalar("SELECT COUNT(*) FROM fact_sales WHERE status='completed' AND company_id=:cid", p)
    avg_order    = _scalar("SELECT AVG(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid", p)

    mkt_spend   = _scalar("SELECT SUM(spend) FROM fact_marketing WHERE company_id=:cid", p)
    mkt_revenue = _scalar("SELECT SUM(revenue_attributed) FROM fact_marketing WHERE company_id=:cid", p)
    overall_roi = round((mkt_revenue - mkt_spend) / mkt_spend, 2) if mkt_spend else 0

    active_customers = _scalar("SELECT COUNT(DISTINCT customer_id) FROM fact_sales WHERE status='completed' AND company_id=:cid", p)
    repeat_customers = _scalar("""
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM fact_sales WHERE status='completed' AND company_id=:cid
            GROUP BY customer_id HAVING COUNT(*) > 1
        ) t
    """, p)
    repeat_rate = round(repeat_customers / active_customers * 100, 1) if active_customers else 0
    churn_risk_high = int(_scalar("""
        SELECT COUNT(*) FROM customer_metrics cm
        JOIN dim_customers dc ON cm.customer_id = dc.customer_id
        WHERE dc.company_id=:cid AND cm.churn_risk_score > 0.7
    """, p))

    top_ch = _rows("SELECT channel FROM fact_sales WHERE status='completed' AND company_id=:cid GROUP BY channel ORDER BY SUM(line_total) DESC LIMIT 1", p)
    top_channel = top_ch[0]["channel"] if top_ch else "N/A"

    prev_rev = _scalar("SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= DATE_TRUNC('month', NOW()) - INTERVAL '1 month' AND CAST(order_date AS DATE) < DATE_TRUNC('month', NOW())", p)
    curr_rev = _scalar("SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= DATE_TRUNC('month', NOW())", p)
    revenue_trend = "up" if curr_rev >= prev_rev else "down"

    best_camp = _rows("""
        SELECT dc.campaign_name
        FROM fact_marketing fm
        JOIN dim_campaigns dc ON fm.campaign_id = dc.campaign_id
        WHERE fm.company_id=:cid
        GROUP BY dc.campaign_name
        ORDER BY (SUM(fm.revenue_attributed) - SUM(fm.spend)) / NULLIF(SUM(fm.spend), 0) DESC
        LIMIT 1
    """, p)
    best_campaign = best_camp[0]["campaign_name"] if best_camp else "N/A"

    seg_rows = _rows("SELECT segment, COUNT(*) AS cnt FROM dim_customers WHERE company_id=:cid GROUP BY segment", p)
    segments = {r["segment"]: int(r["cnt"]) for r in seg_rows}

    return {
        "has_data": True,
        "finance": {
            "total_revenue": revenue, "total_expenses": expenses,
            "gross_profit": gross_profit, "net_profit": net_profit,
            "profit_margin": profit_margin, "cash_in_bank": cash,
            "monthly_burn": monthly_burn, "cash_runway_months": cash_runway,
        },
        "sales": {
            "total_orders": int(total_orders), "avg_order_value": round(avg_order, 2),
            "top_channel": top_channel, "revenue_trend": revenue_trend,
        },
        "marketing": {
            "total_spend": mkt_spend, "total_attributed": mkt_revenue,
            "overall_roi": overall_roi, "best_campaign": best_campaign,
        },
        "customers": {
            "active_customers": int(active_customers), "repeat_rate": repeat_rate,
            "churn_risk_high": churn_risk_high, "segments": segments,
        },
        "alerts": [],
        "anomaly_summary": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# FINANCE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/finance/summary")
def get_finance(period: str = Query(default="last_3_months"), company_id: int = Depends(get_company_id)):
    p = {"cid": company_id}

    if _scalar("SELECT COUNT(*) FROM fact_expenses WHERE company_id=:cid", p) == 0:
        return {"has_data": False}

    interval = _period_interval(period)
    revenue      = _scalar(f"SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    expenses     = _scalar(f"SELECT SUM(amount) FROM fact_expenses WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    gross_profit = _scalar(f"SELECT SUM(gross_profit) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    net_profit   = revenue - expenses
    profit_margin = round((net_profit / revenue * 100), 1) if revenue else 0

    cash = _scalar("SELECT signed_amount FROM fact_cash_flow WHERE company_id=:cid ORDER BY date DESC LIMIT 1", p)
    monthly_burn = _scalar("""
        SELECT AVG(monthly_total) FROM (
            SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS m, SUM(amount) AS monthly_total
            FROM fact_expenses WHERE company_id=:cid
            GROUP BY m ORDER BY m DESC LIMIT 3
        ) t
    """, p)
    cash_runway = round(cash / monthly_burn, 1) if monthly_burn else 0

    rev_rows = _rows(f"""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(order_date AS DATE)), 'Mon YYYY') AS month,
               SUM(line_total) AS revenue
        FROM fact_sales WHERE status='completed' AND company_id=:cid
          AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('month', CAST(order_date AS DATE))
        ORDER BY DATE_TRUNC('month', CAST(order_date AS DATE))
    """, p)
    exp_rows = _rows(f"""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(date AS DATE)), 'Mon YYYY') AS month,
               SUM(amount) AS expenses
        FROM fact_expenses WHERE company_id=:cid
          AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('month', CAST(date AS DATE))
    """, p)
    exp_map = {r["month"]: float(r["expenses"]) for r in exp_rows}
    monthly_trend = [
        {"month": r["month"], "revenue": round(float(r["revenue"]), 2),
         "expenses": round(exp_map.get(r["month"], 0), 2),
         "profit": round(float(r["revenue"]) - exp_map.get(r["month"], 0), 2)}
        for r in rev_rows
    ]

    expense_breakdown = _rows(f"""
        SELECT expense_category AS category, SUM(amount) AS amount
        FROM fact_expenses WHERE company_id=:cid
          AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY expense_category ORDER BY amount DESC
    """, p)

    cash_trend = _rows(f"""
        SELECT TO_CHAR(date, 'YYYY-MM-DD') AS date,
               SUM(signed_amount) OVER (ORDER BY date) AS closing_balance
        FROM fact_cash_flow WHERE company_id=:cid
          AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'
        ORDER BY date LIMIT 12
    """, p)

    return {
        "has_data": True,
        "kpis": {
            "total_revenue": revenue, "total_expenses": expenses,
            "gross_profit": gross_profit, "net_profit": net_profit,
            "profit_margin": profit_margin, "monthly_burn": monthly_burn,
            "cash_in_bank": cash, "cash_runway_months": cash_runway,
        },
        "monthly_trend": monthly_trend,
        "expense_breakdown": expense_breakdown,
        "cash_trend": cash_trend,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SALES & MARKETING (combined)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/sales/summary")
def get_sales(period: str = Query(default="last_3_months"), company_id: int = Depends(get_company_id)):
    p = {"cid": company_id}

    if _scalar("SELECT COUNT(*) FROM fact_sales WHERE company_id=:cid", p) == 0:
        return {"has_data": False}

    interval = _period_interval(period)
    total_orders    = _scalar(f"SELECT COUNT(*) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    returned_orders = _scalar(f"SELECT COUNT(*) FROM fact_sales WHERE status='returned' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    avg_order       = _scalar(f"SELECT AVG(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_revenue   = _scalar(f"SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    return_rate     = round(returned_orders / (total_orders + returned_orders) * 100, 1) if total_orders else 0

    revenue_by_channel = _rows(f"""
        SELECT channel, SUM(line_total) AS revenue, COUNT(*) AS orders
        FROM fact_sales WHERE status='completed' AND company_id=:cid
          AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY channel ORDER BY revenue DESC
    """, p)

    top_products = _rows(f"""
        SELECT dp.product_name, SUM(fs.quantity) AS units_sold, SUM(fs.line_total) AS revenue
        FROM fact_sales fs
        JOIN dim_products dp ON fs.product_id = dp.product_id
        WHERE fs.status='completed' AND fs.company_id=:cid
          AND CAST(fs.order_date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY dp.product_name ORDER BY revenue DESC LIMIT 5
    """, p)

    monthly_revenue = _rows(f"""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(order_date AS DATE)), 'Mon YYYY') AS month,
               SUM(line_total) AS revenue
        FROM fact_sales WHERE status='completed' AND company_id=:cid
          AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('month', CAST(order_date AS DATE))
        ORDER BY DATE_TRUNC('month', CAST(order_date AS DATE))
    """, p)

    campaign_performance = _rows("""
        SELECT dc.campaign_name,
               SUM(fm.spend)              AS spend,
               SUM(fm.revenue_attributed) AS revenue,
               CASE WHEN SUM(fm.spend) > 0
                    THEN (SUM(fm.revenue_attributed) - SUM(fm.spend)) / SUM(fm.spend)
                    ELSE 0 END            AS roi,
               SUM(fm.conversions)        AS conversions
        FROM fact_marketing fm
        JOIN dim_campaigns dc ON fm.campaign_id = dc.campaign_id
        WHERE fm.company_id=:cid
        GROUP BY dc.campaign_name ORDER BY revenue DESC
    """, p)

    spend_trend = _rows(f"""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(date AS DATE)), 'Mon YYYY') AS month,
               SUM(spend) AS spend, SUM(revenue_attributed) AS revenue
        FROM fact_marketing WHERE company_id=:cid
          AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('month', CAST(date AS DATE))
        ORDER BY DATE_TRUNC('month', CAST(date AS DATE))
    """, p)

    return {
        "has_data": True,
        "kpis": {
            "total_orders": int(total_orders), "returned_orders": int(returned_orders),
            "avg_order_value": round(avg_order, 2), "total_revenue": total_revenue,
            "return_rate": return_rate,
        },
        "revenue_by_channel": revenue_by_channel,
        "top_products": top_products,
        "monthly_revenue": monthly_revenue,
        "campaign_performance": campaign_performance,
        "spend_trend": spend_trend,
    }


@app.get("/api/marketing/summary")
def get_marketing(period: str = Query(default="last_3_months"), company_id: int = Depends(get_company_id)):
    p = {"cid": company_id}

    if _scalar("SELECT COUNT(*) FROM fact_marketing WHERE company_id=:cid", p) == 0:
        return {"has_data": False}

    interval = _period_interval(period)
    total_spend       = _scalar(f"SELECT SUM(spend) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_attributed  = _scalar(f"SELECT SUM(revenue_attributed) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_impressions = _scalar(f"SELECT SUM(impressions) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_clicks      = _scalar(f"SELECT SUM(clicks) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_leads       = _scalar(f"SELECT SUM(leads) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    total_conversions = _scalar(f"SELECT SUM(conversions) FROM fact_marketing WHERE company_id=:cid AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    overall_roi = round((total_attributed - total_spend) / total_spend, 2) if total_spend else 0
    ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions else 0
    cpa = round(total_spend / total_conversions, 2) if total_conversions else 0

    campaign_performance = _rows("""
        SELECT dc.campaign_name,
               SUM(fm.spend)              AS spend,
               SUM(fm.revenue_attributed) AS revenue,
               CASE WHEN SUM(fm.spend) > 0
                    THEN (SUM(fm.revenue_attributed) - SUM(fm.spend)) / SUM(fm.spend)
                    ELSE 0 END            AS roi,
               SUM(fm.conversions)        AS conversions
        FROM fact_marketing fm
        JOIN dim_campaigns dc ON fm.campaign_id = dc.campaign_id
        WHERE fm.company_id=:cid
        GROUP BY dc.campaign_name ORDER BY revenue DESC
    """, p)

    spend_trend = _rows(f"""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(date AS DATE)), 'Mon YYYY') AS month,
               SUM(spend) AS spend, SUM(revenue_attributed) AS revenue
        FROM fact_marketing WHERE company_id=:cid
          AND CAST(date AS DATE) >= NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('month', CAST(date AS DATE))
        ORDER BY DATE_TRUNC('month', CAST(date AS DATE))
    """, p)

    return {
        "has_data": True,
        "kpis": {
            "total_spend": total_spend, "total_attributed": total_attributed,
            "overall_roi": overall_roi, "total_impressions": int(total_impressions),
            "total_clicks": int(total_clicks), "total_leads": int(total_leads),
            "total_conversions": int(total_conversions), "ctr": ctr, "cpa": cpa,
        },
        "campaign_performance": campaign_performance,
        "spend_trend": spend_trend,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/customers/summary")
def get_customers(period: str = Query(default="last_3_months"), company_id: int = Depends(get_company_id)):
    p = {"cid": company_id}

    if _scalar("SELECT COUNT(*) FROM dim_customers WHERE company_id=:cid", p) == 0:
        return {"has_data": False}

    interval = _period_interval(period)
    total_customers  = _scalar("SELECT COUNT(*) FROM dim_customers WHERE company_id=:cid", p)
    active_customers = _scalar(f"SELECT COUNT(DISTINCT customer_id) FROM fact_sales WHERE status='completed' AND company_id=:cid AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'", p)
    repeat_customers = _scalar(f"""
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM fact_sales WHERE status='completed' AND company_id=:cid
              AND CAST(order_date AS DATE) >= NOW() - INTERVAL '{interval}'
            GROUP BY customer_id HAVING COUNT(*) > 1
        ) t
    """, p)
    repeat_rate = round(repeat_customers / active_customers * 100, 1) if active_customers else 0

    avg_clv = _scalar("""
        SELECT AVG(cm.total_revenue) FROM customer_metrics cm
        JOIN dim_customers dc ON cm.customer_id = dc.customer_id
        WHERE dc.company_id=:cid
    """, p)
    churn_rate = round(_scalar("""
        SELECT AVG(cm.churn_risk_score) FROM customer_metrics cm
        JOIN dim_customers dc ON cm.customer_id = dc.customer_id
        WHERE dc.company_id=:cid
    """, p) * 100, 1)
    new_this_period = int(_scalar(f"""
        SELECT COUNT(*) FROM dim_customers WHERE company_id=:cid
          AND CAST(created_at AS DATE) >= NOW() - INTERVAL '{interval}'
    """, p))

    revenue_by_segment = _rows("""
        SELECT dc.segment, SUM(fs.line_total) AS revenue, COUNT(DISTINCT fs.customer_id) AS customers
        FROM fact_sales fs
        JOIN dim_customers dc ON fs.customer_id = dc.customer_id
        WHERE fs.status='completed' AND fs.company_id=:cid
        GROUP BY dc.segment ORDER BY revenue DESC
    """, p)

    top_customers = _rows("""
        SELECT dc.customer_id, dc.full_name,
               SUM(fs.line_total) AS total_revenue,
               COUNT(fs.order_id) AS total_orders,
               dc.segment
        FROM fact_sales fs
        JOIN dim_customers dc ON fs.customer_id = dc.customer_id
        WHERE fs.status='completed' AND fs.company_id=:cid
        GROUP BY dc.customer_id, dc.full_name, dc.segment
        ORDER BY total_revenue DESC LIMIT 5
    """, p)

    churn_risk_list = _rows("""
        SELECT dc.customer_id, dc.full_name,
               cm.churn_risk_score,
               EXTRACT(DAY FROM NOW() - MAX(fs.order_date))::int AS last_order_days_ago
        FROM dim_customers dc
        JOIN fact_sales fs ON fs.customer_id = dc.customer_id
        LEFT JOIN customer_metrics cm ON cm.customer_id = dc.customer_id
        WHERE dc.company_id=:cid
        GROUP BY dc.customer_id, dc.full_name, cm.churn_risk_score
        HAVING cm.churn_risk_score > 0.7
        ORDER BY cm.churn_risk_score DESC LIMIT 5
    """, p)

    growth_trend = _rows("""
        SELECT TO_CHAR(DATE_TRUNC('month', CAST(created_at AS DATE)), 'Mon YYYY') AS month,
               COUNT(*) AS new_customers, 0 AS churned
        FROM dim_customers WHERE company_id=:cid
        GROUP BY DATE_TRUNC('month', CAST(created_at AS DATE))
        ORDER BY DATE_TRUNC('month', CAST(created_at AS DATE)) LIMIT 6
    """, p)

    return {
        "has_data": True,
        "kpis": {
            "total_customers":  int(total_customers),
            "active_customers": int(active_customers),
            "repeat_rate":      repeat_rate,
            "churn_rate":       churn_rate,
            "avg_clv":          round(avg_clv, 2),
            "new_this_period":  new_this_period,
        },
        "revenue_by_segment": revenue_by_segment,
        "top_customers":      top_customers,
        "churn_risk_list":    churn_risk_list,
        "growth_trend":       growth_trend,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANOMALIES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/anomalies")
def get_anomalies(company_id: int = Depends(get_company_id)):
    result = run_all_detectors(company_id=company_id)
    enriched = enrich_anomalies_with_explanations(result.get("anomalies", []))
    result["anomalies"] = enriched
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
def api_chat(req: ChatRequest, company_id: int = Depends(get_company_id)):
    user_query = req.question

    if "revenue insight" in user_query.lower():
        return get_revenue_insight()

    if "anomaly" in user_query.lower() or "anomalies" in user_query.lower():
        try:
            result = run_all_detectors(company_id=company_id)
            enriched = enrich_anomalies_with_explanations(result.get("anomalies", []))
            return {
                "answer": f"{result['summary']['total']} anomalies detected.",
                "anomalies": enriched,
                "confidence": 0.95,
            }
        except Exception as e:
            return {"answer": f"Could not fetch anomalies: {e}", "confidence": 0.0}

    kpi = map_to_kpi(user_query)
    sql = KPI_DEFINITIONS[kpi]["sql"] if kpi else generate_sql(user_query)

    if not is_safe_sql(sql):
        return {"answer": "That query cannot be executed safely.", "confidence": 0.0}

    try:
        result = execute_sql(sql)
    except Exception as e:
        return {"answer": f"Query failed: {e}", "sql": sql, "confidence": 0.0}

    explanation = explain_result(user_query, result)
    insight = generate_insight(user_query, explanation, result=result, sql=sql)
    return {
        "answer":     explanation,
        "sql":        sql,
        "result":     result,
        "reason":     insight["reason"],
        "evidence":   insight["evidence"],
        "action":     insight["action"],
        "confidence": 0.85,
    }


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

_DOMAIN_TABLE_MAP = {
    "sales":     "fact_sales",
    "customers": "dim_customers",
    "products":  "dim_products",
    "marketing": "fact_marketing",
    "finance":   "fact_expenses",
}

_REQUIRED_COLS = {
    "sales":     {"order_date", "channel", "status", "line_total"},
    "customers": {"full_name", "segment"},
    "products":  {"product_name", "price", "cost"},
    "marketing": {"date", "spend", "revenue_attributed"},
    "finance":   {"date", "expense_category", "amount"},
}


def _detect_domain(cols: list) -> str:
    col_set = set(c.lower() for c in cols)
    scores = {domain: len(required & col_set) for domain, required in _REQUIRED_COLS.items()}
    return max(scores, key=scores.get)


@app.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    domain: str = Form(default="auto"),
    company_id: int = Depends(get_company_id),
):
    job_id = str(uuid.uuid4())[:8]
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    records_received = len(df)
    duplicates_found = int(df.duplicated().sum())
    df = df.drop_duplicates()

    if domain == "auto":
        domain = _detect_domain(df.columns.tolist())

    required = _REQUIRED_COLS.get(domain, set())
    col_set  = set(c.lower() for c in df.columns)
    missing  = required - col_set
    if missing:
        raise HTTPException(status_code=422,
            detail=f"Missing required columns for domain '{domain}': {missing}")

    req_present = [c for c in df.columns if c.lower() in required]
    df = df.dropna(subset=req_present)
    records_rejected = records_received - len(df)
    anomalies_found  = int((df.select_dtypes(include="number") < 0).any(axis=1).sum())

    # Tag every row with this company's ID
    df["company_id"] = company_id

    table = _DOMAIN_TABLE_MAP.get(domain, domain)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table} WHERE company_id = :cid"), {"cid": company_id})
            conn.commit()
        df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=500)
    except Exception:
        # Table may not exist yet — create it via append
        df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=500)

    records_accepted = len(df)
    job = {
        "job_id":           job_id,
        "file":             file.filename,
        "domain":           domain,
        "company_id":       company_id,
        "status":           "success" if records_rejected == 0 else "partial",
        "records_accepted": records_accepted,
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "quality_report": {
            "records_received": records_received,
            "records_accepted": records_accepted,
            "records_rejected": records_rejected,
            "duplicates_found": duplicates_found,
            "anomalies_found":  anomalies_found,
        },
    }
    _upload_history.insert(0, job)
    return job


@app.get("/upload/history")
def get_upload_history(company_id: int = Depends(get_company_id)):
    return [j for j in _upload_history if j.get("company_id") == company_id][:20]


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/revenue")
def get_revenue():
    return {"revenue": _scalar("SELECT SUM(line_total) FROM fact_sales WHERE status='completed'")}


@app.get("/top-products")
def top_products():
    return _rows("""
        SELECT dp.product_name, SUM(fs.line_total) AS revenue
        FROM fact_sales fs
        JOIN dim_products dp ON fs.product_id = dp.product_id
        WHERE fs.status = 'completed'
        GROUP BY dp.product_name ORDER BY revenue DESC LIMIT 5
    """)


@app.post("/recommendations")
def get_recommendations_endpoint(anomalies: list):
    return generate_recommendations(anomalies)


@app.post("/query")
def query(user_query: str = Query(...)):
    kpi = map_to_kpi(user_query)
    sql = KPI_DEFINITIONS[kpi]["sql"] if kpi else generate_sql(user_query)

    if not is_safe_sql(sql):
        return {"error": "Unsafe query"}

    try:
        result = execute_sql(sql)
    except Exception as e:
        return {"query": user_query, "sql": sql, "error": str(e)}

    return {
        "query": user_query, "sql": sql, "result": result,
        "explanation": explain_result(user_query, result),
    }
