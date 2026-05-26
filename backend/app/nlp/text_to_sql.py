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
    order_item_id, order_id, product_id, quantity,
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
    record_id, campaign_id,
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
"""


def generate_sql(user_query: str) -> str:
    prompt = f"""You are a PostgreSQL expert. Convert the user question to a single PostgreSQL SELECT query.

Rules:
- Return ONLY raw SQL, no markdown, no code fences, no explanation
- Use ONLY columns that exist in the schema below
- fact_marketing has NO roi or roas column — compute ROI as (revenue_attributed - spend) / NULLIF(spend, 0)
- fact_expenses.date and fact_marketing.date are TEXT — use CAST(date AS DATE) for date functions
- Revenue = fact_sales.line_total  |  Expenses = fact_expenses.amount
- For product names JOIN dim_products ON product_id
- For campaign names JOIN dim_campaigns ON campaign_id
- For customer names JOIN dim_customers ON customer_id
- Limit results to 20 rows unless the query is for a single value

Schema:
{_SCHEMA}

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