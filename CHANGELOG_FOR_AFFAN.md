# BI Dashboard — Technical Changes & Implementation Notes
**For:** Affan  
**From:** Mayank  
**Date:** May 2026  
**Branch:** `feature/explainability`

---

## Overview

This document covers all changes made to the codebase across the backend, frontend, database, and AI/NLP layer. Changes are grouped by feature/functionality.

---

## 1. Database Connection Fix

**File:** `src/data_pipeline/load.py` (line 35)

**Problem:** The ETL pipeline had a hardcoded password `1234` that didn't match the actual PostgreSQL password.

**Fix:** Changed to read from environment variable.

```python
# Before
self.db_url = "postgresql://postgres:1234@localhost:5432/bi_dashboard"

# After
self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/bi_dashboard")
```

**Also:** The password `Mayank1717@@` must be URL-encoded in `.env` because `@` is a special character in connection strings:
```
DATABASE_URL=postgresql://postgres:Mayank1717%40%40@localhost:5432/bi_dashboard
```

---

## 2. Groq API Integration (Replacing Ollama)

**Files:** `backend/app/nlp/text_to_sql.py`, `backend/app/services/explainer.py`

**Problem:** The system used Ollama (a local LLM) for SQL generation and anomaly explanations. Ollama cannot be deployed to clients — it requires a local GPU installation.

**Solution:** Replaced Ollama with Groq API (free tier, 14,400 requests/day), which uses `llama-3.1-8b-instant` via an OpenAI-compatible endpoint.

### `text_to_sql.py`
- Replaced `_call_ollama()` with `_call_groq()` using `https://api.groq.com/openai/v1/chat/completions`
- Fixed the schema description passed to the LLM — removed fake columns (`roi`, `roas`) from `fact_marketing` that don't exist in the database
- Added explicit note: *"there is NO roi or roas column; compute as `(revenue_attributed - spend) / NULLIF(spend, 0)`"*
- Added notes that `fact_marketing.date`, `fact_expenses.date`, `dim_customers.created_at` are all **TEXT type** and require `CAST(date AS DATE)` for date functions

```python
# Key constants
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL   = "llama-3.1-8b-instant"
```

### `explainer.py`
- Renamed `_call_ollama()` → `_call_groq()` with same Groq endpoint
- Rewrote `explain_result()` to generate real summaries from actual SQL result rows/columns instead of returning a generic static message
- All anomaly explanations call Groq, with a rule-based `_template_explanation()` fallback if the API is unavailable

---

## 3. Semantic Layer Expansion

**Files:** `backend/app/semantic/kpis.py`, `notebooks/semantic_layer.json`

