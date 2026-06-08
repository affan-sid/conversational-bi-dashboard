import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sqlalchemy import text
from datetime import timedelta

from backend.app.services.db import engine


def _fetch(sql: str, params: dict) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def _linear_forecast(values: np.ndarray, n_forecast: int, allow_negative: bool = False):
    """
    Fit a LinearRegression on equally-spaced values and project n_forecast steps ahead.
    Returns (forecast, lower_95, upper_95, metrics, trend_pct).

    metrics dict contains: r2, rmse, mae, mape
    allow_negative=True for cash flow where negative values are meaningful.
    """
    X_hist = np.arange(len(values)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(X_hist, values)

    y_hist_pred = model.predict(X_hist)
    residuals = values - y_hist_pred
    res_std = float(np.std(residuals))

    r2   = float(r2_score(values, y_hist_pred))
    rmse = float(np.sqrt(mean_squared_error(values, y_hist_pred)))
    mae  = float(mean_absolute_error(values, y_hist_pred))
    # MAPE: exclude near-zero actuals to avoid division instability
    nonzero_mask = np.abs(values) > 1e-6
    mape = (
        float(np.mean(np.abs(residuals[nonzero_mask] / values[nonzero_mask])) * 100)
        if nonzero_mask.any() else None
    )

    metrics = {
        "r2":   round(r2, 3),
        "rmse": round(rmse, 2),
        "mae":  round(mae, 2),
        "mape": round(mape, 2) if mape is not None else None,
    }

    X_future = np.arange(len(values), len(values) + n_forecast).reshape(-1, 1)
    y_future = model.predict(X_future).tolist()

    ci = 1.96 * res_std
    if allow_negative:
        forecast = [round(float(v), 2) for v in y_future]
        lower    = [round(float(v) - ci, 2) for v in y_future]
    else:
        forecast = [round(max(0.0, float(v)), 2) for v in y_future]
        lower    = [round(max(0.0, float(v) - ci), 2) for v in y_future]
    upper = [round(float(v) + ci, 2) for v in y_future]

    baseline = float(model.predict([[len(values) - 1]])[0])
    end_val  = float(model.predict([[len(values) + n_forecast - 1]])[0])
    trend_pct = round((end_val - baseline) / abs(baseline) * 100, 1) if abs(baseline) > 1 else 0.0

    return forecast, lower, upper, metrics, trend_pct


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE FORECAST
# ─────────────────────────────────────────────────────────────────────────────

def forecast_revenue(company_id: int, days_ahead: int = 30) -> dict:
    df = _fetch("""
        SELECT day, SUM(revenue) AS revenue FROM (
            SELECT CAST(order_date AS DATE) AS day, SUM(line_total) AS revenue
            FROM fact_sales
            WHERE status = 'completed' AND company_id = :cid
            GROUP BY CAST(order_date AS DATE)
            UNION ALL
            SELECT CAST(booking_date AS DATE) AS day, SUM(line_total) AS revenue
            FROM fact_service_bookings
            WHERE status = 'completed' AND company_id = :cid
            GROUP BY CAST(booking_date AS DATE)
        ) combined
        GROUP BY day ORDER BY day
    """, {"cid": company_id})

    if df.empty or len(df) < 14:
        return {"error": "Need at least 14 days of completed sales data for forecasting."}

    df["day"] = pd.to_datetime(df["day"])
    cutoff = df["day"].max() - pd.Timedelta(days=90)
    df = df[df["day"] >= cutoff].copy().reset_index(drop=True)

    values = df["revenue"].values.astype(float)
    fc, lo, hi, metrics, trend_pct = _linear_forecast(values, days_ahead)

    last_date = df["day"].max()
    historical = [
        {"date": row["day"].strftime("%Y-%m-%d"), "value": round(float(row["revenue"]), 2)}
        for _, row in df.iterrows()
    ]
    forecast = [
        {
            "date": (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
            "value": fc[i], "lower": lo[i], "upper": hi[i],
        }
        for i in range(days_ahead)
    ]

    trend = "up" if trend_pct > 0 else "down"
    r2 = metrics["r2"]
    return {
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "trend_pct": trend_pct,
        "metrics": metrics,
        "r2_score": r2,
        "model": "linear_regression",
        "days_ahead": days_ahead,
        "summary": (
            f"Revenue is forecast to {'increase' if trend == 'up' else 'decrease'} "
            f"by {abs(trend_pct):.1f}% over the next {days_ahead} days "
            f"(R²={r2:.3f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}"
            + (f", MAPE={metrics['mape']:.1f}%" if metrics['mape'] is not None else "")
            + ")."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CASH FLOW FORECAST
# ─────────────────────────────────────────────────────────────────────────────

def forecast_cashflow(company_id: int, days_ahead: int = 30) -> dict:
    df = _fetch("""
        SELECT CAST(date AS DATE) AS day, SUM(signed_amount) AS cashflow
        FROM fact_cash_flow
        WHERE company_id = :cid
        GROUP BY CAST(date AS DATE)
        ORDER BY day
    """, {"cid": company_id})

    if df.empty or len(df) < 14:
        return {"error": "Need at least 14 days of cash flow data for forecasting."}

    df["day"] = pd.to_datetime(df["day"])
    cutoff = df["day"].max() - pd.Timedelta(days=90)
    df = df[df["day"] >= cutoff].copy().reset_index(drop=True)

    values = df["cashflow"].values.astype(float)
    fc, lo, hi, metrics, trend_pct = _linear_forecast(values, days_ahead, allow_negative=True)

    last_date = df["day"].max()
    historical = [
        {"date": row["day"].strftime("%Y-%m-%d"), "value": round(float(row["cashflow"]), 2)}
        for _, row in df.iterrows()
    ]
    forecast = [
        {
            "date": (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
            "value": fc[i], "lower": lo[i], "upper": hi[i],
        }
        for i in range(days_ahead)
    ]

    trend = "up" if trend_pct > 0 else "down"
    r2 = metrics["r2"]
    return {
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "trend_pct": trend_pct,
        "metrics": metrics,
        "r2_score": r2,
        "model": "linear_regression",
        "days_ahead": days_ahead,
        "summary": (
            f"Daily cash flow is forecast to {'improve' if trend == 'up' else 'decline'} "
            f"by {abs(trend_pct):.1f}% over the next {days_ahead} days "
            f"(R²={r2:.3f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}"
            + (f", MAPE={metrics['mape']:.1f}%" if metrics['mape'] is not None else "")
            + ")."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE FORECAST (monthly)
# ─────────────────────────────────────────────────────────────────────────────

def forecast_expenses(company_id: int, months_ahead: int = 3) -> dict:
    df = _fetch("""
        SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, SUM(amount) AS expenses
        FROM fact_expenses
        WHERE company_id = :cid
        GROUP BY DATE_TRUNC('month', CAST(date AS DATE))
        ORDER BY month
    """, {"cid": company_id})

    if df.empty or len(df) < 3:
        return {"error": "Need at least 3 months of expense data for forecasting."}

    df["month"] = pd.to_datetime(df["month"])
    values = df["expenses"].values.astype(float)
    fc, lo, hi, metrics, trend_pct = _linear_forecast(values, months_ahead)

    last_month = df["month"].max()
    historical = [
        {"date": row["month"].strftime("%Y-%m"), "value": round(float(row["expenses"]), 2)}
        for _, row in df.iterrows()
    ]
    forecast = [
        {
            "date": (last_month + pd.DateOffset(months=i + 1)).strftime("%Y-%m"),
            "value": fc[i], "lower": lo[i], "upper": hi[i],
        }
        for i in range(months_ahead)
    ]

    trend = "up" if trend_pct > 0 else "down"
    r2 = metrics["r2"]
    return {
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "trend_pct": trend_pct,
        "metrics": metrics,
        "r2_score": r2,
        "model": "linear_regression",
        "months_ahead": months_ahead,
        "summary": (
            f"Monthly expenses are forecast to {'rise' if trend == 'up' else 'fall'} "
            f"by {abs(trend_pct):.1f}% over the next {months_ahead} months "
            f"(R²={r2:.3f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}"
            + (f", MAPE={metrics['mape']:.1f}%" if metrics['mape'] is not None else "")
            + ")."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_forecasts(company_id: int, days_ahead: int = 30) -> dict:
    try:
        revenue  = forecast_revenue(company_id, days_ahead=days_ahead)
    except Exception as e:
        revenue  = {"error": str(e)}
    try:
        cashflow = forecast_cashflow(company_id, days_ahead=days_ahead)
    except Exception as e:
        cashflow = {"error": str(e)}
    try:
        expenses = forecast_expenses(company_id, months_ahead=3)
    except Exception as e:
        expenses = {"error": str(e)}

    return {"revenue": revenue, "cashflow": cashflow, "expenses": expenses}
