import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from scipy import stats
from sqlalchemy import text
from backend.app.services.db import engine

# Thresholds
_ZSCORE_HIGH = 3.0
_ZSCORE_MEDIUM = 2.0
_IF_CONTAMINATION = 0.05


# ── DB LOADERS ─────────────────────────────────────────────────────

def _query_df(sql: str, company_id: int) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    if "company_id" in df.columns:
        df = df[df["company_id"] == company_id]
    return df


# ── HELPERS ───────────────────────────────────────────────────────

def _severity(z: float) -> str:
    if z >= _ZSCORE_HIGH:
        return "high"
    if z >= _ZSCORE_MEDIUM:
        return "medium"
    return "low"


def _anomaly(domain, atype, severity, message, date=None,
             value=None, expected=None, deviation_pct=None,
             z_score=None, method="zscore", unit=""):
    return {
        "domain": domain,
        "type": atype,
        "severity": severity,
        "message": message,
        "date": date,
        "value": round(float(value), 2) if value is not None else None,
        "expected": round(float(expected), 2) if expected is not None else None,
        "deviation_pct": round(float(deviation_pct), 1) if deviation_pct is not None else None,
        "z_score": round(float(z_score), 2) if z_score is not None else None,
        "method": method,
        "unit": unit,
        "recommendation": _recommendation(domain, atype)
    }


def _recommendation(domain, atype):
    if "revenue" in atype:
        return "Investigate sales trends, campaigns, or seasonality changes."
    if "expense" in atype:
        return "Check for unusual or one-off expenses."
    if "marketing" in atype:
        return "Review campaign performance and targeting."
    if "cash" in atype:
        return "Monitor liquidity and upcoming liabilities."
    return "Further investigation required."


def _zscore_scan(series: pd.Series, dates: pd.Series,
                 domain: str, metric: str, unit: str = "") -> list:

    results = []
    if len(series) < 7 or series.std() < 1e-6:
        return results

    z_scores = np.abs(stats.zscore(series.values, nan_policy="omit"))
    mean_val = float(series.mean())

    for z, val, date in zip(z_scores, series.values, dates):
        if np.isnan(z) or z < _ZSCORE_MEDIUM:
            continue

        direction = "spike" if val > mean_val else "drop"
        dev_pct = ((val - mean_val) / mean_val * 100) if mean_val != 0 else 0

        results.append(_anomaly(
            domain=domain,
            atype=f"{metric}_{direction}",
            severity=_severity(z),
            message=f"{metric.replace('_',' ').title()} {direction} of {abs(dev_pct):.1f}% on {date}",
            date=str(date),
            value=val,
            expected=mean_val,
            deviation_pct=dev_pct,
            z_score=z,
            unit=unit,
        ))

    return results


# ── DETECTORS ─────────────────────────────────────────────────────

def detect_revenue_anomalies(company_id: int) -> list:
    df = _query_df("SELECT * FROM orders WHERE status='completed'", company_id)
    if df.empty:
        return []

    df["order_date"] = pd.to_datetime(df["order_date"])

    daily = df.groupby("order_date")["total_amount"].sum().reset_index()

    return _zscore_scan(
        daily["total_amount"],
        daily["order_date"].dt.strftime("%Y-%m-%d"),
        "sales",
        "daily_revenue",
        "$"
    )


def detect_expense_anomalies(company_id: int) -> list:
    df = _query_df("SELECT * FROM expenses", company_id)
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    results = []

    for cat, group in df.groupby("expense_category"):
        if len(group) < 5:
            continue

        results.extend(_zscore_scan(
            group["amount"],
            group["date"].dt.strftime("%Y-%m-%d"),
            "finance",
            f"{cat.lower()}_expense",
            "$"
        ))

    return results


def detect_marketing_anomalies(company_id: int) -> list:
    df = _query_df("SELECT * FROM marketing_performance", company_id)
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    results = []

    # Rule check
    bad = df[df["conversions"] > df["clicks"]]
    if not bad.empty:
        results.append(_anomaly(
            "marketing",
            "data_quality_issue",
            "medium",
            f"{len(bad)} invalid rows (conversions > clicks)",
        ))

    # Isolation Forest
    features = df[["spend", "conversions", "revenue_attributed"]].dropna()
    if len(features) >= 20:
        clf = IsolationForest(contamination=_IF_CONTAMINATION, random_state=42)
        preds = clf.fit_predict(features)

        for idx in np.where(preds == -1)[0]:
            row = df.iloc[idx]
            results.append(_anomaly(
                "marketing",
                "pattern_anomaly",
                "medium",
                f"Unusual marketing activity on {row['date'].date()}",
                date=str(row["date"].date()),
                value=row["spend"]
            ))

    return results


def detect_cashflow_anomalies(company_id: int) -> list:
    df = _query_df("SELECT * FROM cash_balances", company_id)
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    df["change"] = df["closing_balance"].diff()

    return _zscore_scan(
        df["change"].dropna(),
        df["date"].dt.strftime("%Y-%m-%d")[1:],
        "finance",
        "cashflow_change",
        "$"
    )


# ── MAIN ──────────────────────────────────────────────────────────

def run_all_detectors(company_id: int = 1) -> dict:

    try:
        anomalies = []
        anomalies += detect_revenue_anomalies(company_id)
        anomalies += detect_expense_anomalies(company_id)
        anomalies += detect_marketing_anomalies(company_id)
        anomalies += detect_cashflow_anomalies(company_id)
        
    except Exception as e:
        return{
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0},
            "anomalies": [],
            "error": str(e)
        }

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda x: severity_rank.get(x["severity"], 2))

    return {
        "summary": {
            "total": len(anomalies),
            "high": sum(1 for a in anomalies if a["severity"] == "high"),
            "medium": sum(1 for a in anomalies if a["severity"] == "medium"),
            "low": sum(1 for a in anomalies if a["severity"] == "low"),
        },
        "anomalies": anomalies
    }