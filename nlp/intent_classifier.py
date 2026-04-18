def classify_intent(question):
    question = question.lower()

    if "why" in question:
        return "root_cause_analysis"
    elif "trend" in question or "change" in question:
        return "trend_analysis"
    elif "top" in question or "best" in question:
        return "ranking"
    elif "compare" in question or "vs" in question:
        return "comparison"
    elif "forecast" in question or "future" in question:
        return "forecast"
    elif "recommend" in question or "should" in question:
        return "recommendation"
    elif "anomaly" in question or "unusual" in question:
        return "anomaly_explanation"
    elif "data" in question and "clean" in question:
        return "data_quality"
    elif "hello" in question or "hi" in question:
        return "general_chat"
    else:
        return "kpi_retrieval"