**Problem:** The semantic layer only had 6 pre-written KPI queries. Any question outside those 6 went to Groq, which often generated SQL with wrong column names (e.g., `customer_segment` instead of `segment`, `roi` which doesn't exist).

**Solution:** Expanded to 13 KPIs with pre-written, tested SQL. This means most common business questions hit the semantic layer directly and never call Groq.

**New KPIs added to `semantic_layer.json`:**

| KPI Key | Description | SQL Approach |
|---|---|---|
| `revenue_by_segment` | Revenue by customer segment (Retail/SME/Corporate) | JOIN `fact_sales` → `dim_customers` on `segment` |
| `revenue_by_channel` | Revenue by sales channel | GROUP BY `channel` on `fact_sales` |
| `revenue_by_city` | Revenue by city | JOIN `fact_sales` → `dim_customers` on `city` |
| `expense_breakdown` | Expenses by category | GROUP BY `expense_category` on `fact_expenses` |
| `top_customers` | Top 10 customers by revenue | JOIN `fact_sales` → `dim_customers` |
| `orders_by_city` | Order count per city | JOIN `fact_sales` → `dim_customers` |
| `cash_runway` | Fixed | Changed `DATE_TRUNC('month', date)` → `DATE_TRUNC('month', CAST(date AS DATE))` |

**Synonym map expanded in `kpis.py`:**
```python
"revenue_by_segment": ["segment", "spends the most", "which segment", "retail", "sme", "corporate"],
"revenue_by_channel": ["by channel", "channel revenue", "which channel"],
"revenue_by_city":    ["by city", "city revenue", "which city", "cities"],
"expense_breakdown":  ["expense breakdown", "where are we spending", "cost breakdown"],
"top_customers":      ["top customer", "best customer", "highest spending"],
"orders_by_city":     ["orders from each city", "orders by city", "how many orders from"],
```

---

## 4. Backend API Fixes — Per-Endpoint

**File:** `backend/main.py`

### 4a. `GET /api/overview`
- Added missing fields to response: `top_channel`, `revenue_trend`, `best_campaign`, `repeat_rate`, `churn_risk_high`, `segments`
- These were causing `KeyError` on the Overview frontend page

### 4b. `GET /api/finance/summary`
- Fixed `monthly_trend`: `INTERVAL :interval` cannot be parameterized in PostgreSQL — switched to f-string with a whitelist of allowed values
- Fixed `CAST(date AS DATE)` for `fact_expenses.date` which is stored as TEXT
- Rewrote monthly trend by running two separate queries (revenue + expenses) and merging in Python, avoiding complex SQL JOIN issues

### 4c. `GET /api/sales/summary`
- Fixed `INTERVAL '{interval}'` (same f-string fix as finance)
- Added `campaign_performance` and `spend_trend` to response (were missing, causing frontend errors)

### 4d. `GET /api/marketing/summary`
- Removed `AVG(fm.roi)` — `roi` column does not exist in `fact_marketing`
- Replaced with computed ROI:
```sql
CASE WHEN SUM(spend) > 0
     THEN (SUM(revenue_attributed) - SUM(spend)) / SUM(spend)
     ELSE 0 END AS roi
```
- Fixed `CAST(date AS DATE)` for `fact_marketing.date` (TEXT type)

### 4e. `GET /api/customers/summary`
- Added missing KPI fields: `churn_rate`, `avg_clv`, `new_this_period`
- Fixed `CAST(created_at AS DATE)` for `dim_customers.created_at` (TEXT type)
- Added `0 AS churned` to `growth_trend` query (missing column caused frontend crash)

---

## 5. Multi-Tenant SaaS Authentication

**File:** `backend/main.py`, `frontend/pages/login.py`, `frontend/pages/register.py`, `frontend/app.py`

**Problem:** The original auth was fake — login accepted any credentials regardless of password, and register always returned success even if the email was already taken. Everyone was assigned `company_id = 1` (the demo company).

**Solution:** Implemented proper multi-tenant authentication.

### Token System
An in-memory dictionary maps each session token to a company:
```python
_TOKENS: dict = {}  # token -> {user_id, company_id, full_name, role}
```

### Auth Dependency
All protected endpoints use a FastAPI `Depends()` to extract `company_id` from the Bearer token:
```python
def get_company_id(authorization: str = Header(None)) -> int:
    token = authorization.split(" ", 1)[1]
    info = _TOKENS.get(token)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return info["company_id"]
```

### `POST /auth/register`
- Checks `dim_users` for duplicate email — returns `400` if already registered
- Creates a new row in `dim_companies` (auto-increments `company_id` via `MAX + 1`)
- Creates a new row in `dim_users` with SHA-256 hashed password
- Returns a real UUID token and the new `company_id`

> **Note:** Tables are `dim_users` and `dim_companies` (star schema naming), not `users`/`companies`.

### `POST /auth/login`
- Fetches user from `dim_users` by email
- Compares SHA-256 hash of entered password against stored hash
- Returns `401` if email not found or password wrong
- Returns real UUID token on success

### Frontend Changes
- **`register.py`:** After successful registration, redirects to **Upload page** (not Overview) with message "Upload your data to get started"
- **`login.py`:** Stores `company_id` from response into `st.session_state`
- **`app.py`:** Added `company_id` to session state defaults; clears it on logout/home

---

## 6. Per-Company Data Isolation

**File:** `backend/main.py` (all GET endpoints)

**Problem:** All SQL queries showed data for all companies combined. In a SaaS context, each customer must only see their own data.

**Solution:** Every query now filters by `company_id` from the authenticated token.

```python
# Example — before
revenue = _scalar("SELECT SUM(line_total) FROM fact_sales WHERE status='completed'")

# After
revenue = _scalar(
    "SELECT SUM(line_total) FROM fact_sales WHERE status='completed' AND company_id=:cid",
    {"cid": company_id}
)
```

This was applied to all queries across: `get_overview`, `get_finance`, `get_sales`, `get_marketing`, `get_customers`.

### `has_data` Flag
Each endpoint now checks whether the company has uploaded any data. If not, it returns `{"has_data": False}` instead of showing zeros:
```python
if _scalar("SELECT COUNT(*) FROM fact_sales WHERE company_id=:cid", p) == 0:
    return {"has_data": False}
```

---

## 7. Database Schema Fix — Missing `company_id` Columns

**Problem:** `fact_sales` and `fact_marketing` did not have a `company_id` column. All other tables (`fact_expenses`, `fact_cash_flow`, `dim_customers`, `dim_products`) already had it.

**Fix:** Added the column via `ALTER TABLE` and set all existing rows to `company_id = 1` (the original Northstar demo company):

```sql
ALTER TABLE fact_sales ADD COLUMN IF NOT EXISTS company_id BIGINT DEFAULT 1;
UPDATE fact_sales SET company_id = 1 WHERE company_id IS NULL;

ALTER TABLE fact_marketing ADD COLUMN IF NOT EXISTS company_id BIGINT DEFAULT 1;
UPDATE fact_marketing SET company_id = 1 WHERE company_id IS NULL;
```

---

## 8. CSV Upload — Per-Company

**File:** `backend/main.py` — `POST /upload/csv`

**Problem:** Upload was using `if_exists="replace"` which dropped and recreated the entire table, destroying all other companies' data. It also hardcoded `company_id = 1`.

**Solution:**
1. Upload endpoint now uses `Depends(get_company_id)` — company_id comes from the token
2. Tags every uploaded row with the authenticated company's ID: `df["company_id"] = company_id`
3. Deletes only that company's existing rows before inserting: 
```python
conn.execute(text(f"DELETE FROM {table} WHERE company_id = :cid"), {"cid": company_id})
df.to_sql(table, engine, if_exists="append", ...)
```
4. Upload history filtered per company: `GET /upload/history` returns only that company's uploads

---

## 9. Frontend — Conditional Dashboard Pages

**Files:** `frontend/pages/p01_overview.py`, `p03_finance.py`, `p04_sales.py`, `p05_customers.py`

**Problem:** Pages crashed or showed zeros when a new company hadn't uploaded data yet.

**Solution:** Each page checks `has_data` from the API response. If `False`, shows an upload prompt instead of the dashboard:

```python
if data.get("has_data") is False:
    st.info("📁 No data uploaded yet. Upload your CSV files to see this dashboard.")
    if st.button("Go to Upload →"):
        st.session_state.page = "upload"
        st.rerun()
    return
```

This means:
- Upload **sales CSV** → Sales & Marketing page unlocks
- Upload **finance CSV** → Finance page unlocks
- Upload **customers CSV** → Customers page unlocks
- Upload nothing → all pages show the upload prompt

---

## 10. Frontend — Chat Page Fix

**File:** `frontend/pages/p02_chat.py`

**Problem:** Chat always showed *"Result generated successfully from the semantic warehouse."* regardless of the actual data returned.

**Fix:** Rewrote `explain_result()` in `explainer.py` to:
- Parse actual rows and columns from the SQL result
- Generate context-aware intros ("Your best customer is...", "Top campaign...")
- Show a `st.dataframe()` when the result has multiple rows

---

## 11. Frontend — Landing Page (Anusha's Updates)

**Files:** `frontend/pages/landing.py`, `frontend/app.py`, `frontend/pages/register.py`

Pulled Anusha's updated frontend from `origin/main` into the `feature/explainability` branch:

- `landing.py` — Wouessi branding (purple/blue `#2D00C8` theme, Wouessi logo as embedded base64 image, replaces "BI DASH" lime-green theme)
- `app.py` — Sidebar uses Wouessi logo instead of text
- `register.py` — Updated styling to match Wouessi design

---

## 12. Demo Data

**Directory:** `data/demo/`

Generated 7 demo CSV files for a fictional electronics company ("Horizon Tech") to demonstrate the upload feature to clients. Files follow the exact column schema required by each domain:

| File | Domain | Uploads to Table |
|---|---|---|
| `order_items.csv` | sales | `fact_sales` |
| `customers.csv` | customers | `dim_customers` |
| `products.csv` | products | `dim_products` |
| `marketing_performance.csv` | marketing | `fact_marketing` |
| `expenses.csv` | finance | `fact_expenses` |
| `campaigns.csv` | — | `dim_campaigns` |
| `orders.csv` | — | reference only |

---

## Summary of Files Changed

| File | What Changed |
|---|---|
| `backend/main.py` | Auth (real login/register), per-company queries, has_data flags, upload fix |
| `backend/app/nlp/text_to_sql.py` | Replaced Ollama with Groq, fixed schema description |
| `backend/app/services/explainer.py` | Replaced Ollama with Groq, rewrote explain_result() |
| `backend/app/semantic/kpis.py` | Expanded synonym map from 6 to 13 KPIs |
| `notebooks/semantic_layer.json` | Added 6 new KPI SQL definitions, fixed cash_runway SQL |
| `src/data_pipeline/load.py` | Fixed hardcoded password |
| `frontend/app.py` | Added company_id to session state, Wouessi sidebar logo |
| `frontend/pages/login.py` | Stores company_id from API response |
| `frontend/pages/register.py` | Redirects to Upload after register, Wouessi branding |
| `frontend/pages/landing.py` | Full Wouessi rebrand (Anusha's update) |
| `frontend/pages/p01_overview.py` | has_data check, fixed missing fields |
| `frontend/pages/p03_finance.py` | has_data check, fixed cash_trend crash, monthly_trend guard |
| `frontend/pages/p04_sales.py` | has_data check, campaign_performance guard |
| `frontend/pages/p05_customers.py` | has_data check, fixed missing KPI fields |
| `frontend/pages/p02_chat.py` | Added dataframe display for multi-row results |
| `frontend/api_client.py` | Removed company_id from chat payload |
| **Database** | Added `company_id` column to `fact_sales` and `fact_marketing` |

---

## Environment Variables Required

```env
DATABASE_URL=postgresql://postgres:Mayank1717%40%40@localhost:5432/bi_dashboard
GROQ_API_KEY=gsk_<your_groq_api_key_here>
```

---

## How to Run

```bash
# Backend
cd D:\Uni\conversational-bi-dashboard
$env:DATABASE_URL = "postgresql://postgres:Mayank1717%40%40@localhost:5432/bi_dashboard"
$env:GROQ_API_KEY = "gsk_..."
.\.venv\Scripts\uvicorn.exe backend.main:app --port 8001 --reload

# Frontend (separate terminal)
cd D:\Uni\conversational-bi-dashboard\frontend
.\.venv\Scripts\streamlit.exe run app.py
```

**Backend:** http://localhost:8001  
**Frontend:** http://localhost:8501
