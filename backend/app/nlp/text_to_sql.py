from openai import OpenAI
import requests

# client = OpenAI()

def generate_sql(user_query: str):

    # UPDATED STAR SCHEMA
    schema = """
    Tables:

    fact_sales(
        order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        cost_price,
        line_total,
        order_date DATE,
        customer_id,
        channel,
        status,
        gross_profit,
        profit_margin
    )

    dim_products(
        product_id,
        product_name,
        category,
        price,
        cost,
        profit_margin
    )

    dim_customers(
        customer_id,
        company_id,
        full_name,
        email,
        phone,
        segment,
        city,
        country,
        created_at
    )

    fact_expenses(
        expense_id,
        company_id,
        date DATE,
        expense_category,
        vendor_name,
        amount,
        recurring_flag
    )

    fact_marketing(
        campaign_id,
        date DATE,
        impressions,
        clicks,
        leads,
        conversions,
        spend,
        revenue_attributed,
        roi,
        roas
    )

    dim_campaigns(
        campaign_id,
        campaign_name,
        platform,
        budget
    )

    fact_cash_flow(
        company_id,
        date DATE,
        type,
        amount,
        signed_amount
    )
    """

    prompt = f"""
    You are a PostgreSQL expert.

    Convert the natural language query into PostgreSQL SQL.

    Rules:
    - Only return raw SQL
    - No markdown
    - No explanations
    - No code fences
    - Use ONLY the provided schema
    - Prefer fact tables for metrics
    - Prefer dimension tables for descriptive information
    - Use PostgreSQL syntax

    Important:
    - Revenue comes from fact_sales.line_total
    - Expenses come from fact_expenses.amount
    - Product names come from dim_products
    - Customer data comes from dim_customers
    - Marketing data comes from fact_marketing
    - For category-based queries, join dim_products using product_id
    - "sales by category" means GROUP BY product category
    - "top customers" means order by customer revenue or order count

    Schema:
    {schema}

    User Query:
    {user_query}
    """

    # GPT VERSION
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}],
    #     temperature=0
    # )
    # return response.choices[0].message.content.strip()

    # OLLAMA LOCAL MODEL
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.1",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    )

    data = response.json()

    sql = data["message"]["content"].strip()

    sql = sql.replace("```sql", "").replace("```", "").strip()

    print("Generated SQL:")
    print(sql)

    return sql


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