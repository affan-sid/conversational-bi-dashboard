import os
import requests
from dotenv import load_dotenv

load_dotenv()

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL   = "gpt-4o-mini"

_SCHEMA = """
Tables:

fact_sales(
    order_item_id, order_id, product_id, company_id, quantity,
    unit_price, cost_price, line_total,
    order_date DATE, customer_id, channel,
    status TEXT -- 'completed' or 'returned',
    gross_profit
)

dim_products(product_id, product_name, category, price, cost)

dim_customers(
    customer_id, company_id, full_name, email,
    segment, city, country, created_at
)

fact_expenses(
    expense_id, company_id,
    date TEXT,   -- stored as 'YYYY-MM-DD' text, cast with CAST(date AS DATE)
    expense_category, vendor_name, amount, recurring_flag
)

fact_marketing(
    record_id, campaign_id, company_id,
    date TEXT,   -- stored as 'YYYY-MM-DD' text, cast with CAST(date AS DATE)
    impressions, clicks, leads, conversions,
    spend, revenue_attributed
    -- NOTE: there is NO roi or roas column; compute as (revenue_attributed - spend) / spend
)

dim_campaigns(campaign_id, campaign_name, platform, budget)

fact_cash_flow(
    transaction_id, company_id,
    date TIMESTAMP,
    type TEXT, amount, signed_amount
)

dim_services(
    service_id, company_id, service_name, category,
    duration_minutes, price, recurring_flag, active_flag, description
)

fact_service_bookings(
    booking_id, service_id, company_id, customer_id,
    booking_date TEXT,  -- stored as 'YYYY-MM-DD' text, cast with CAST(booking_date AS DATE)
    sessions INT,       -- number of sessions booked (like quantity for products)
    unit_price, line_total, gross_profit,
    channel TEXT, status TEXT  -- 'completed' or 'cancelled'
)
"""


def _few_shot_examples(company_id: int) -> str:
    return f"""
Examples (for company_id = {company_id}):

Q: What is my total revenue?
SQL: SELECT SUM(line_total) AS total_revenue FROM fact_sales WHERE status = 'completed' AND company_id = {company_id};

Q: What are my top 5 best-selling products?
SQL: SELECT p.product_name, SUM(s.line_total) AS revenue
     FROM fact_sales s
     JOIN dim_products p ON s.product_id = p.product_id
     WHERE s.status = 'completed' AND s.company_id = {company_id}
     GROUP BY p.product_name
     ORDER BY revenue DESC
     LIMIT 5;

Q: Which marketing campaign has the best ROI?
SQL: SELECT c.campaign_name,
            SUM(m.revenue_attributed) AS revenue,
            SUM(m.spend) AS spend,
            (SUM(m.revenue_attributed) - SUM(m.spend)) / NULLIF(SUM(m.spend), 0) AS roi
     FROM fact_marketing m
     JOIN dim_campaigns c ON m.campaign_id = c.campaign_id
     WHERE m.company_id = {company_id}
     GROUP BY c.campaign_name
     ORDER BY roi DESC
     LIMIT 20;

Q: Show me monthly revenue trend
SQL: SELECT DATE_TRUNC('month', order_date) AS month, SUM(line_total) AS revenue
     FROM fact_sales
     WHERE status = 'completed' AND company_id = {company_id}
     GROUP BY month
     ORDER BY month;

Q: What are my biggest expense categories?
SQL: SELECT expense_category, SUM(amount) AS total_expense
     FROM fact_expenses
     WHERE company_id = {company_id}
     GROUP BY expense_category
     ORDER BY total_expense DESC
     LIMIT 10;

Q: What is my current cash balance?
SQL: SELECT SUM(signed_amount) AS current_balance FROM fact_cash_flow WHERE company_id = {company_id};

Q: Who are my top customers by revenue?
SQL: SELECT c.full_name, SUM(s.line_total) AS total_revenue
     FROM fact_sales s
     JOIN dim_customers c ON s.customer_id = c.customer_id
     WHERE s.status = 'completed' AND s.company_id = {company_id}
     GROUP BY c.full_name
     ORDER BY total_revenue DESC
     LIMIT 10;

Q: What is my gross profit?
SQL: SELECT SUM(gross_profit) AS total_gross_profit FROM fact_sales WHERE status = 'completed' AND company_id = {company_id};

Q: What are my top services by revenue?
SQL: SELECT ds.service_name, ds.category, SUM(fsb.sessions) AS total_sessions, SUM(fsb.line_total) AS revenue
     FROM fact_service_bookings fsb
     JOIN dim_services ds ON fsb.service_id = ds.service_id
     WHERE fsb.status = 'completed' AND fsb.company_id = {company_id}
     GROUP BY ds.service_name, ds.category
     ORDER BY revenue DESC
     LIMIT 10;

Q: What is my total service revenue?
SQL: SELECT SUM(line_total) AS service_revenue FROM fact_service_bookings WHERE status = 'completed' AND company_id = {company_id};

Q: How many service bookings did I have this month?
SQL: SELECT COUNT(*) AS total_bookings FROM fact_service_bookings
     WHERE status = 'completed' AND company_id = {company_id}
       AND CAST(booking_date AS DATE) >= DATE_TRUNC('month', NOW());
"""


def generate_sql(user_query: str, company_id: int) -> str:
    few_shots = _few_shot_examples(company_id)
    prompt = f"""You are a PostgreSQL expert. Convert the user question to a single PostgreSQL SELECT query.

Rules:
- Return ONLY raw SQL, no markdown, no code fences, no explanation
- Use ONLY columns that exist in the schema below
- CRITICAL SECURITY RULE: Every table that has a company_id column MUST be filtered with company_id = {company_id}.
  Tables with company_id: fact_sales, dim_customers, fact_expenses, fact_marketing, fact_cash_flow, dim_services, fact_service_bookings
- fact_marketing has NO roi or roas column — compute ROI as (revenue_attributed - spend) / NULLIF(spend, 0)
- fact_expenses.date and fact_marketing.date are TEXT — use CAST(date AS DATE) for date functions
- Revenue = fact_sales.line_total  |  Expenses = fact_expenses.amount
- For product names JOIN dim_products ON product_id
- For campaign names JOIN dim_campaigns ON campaign_id
- For customer names JOIN dim_customers ON customer_id
- Limit results to 20 rows unless the query is for a single value

Schema:
{_SCHEMA}

{few_shots}
Question: {user_query}
SQL:"""

    try:
        resp = requests.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {_OPENAI_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": _OPENAI_MODEL,
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0},
            timeout=30
        )
        sql = resp.json()["choices"][0]["message"]["content"].strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
        print("Generated SQL:", sql[:120])
        return sql
    except Exception as e:
        print(f"OpenAI SQL generation failed: {e}")
        return "SELECT 'Could not generate SQL' AS error"


def is_safe_sql(sql: str):

    forbidden = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE"
    ]

    return not any(word in sql.upper() for word in forbidden)