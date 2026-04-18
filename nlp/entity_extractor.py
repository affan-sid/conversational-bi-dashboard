def extract_entities(question):
    question = question.lower()
    entities = {}

    if "month" in question:
        entities["time_period"] = "month"
    if "year" in question:
        entities["time_period"] = "year"

    if "revenue" in question:
        entities["metric"] = "revenue"
    if "profit" in question:
        entities["metric"] = "profit"
    if "expenses" in question:
        entities["metric"] = "expenses"

    if "product" in question:
        entities["product"] = True

    if "campaign" in question:
        entities["campaign"] = True

    return entities
