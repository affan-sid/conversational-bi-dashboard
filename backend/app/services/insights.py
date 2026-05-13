from backend.app.analytics.anomaly_detection import run_all_detectors
from backend.app.semantic.kpis import KPI_DEFINITIONS
from backend.app.services.query_engine import execute_sql


def get_revenue_insight():

    sql = KPI_DEFINITIONS["revenue"]["sql"]
    result = execute_sql(sql)
    revenue = result["rows"][0][0]

    anomalies = run_all_detectors()
    revenue_anomalies = [
        a for a in anomalies["anomalies"]
        if "revenue" in a["type"]
    ]

    insight = {
        "revenue": revenue,
        "anomaly_count": len(revenue_anomalies),
        "message": f"Total revenue is ${revenue:,.0f}. "
                   f"{len(revenue_anomalies)} anomalies detected in revenue trends."
    }

    return insight