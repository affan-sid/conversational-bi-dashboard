"""
Anomaly Detection Module (D4)

Detects unusual patterns in business data using:
  - Z-score for time-series spikes/drops (revenue, expenses, cash flow)
  - Isolation Forest for multivariate marketing anomalies
  - Rule-based checks for data quality issues

Returns structured anomaly objects consumed by /api/anomalies endpoint
and the Overview alert panel.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest
from scipy import stats

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

# Thresholds
_ZSCORE_HIGH = 3.0
_ZSCORE_MEDIUM = 2.0
_IF_CONTAMINATION = 0.05   # expect ~5% outliers in marketing data


# ── HELPERS ───────────────────────────────────────────────────────

def _load(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


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
    }


def _zscore_scan(series: pd.Series, dates: pd.Series,
                 domain: str, metric: str, unit: str = "") -> list:
    """Apply Z-score to a time series, return anomaly dicts for outliers."""
    results = []
    if len(series) < 7:
        return results
    if series.std() < 1e-6:  # constant series — no anomalies possible
        return results

    z_scores = np.abs(stats.zscore(series.values, nan_policy="omit"))
    mean_val = float(series.mean())

    for z, val, date in zip(z_scores, series.values, dates):
        if np.isnan(z) or z < _ZSCORE_MEDIUM:
            continue
        val = float(val)
        direction = "spike" if val > mean_val else "drop"
        dev_pct = ((val - mean_val) / mean_val * 100) if mean_val != 0 else 0
        label = metric.replace("_", " ").title()
        results.append(_anomaly(
            domain=domain,
            atype=f"{metric}_{direction}",
            severity=_severity(z),
            message=f"{label} {direction} of {abs(dev_pct):.1f}% on {date} "
                    f"(actual {unit}{val:,.0f} vs avg {unit}{mean_val:,.0f})",
            date=str(date),
            value=val,
            expected=mean_val,
            deviation_pct=dev_pct,
            z_score=z,
            method="zscore",
            unit=unit,
        ))

    return results


# ── DETECTORS ─────────────────────────────────────────────────────

def detect_revenue_anomalies() -> list:
    """Detect daily revenue spikes/drops from completed orders."""
    df = _load("orders.csv")
    if df.empty:
        return []

    df["order_date"] = pd.to_datetime(df["order_date"])
    df = df[df["status"].str.lower() == "completed"]

    daily = (
        df.groupby("order_date")["total_amount"]
        .sum()
        .reset_index()
        .sort_values("order_date")
    )

    return _zscore_scan(
        series=daily["total_amount"],
        dates=daily["order_date"].dt.strftime("%Y-%m-%d"),
        domain="sales",
        metric="daily_revenue",
        unit="$",
    )


def detect_expense_anomalies() -> list:
    """Detect unusual expense amounts within each category."""
    df = _load("expenses.csv")
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    results = []

    for category, group in df.groupby("expense_category"):
        group = group.sort_values("date")
        if len(group) < 5:
            continue
        metric = category.lower().replace(" ", "_") + "_expense"
        results.extend(_zscore_scan(
            series=group["amount"],
            dates=group["date"].dt.strftime("%Y-%m-%d"),
            domain="finance",
            metric=metric,
            unit="$",
        ))

    return results


def detect_marketing_anomalies() -> list:
    """
    Two-pronged approach:
      1. Rule-based: flag rows where conversions > clicks (impossible IRL).
      2. Isolation Forest on (spend, conversions, revenue_attributed).
      3. Z-score on aggregated daily spend.
    """
    df = _load("marketing_performance.csv")
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    results = []

    # --- Rule: conversions cannot exceed clicks ---
    bad = df[df["conversions"] > df["clicks"]]
    if not bad.empty:
        results.append(_anomaly(
            domain="marketing",
            atype="data_quality_issue",
            severity="medium",
            message=f"{len(bad)} marketing records where conversions exceed clicks — "
                    "likely a data ingestion error.",
            date=None,
            value=len(bad),
            expected=0,
            deviation_pct=None,
            z_score=None,
            method="rule",
            unit="rows",
        ))

    # --- Isolation Forest on multivariate marketing metrics ---
    features_cols = ["spend", "conversions", "revenue_attributed"]
    features = df[features_cols].dropna()
    if len(features) >= 20:
        clf = IsolationForest(
            contamination=_IF_CONTAMINATION,
            random_state=42,
            n_estimators=100,
        )
        preds = clf.fit_predict(features)
        scores = clf.decision_function(features)  # more negative = more anomalous

        for idx in np.where(preds == -1)[0]:
            row = df.iloc[idx]
            sev = "high" if scores[idx] < -0.15 else "medium"
            results.append(_anomaly(
                domain="marketing",
                atype="marketing_pattern_anomaly",
                severity=sev,
                message=(
                    f"Unusual marketing pattern on {row['date'].strftime('%Y-%m-%d')}: "
                    f"spend=${row['spend']:.0f}, conversions={row['conversions']}, "
                    f"revenue=${row['revenue_attributed']:.0f}"
                ),
                date=row["date"].strftime("%Y-%m-%d"),
                value=float(row["spend"]),
                expected=float(features["spend"].mean()),
                deviation_pct=None,
                z_score=None,
                method="isolation_forest",
                unit="$",
            ))

    # --- Z-score on daily ad spend ---
    daily_spend = (
        df.groupby("date")["spend"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    results.extend(_zscore_scan(
        series=daily_spend["spend"],
        dates=daily_spend["date"].dt.strftime("%Y-%m-%d"),
        domain="marketing",
        metric="daily_spend",
        unit="$",
    ))

    return results


def detect_cashflow_anomalies() -> list:
    """Detect unusual day-over-day cash balance changes."""
    df = _load("cash_balances.csv")
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["balance_change"] = df["closing_balance"].diff()
    df = df.dropna(subset=["balance_change"])

    return _zscore_scan(
        series=df["balance_change"],
        dates=df["date"].dt.strftime("%Y-%m-%d"),
        domain="finance",
        metric="cash_balance_change",
        unit="$",
    )


# ── MAIN ENTRY POINT ──────────────────────────────────────────────

def run_all_detectors(company_id: int = 1) -> dict:
    """
    Run all anomaly detectors and return a combined, severity-sorted result.

    Returns:
        {
            "summary": {"total": int, "high": int, "medium": int, "low": int},
            "anomalies": [list of anomaly dicts, sorted high → low severity]
        }
    """
    all_anomalies = []
    all_anomalies.extend(detect_revenue_anomalies())
    all_anomalies.extend(detect_expense_anomalies())
    all_anomalies.extend(detect_marketing_anomalies())
    all_anomalies.extend(detect_cashflow_anomalies())

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    all_anomalies.sort(key=lambda x: severity_rank.get(x["severity"], 2))

    counts = {"high": 0, "medium": 0, "low": 0}
    for a in all_anomalies:
        counts[a["severity"]] = counts.get(a["severity"], 0) + 1

    return {
        "summary": {
            "total": len(all_anomalies),
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
        },
        "anomalies": all_anomalies,
    }
