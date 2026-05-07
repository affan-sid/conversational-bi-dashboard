def explain_result(user_query, result):
    if "total_revenue" in user_query.lower():
        value = result["rows"][0][0]
        return f"Your total revenue is ${value:,.0f}."

    if "top" in user_query.lower() and "product" in user_query.lower():
        top = result["rows"][0]
        return f"Your top product is {top[0]} generating ${top[1]:,.0f}."

    return "Here is your result."