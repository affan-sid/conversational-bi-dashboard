def compose_response(nlp_result):
    question = nlp_result.get("question", "")
    intent = nlp_result.get("intent", "")
    entities = nlp_result.get("entities", {})

    metric = entities.get("metric", "business performance")
    time_period = entities.get("time_period", "the selected period")

    if intent == "root_cause_analysis":
        answer = f"You are asking why {metric} is changing during {time_period}."
        next_step = "Compare revenue, expenses, and related business drivers to identify the likely cause."

    elif intent == "trend_analysis":
        answer = f"You are asking to view the trend for {metric} over {time_period}."
        next_step = "Fetch time-based data and prepare chart-ready trend values."

    elif intent == "ranking":
        answer = "You are asking for a ranked list of business items."
        next_step = "Fetch the top or bottom results based on the selected metric."

    elif intent == "comparison":
        answer = "You are asking to compare two or more business measures."
        next_step = "Fetch comparison data and calculate differences."

    elif intent == "recommendation":
        answer = "You are asking for a recommended action."
        next_step = "Analyse business indicators and suggest the most useful next action."

    elif intent == "forecast":
        answer = "You are asking for a future estimate."
        next_step = "Use historical data to generate a forecast."

    elif intent == "data_quality":
        answer = "You are asking about the quality or cleanliness of the data."
        next_step = "Check missing values, duplicates, and recent ETL logs."

    else:
        answer = "Your question has been processed."
        next_step = "Route the question to the correct business analysis module."

    return {
        "question": question,
        "answer": answer,
        "intent": intent,
        "entities": entities,
        "next_step": next_step
    }