# Conversational BI Dashboard — Developer Guide

A plain-English guide for any developer picking up this project.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [Backend Module Reference](#backend-module-reference)
5. [API Endpoint Reference](#api-endpoint-reference)
6. [Database Schema](#database-schema)
7. [Adding New Features](#adding-new-features)
8. [Demo Data & Seeding](#demo-data--seeding)
9. [Deployment (Render)](#deployment-render)

---

## What This Project Does

An AI-powered business intelligence dashboard for small and medium businesses. Users log in, connect their data (or use demo data), and can:

- Ask questions in plain English: *"What was my revenue last month?"*
- View dashboards for finance, sales, marketing, and customers
- Get automatically detected anomalies (unusual spikes/drops in data)
- See 30/60/90-day revenue and cash flow forecasts
- Upload their own CSV data files

The system converts natural-language questions into SQL using OpenAI's GPT-4o-mini, runs the query against the user's company data, and returns a plain-English explanation plus recommended actions.

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (local or hosted, e.g. Supabase, Render Postgres)
- An OpenAI API key

### 1. Clone and install

```bash
git clone <repo-url>
cd conversational-bi-dashboard
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in DATABASE_URL and OPENAI_API_KEY
```

The `.env` file must contain:

```
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/bi_dashboard
OPENAI_API_KEY=sk-...
```

### 3. Seed demo data

Start the backend first (step 4), then seed demo data via:

```
POST /api/admin/seed-demo?secret=SEED_WOUESSI_2024
```

This loads the Wouessi Digital Agency demo dataset into the database.

### 4. Run the backend

```bash
cd conversational-bi-dashboard
uvicorn backend.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 5. Run the frontend

Open a second terminal:

```bash
cd frontend
streamlit run app.py
```

Frontend opens at: `http://localhost:8501`

### Demo login

Use the **Try Demo** button on the login page, or `POST /auth/demo-login`. This logs in as `demo@wouessi.com` tied to the Wouessi demo dataset.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND  (Streamlit — frontend/)                           │
│  Pages: Overview, Chat, Finance, Sales, Customers,           │
│         Anomalies, Forecasting, Upload                       │
│  All API calls go through frontend/api_client.py             │
└──────────────────────┬───────────────────────────────────────┘
                       │  HTTP/REST
┌──────────────────────▼───────────────────────────────────────┐
│  BACKEND  (FastAPI — backend/main.py)                        │
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐                  │
│  │  NLP Layer      │  │  Analytics Layer │                  │
│  │  text_to_sql.py │  │  anomaly_        │                  │
│  │  kpis.py        │  │  detection.py    │                  │
│  └────────┬────────┘  │  forecasting.py  │                  │
│           │           └──────────────────┘                  │
│  ┌────────▼────────────────────────────────┐                │
│  │  Services Layer                          │                │
│  │  db.py  query_engine.py  explainer.py   │                │
│  │  insights.py  recommendations.py        │                │
│  └────────┬────────────────────────────────┘                │
└───────────┼──────────────────────────────────────────────────┘
            │  SQLAlchemy
┌───────────▼──────────────────────────────────────────────────┐
│  DATABASE  (PostgreSQL)                                       │
│  Star schema: fact_* tables + dim_* tables                   │
│  Multi-tenant: every table filtered by company_id            │
└──────────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│  EXTERNAL APIs                                               │
│  OpenAI GPT-4o-mini — SQL generation + explanations         │
└──────────────────────────────────────────────────────────────┘
```

**Multi-tenancy:** Every user belongs to a company (`company_id`). All queries are filtered by `company_id` so companies never see each other's data. Authentication is token-based; tokens are stored in memory on the server (lost on restart — upgrade to Redis/DB for production).

---

## Backend Module Reference

### `backend/main.py`
The FastAPI application entry point. Contains all route handlers and two helper utilities used across endpoints:

| Function | What it does |
|----------|-------------|
| `_scalar(sql, params)` | Runs a SQL query and returns a single number. Returns `0.0` on error. |
| `_rows(sql, params)` | Runs a SQL query and returns a list of dicts (one per row). Returns `[]` on error. |
| `_cash_in_bank(company_id)` | Gets the current cash balance — checks `fact_cash_balances` first, falls back to summing `fact_cash_flow`. |
| `_period_interval(period)` | Converts a period string like `"last_30_days"` to a PostgreSQL interval like `"30 days"`. |
| `get_company_id(authorization)` | FastAPI dependency that extracts `company_id` from the Bearer token. Used on every protected endpoint. |

On startup (`@app.on_event("startup")`), the app creates the `dim_services` and `fact_service_bookings` tables if they don't exist.

---

### `backend/app/nlp/text_to_sql.py`
Converts a user's plain-English question into a PostgreSQL SELECT query using OpenAI.

| Function | What it does |
|----------|-------------|
| `generate_sql(user_query, company_id)` | Sends the user's question to GPT-4o-mini with the database schema and few-shot examples. Returns a SQL string. If OpenAI is unavailable, returns a safe error string. |
| `is_safe_sql(sql)` | Checks that the SQL does not contain any write/delete operations (`DROP`, `DELETE`, `UPDATE`, etc.). Returns `True` if safe. |

**How it works:** The prompt includes the full table schema (`_SCHEMA`) and 12 example question→SQL pairs (`_few_shot_examples`). This guides the model to always filter by `company_id` and handle edge cases like combining `fact_sales` and `fact_service_bookings` for revenue queries.

---

### `backend/app/semantic/kpis.py`
A keyword-matching layer that shortcuts common questions to pre-written SQL, avoiding an OpenAI call.

| Function | What it does |
|----------|-------------|
| `map_to_kpi(user_query)` | Checks the query against keyword lists for ~25 KPI types. Returns the KPI key (e.g. `"revenue"`) if matched, or `None` to fall through to the LLM. |
| `KPI_DEFINITIONS` | Dict mapping KPI keys to `{sql, description}`. The SQL uses a `:company_id` bind parameter. |

**Examples of KPIs:** `revenue`, `gross_profit`, `net_profit`, `cash_runway`, `top_products`, `top_services`, `marketing_roi`, `churn_risk`, `avg_order_value`, `expense_breakdown`, etc.

The chat endpoint (`/api/chat`) tries `map_to_kpi` first. Only if it returns `None` does it call `generate_sql`.

---

### `backend/app/analytics/anomaly_detection.py`
Detects unusual patterns across four business domains using statistical methods.

| Function | What it does |
|----------|-------------|
| `run_all_detectors(company_id)` | Runs all four detectors, merges results, sorts by severity, returns `{summary, anomalies}`. |
| `detect_revenue_anomalies(company_id)` | Aggregates daily revenue from `fact_sales` + `fact_service_bookings`, then runs Z-score analysis. |
| `detect_expense_anomalies(company_id)` | Runs Z-score per expense category from `fact_expenses`. |
| `detect_marketing_anomalies(company_id)` | Runs Isolation Forest on `{spend, conversions, revenue_attributed}` from `fact_marketing`. Also includes SHAP values to explain which feature drove each anomaly. |
| `detect_cashflow_anomalies(company_id)` | Runs Z-score on daily signed cash movements from `fact_cash_flow`. |
| `_zscore_scan(series, dates, domain, metric)` | Reusable helper: computes Z-scores, returns anomaly dicts for any point with Z ≥ 2.0. |

**Severity thresholds:** Z-score ≥ 3.0 = `"high"`, ≥ 2.0 = `"medium"`. Isolation Forest anomalies are always `"medium"`.

**Anomaly dict format:**
```python
{
  "domain": "sales",          # business area
  "type": "daily_revenue_spike",
  "severity": "high",
  "message": "Daily Revenue spike of 45.2% on 2024-03-15",
  "date": "2024-03-15",
  "value": 15200.0,           # actual observed value
  "expected": 10500.0,        # normal baseline (mean)
  "deviation_pct": 44.8,
  "z_score": 3.21,
  "method": "zscore",
  "unit": "$",
  "recommendation": "Investigate sales trends..."
}
```

---

### `backend/app/analytics/forecasting.py`
Generates short-term revenue, expense, and cash flow forecasts using linear regression.

| Function | What it does |
|----------|-------------|
| `run_all_forecasts(company_id, days_ahead)` | Runs all three forecasts and returns combined results. `days_ahead` is 7–90. |
| `forecast_revenue(company_id, days_ahead)` | Aggregates daily revenue (sales + service bookings), fits a linear regression, projects `days_ahead` days forward. Returns `{historical, forecast, metrics}`. |
| `forecast_expenses(company_id, days_ahead)` | Same approach on `fact_expenses`. |
| `forecast_cashflow(company_id, days_ahead)` | Same approach on `fact_cash_flow.signed_amount` (cumulative). |

**Forecast response format (per domain):**
```python
{
  "historical": [{"date": "2024-01-01", "value": 1200.0}, ...],
  "forecast":   [{"date": "2024-04-01", "value": 1350.0}, ...],
  "metrics": {
    "rmse": 145.2,
    "mae": 112.0,
    "mape": 8.3,
    "r2_score": 0.84
  }
}
```

---

### `backend/app/services/explainer.py`
Turns raw query results and anomalies into plain-English explanations and recommended actions.

| Function | What it does |
|----------|-------------|
| `explain_result(user_query, result)` | Formats a SQL result dict into a human-readable string. Context-aware: different intros for customer queries, product queries, etc. No LLM needed. |
| `generate_insight(user_query, answer_summary, result, sql)` | Calls OpenAI to produce `{reason, evidence, action}` — why this happened, two data points as evidence, and 2-3 sentence action recommendation. Falls back to `_rule_based_action` if OpenAI is unavailable or returns a short response. |
| `explain_anomaly(anomaly)` | Calls OpenAI to write a 2-3 sentence business-friendly explanation of one anomaly. Falls back to `_template_explanation`. |
| `enrich_anomalies_fast(anomalies)` | Template-only enrichment — no API calls, very fast. Used by the live `/api/anomalies` endpoint. |
| `enrich_anomalies_with_explanations(anomalies)` | LLM-based enrichment — one API call per anomaly. Slow; only use offline or on demand. |
| `explain_marketing_anomalies_with_shap(features_df)` | Fits an Isolation Forest, computes SHAP values, returns plain-English feature-level explanations. |
| `_call_openai(prompt)` | Internal helper that POSTs to the OpenAI API. Returns empty string on failure. |
| `_rule_based_action(user_query, result)` | Fallback action suggestions based on keywords in the query. Always returns something even without an API key. |

---

### `backend/app/services/db.py`
Creates and exports the SQLAlchemy `engine`. All other modules import `engine` from here.

```python
from backend.app.services.db import engine
```

The connection string is read from `DATABASE_URL` in the environment.

---

### `backend/app/services/query_engine.py`
Executes a SQL string and returns results in a standard format.

| Function | What it does |
|----------|-------------|
| `execute_sql(sql, params)` | Runs the query, returns `{columns: [...], rows: [...]}`. Returns `{error: "..."}` on failure. |

---

### `backend/app/services/insights.py`
Legacy module — provides `get_revenue_insight()` which combines total revenue with any detected revenue anomalies. Called only when the chat query explicitly says "revenue insight".

---

### `backend/app/services/recommendations.py`
Converts a list of anomaly dicts into actionable recommendations.

| Function | What it does |
|----------|-------------|
| `generate_recommendations(anomalies)` | Scans anomaly types, returns up to one recommendation per domain (revenue drop, cashflow, expense, marketing, data quality). Each recommendation has `{type, confidence, recommendation}`. Sorted by confidence descending. |

---

### `backend/app/admin/seed_demo.py`
One-time data seeding for demo/testing purposes.

| Function | What it does |
|----------|-------------|
| `seed_wouessi(engine)` | Seeds the Wouessi Digital Agency demo dataset: customers, finance, marketing, products, sales. Wipes existing data for company 1 first. |
| `seed_kp_fashion_services(engine)` | Seeds a fashion/services demo dataset as a second company. |

These are called via the admin endpoints (see API Reference below). Require a secret key.

---

## API Endpoint Reference

All endpoints except auth require a `Authorization: Bearer <token>` header. The token is returned on login.

### Auth

| Method | Path | What it does |
|--------|------|-------------|
| `POST` | `/auth/login` | Login with `{email, password}`. Returns `{token, user}`. |
| `POST` | `/auth/register` | Register with `{full_name, email, password, company_name, currency}`. Returns `{token, user}`. |
| `POST` | `/auth/demo-login` | Get a token for the read-only demo account. No body needed. |
| `POST` | `/auth/reset-password` | Reset password with `{email, new_password}`. |

### Dashboard Data

| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/api/overview` | Executive summary KPIs: revenue, profit, cash, customers, marketing. |
| `GET` | `/api/finance/summary?period=last_3_months` | Finance dashboard data: KPIs, monthly trend, expense breakdown, cash trend. |
| `GET` | `/api/sales/summary?period=last_3_months` | Sales + marketing data: orders, top products/services, campaign performance. |
| `GET` | `/api/marketing/summary?period=last_3_months` | Marketing KPIs: impressions, CTR, CPA, campaign breakdown. |
| `GET` | `/api/customers/summary?period=last_3_months` | Customer analytics: segments, CLV, churn risk, top customers. |
| `GET` | `/api/services/summary?period=last_3_months` | Service booking analytics: top services, revenue by category/channel. |

Valid `period` values: `last_7_days`, `last_30_days`, `last_3_months`, `last_6_months`, `all_time`.

### AI Features

| Method | Path | What it does |
|--------|------|-------------|
| `POST` | `/api/chat` | Natural language query. Body: `{question: "..."}`. Returns `{answer, sql, result, reason, evidence, action, confidence}`. |
| `GET` | `/api/anomalies` | Detect anomalies for the logged-in company. Returns `{summary, anomalies}`. |
| `GET` | `/api/forecasts?days_ahead=30` | Forecasts for revenue, expenses, and cash flow. `days_ahead`: 7–90. |

### Data Upload

| Method | Path | What it does |
|--------|------|-------------|
| `POST` | `/upload/csv` | Upload a CSV file. Form fields: `file` (the CSV), `domain` (optional: `auto`, `sales`, `customers`, `products`, `marketing`, `finance`, `services`, `service_bookings`). Returns a quality report. |
| `GET` | `/upload/history` | Last 20 uploads for the logged-in company. |

### Admin (restricted)

| Method | Path | What it does |
|--------|------|-------------|
| `POST` | `/api/admin/seed-demo?secret=SEED_WOUESSI_2024` | Load the Wouessi demo dataset into the database. |
| `POST` | `/api/admin/seed-kp-fashion?secret=SEED_WOUESSI_2024` | Load the KP Fashion demo dataset. |

### Legacy (kept for backwards compatibility)

| Method | Path | What it does |
|--------|------|-------------|
| `GET` | `/revenue` | Total revenue across all companies (no auth). |
| `GET` | `/top-products` | Top 5 products by revenue (no auth). |
| `POST` | `/query?user_query=...` | NLP query, older format. Prefer `/api/chat`. |
| `POST` | `/recommendations` | Generate recommendations from a list of anomaly dicts. Body: list of anomaly objects. |

---

## Database Schema

All tables use `company_id` for multi-tenancy. Never query without filtering by `company_id`.

### Dimension Tables

| Table | Key columns | Purpose |
|-------|-------------|---------|
| `dim_companies` | `company_id`, `company_name`, `industry`, `currency` | Company master — one row per tenant |
| `dim_users` | `user_id`, `company_id`, `email`, `password_hash`, `role` | User accounts |
| `dim_customers` | `customer_id`, `company_id`, `full_name`, `segment`, `created_at` | Customer master |
| `dim_products` | `product_id`, `product_name`, `category`, `price`, `cost` | Product catalog |
| `dim_campaigns` | `campaign_id`, `campaign_name`, `platform`, `budget` | Marketing campaigns |
| `dim_services` | `service_id`, `company_id`, `service_name`, `category`, `price`, `recurring_flag` | Service offerings |
| `customer_metrics` | `customer_id`, `total_revenue`, `churn_risk_score` | Pre-computed customer KPIs |

### Fact Tables

| Table | Key columns | Purpose |
|-------|-------------|---------|
| `fact_sales` | `order_date`, `company_id`, `customer_id`, `product_id`, `line_total`, `gross_profit`, `channel`, `status` | Product sales transactions. `status` = `'completed'` or `'returned'` |
| `fact_service_bookings` | `booking_date`, `company_id`, `service_id`, `customer_id`, `sessions`, `line_total`, `gross_profit`, `channel`, `status` | Service booking records. `status` = `'completed'` or `'cancelled'` |
| `fact_expenses` | `date`, `company_id`, `expense_category`, `amount`, `vendor_name` | Expense records. `date` is stored as TEXT — use `CAST(date AS DATE)` |
| `fact_marketing` | `date`, `company_id`, `campaign_id`, `spend`, `revenue_attributed`, `impressions`, `clicks`, `leads`, `conversions` | Marketing performance. `date` is TEXT. No `roi` column — compute as `(revenue_attributed - spend) / spend` |
| `fact_cash_flow` | `date`, `company_id`, `type`, `amount`, `signed_amount` | Cash transaction log. `signed_amount` is positive for inflows, negative for outflows |
| `fact_cash_balances` | `date`, `company_id`, `closing_balance` | Daily cash balance snapshots (optional, used if populated) |

**Important:** `fact_expenses.date`, `fact_marketing.date`, and `fact_service_bookings.booking_date` are all stored as TEXT strings (`YYYY-MM-DD`). Always cast with `CAST(column AS DATE)` before date arithmetic.

---

## Adding New Features

### Adding a new dashboard page

1. Create `frontend/pages/pXX_mypage.py` following the pattern of existing pages
2. Add a new entry in the sidebar navigation in `frontend/app.py`
3. Add the corresponding API endpoint in `backend/main.py`
4. The frontend calls the backend via `frontend/api_client.py` — add a wrapper function there

### Adding a new KPI shortcut

Open `backend/app/semantic/kpis.py` and add to `KPI_DEFINITIONS`:

```python
"my_new_kpi": {
    "sql": "SELECT SUM(amount) FROM fact_expenses WHERE company_id = :company_id AND expense_category = 'Rent'",
    "description": "Total rent expenses"
}
```

Then add keyword triggers to `map_to_kpi()` so it routes matching queries to this KPI instead of the LLM.

### Adding a new anomaly detector

Add a function to `backend/app/analytics/anomaly_detection.py`:

```python
def detect_my_anomalies(company_id: int) -> list:
    df = _query_df("SELECT ...", company_id)
    if df.empty:
        return []
    return _zscore_scan(df["my_metric"], df["date"], "my_domain", "my_metric_name", "$")
```

Then call it inside `run_all_detectors()`:

```python
anomalies += detect_my_anomalies(company_id)
```

### Adding a new upload domain

In `backend/main.py`, add to `_DOMAIN_TABLE_MAP` and `_REQUIRED_COLS`:

```python
_DOMAIN_TABLE_MAP["my_domain"] = "my_table"
_REQUIRED_COLS["my_domain"] = {"required_col1", "required_col2"}
```

---

## Demo Data & Seeding

The project ships with two demo datasets in `data/demo_wouessi/`:

- `customers.csv` — Wouessi Digital Agency customer records
- `finance.csv` — expense records
- `marketing.csv` — campaign performance
- `products.csv` — services (treated as products)
- `sales.csv` — sales/booking records

To load into a fresh database:

```
POST /api/admin/seed-demo?secret=SEED_WOUESSI_2024
```

To reset and reload at any time, call the same endpoint again (it wipes existing data for company 1 first).

Raw sample data is also available in `data/raw/` and a SQLite version in `data/raw/bi_sample.sqlite`.

---

## Deployment (Render)

A `render.yaml` is included at the project root for one-click deployment on [Render](https://render.com).

**Environment variables to set in the Render dashboard:**

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Render PostgreSQL internal URL |
| `OPENAI_API_KEY` | Your OpenAI key |

After deploying:
1. Call `POST /api/admin/seed-demo?secret=SEED_WOUESSI_2024` to load demo data
2. Test with the demo login via the frontend

**Auth note:** The current token store is in-memory (`_TOKENS` dict in `main.py`). Sessions are lost when the server restarts. For production, replace with a Redis store or a `sessions` database table.
