KPI_DEFINITIONS = {
    "total_revenue": {
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM orders",
        "description": "Total revenue from all orders"
    },
    "top_products": {
        "sql": """
            SELECT p.product_name, SUM(oi.line_total) AS revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY revenue DESC
            LIMIT 5
        """
    }
}

def map_to_kpi(user_query: str):
    if "revenue" in user_query.lower():
        return "total_revenue"
    if "top" in user_query.lower() and "products" in user_query.lower():
        return "top_products"
    return None