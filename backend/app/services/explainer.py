def explain_result(user_query, result):

    if "revenue" in user_query.lower():
        revenue = result["rows"][0][0]
        return f"Total revenue is ${revenue:,.0f}, calculated from completed sales transactions."

    if "gross profit" in user_query.lower():
        gp = result["rows"][0][0]
        return f"Gross profit is ${gp:,.0f}, derived from revenue minus product costs."

    if "marketing roi" in user_query.lower():
        return "Marketing ROI compares attributed revenue against campaign spending."

    if "top customer" in user_query.lower():
        return "Customers are ranked using purchase activity and revenue contribution."

    return "Result generated successfully from the semantic warehouse."