from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.app.services.db import engine
from backend.app.nlp.engine import process_query
from backend.app.nlp.response_composer import compose_response


def get_revenue_from_db():
    query = text("SELECT SUM(total_amount) AS revenue FROM orders")

    try:
        with engine.connect() as conn:
            result = conn.execute(query).fetchone()

        if result is None or result[0] is None:
            return {
                "success": True,
                "revenue": 0
            }

        return {
            "success": True,
            "revenue": float(result[0])
        }

    except SQLAlchemyError as error:
        return {
            "success": False,
            "error": "Database connection is currently unavailable.",
            "details": str(error)
        }


def handle_chat(question: str):
    nlp_result = process_query(question)
    response = compose_response(nlp_result)

    entities = nlp_result.get("entities", {})
    metric = entities.get("metric")
    intent = nlp_result.get("intent")

    if metric == "revenue":
        revenue_result = get_revenue_from_db()

        if revenue_result["success"]:
            revenue = revenue_result["revenue"]

            response["data"] = {
                "revenue": revenue
            }

            response["answer"] = f"The total revenue is ${revenue:,.2f}."

            if intent == "trend_analysis":
                response["next_step"] = (
                    "Revenue trend was requested. Current version returns total revenue first; "
                    "chart-ready trend values can be added next."
                )

        else:
            response["data"] = None
            response["answer"] = (
                "I understood that you are asking about revenue, but the database is not connected locally right now."
            )
            response["next_step"] = (
                "Start the local PostgreSQL database or confirm the correct database host, port, username, password, and database name."
            )
            response["database_status"] = "unavailable"

    return {
        "message": "Processed successfully",
        "response": response
    }