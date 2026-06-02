from sqlalchemy import text
from backend.app.services.db import engine

def execute_sql(sql_query: str, params: dict = None):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query), params or {})
            rows = result.fetchall()
            columns = result.keys()

        return {
            "columns": list(columns),
            "rows": [list(row) for row in rows]
        }

    except Exception as e:
        return {"error": str(e)}