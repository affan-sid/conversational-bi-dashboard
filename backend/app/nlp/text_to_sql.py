from openai import OpenAI
import requests
# client = OpenAI()

def generate_sql(user_query: str):

    schema = """
    Tables:
    orders(order_id, company_id, customer_id, order_date, total_amount)
    order_items(order_item_id, order_id, product_id, quantity, unit_price, cost_price, line_total)
    products(product_id, product_name, category, price, cost)
    """

    prompt = f"""
    You are a PostgreSQL expert.
    Convert the following natural language query into SQL.

    Rules:
    - Only return raw SQL
    - Do NOT use code fences or markdown
    - Do NOT add ```sql
    - Do not explain anything
    - Use only the given schema

    Schema:
    {schema}
    User Query:
    {user_query}
    """

    # BELOW CHUNK TO BE USED TOWARDS THE END OF DEVELOPMENT AS IT IS PAID.

    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",  #cheap + good enough
    #     messages=[{"role": "user", "content": prompt}],
    #     temperature=0
    # )
    # return response.choices[0].message.content.strip()

    # USING LAMA3.1 FOR NOW AS IT IS FREE AND GOOD ENOUGH FOR OUR PROTOTYPE
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.1",   # or qwen2.5
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    )

    data = response.json()
    sql = data["message"]["content"].strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    print("Generated SQL:", sql)
    return sql

def is_safe_sql(sql: str):
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT"]
    return not any(word in sql.upper() for word in forbidden)