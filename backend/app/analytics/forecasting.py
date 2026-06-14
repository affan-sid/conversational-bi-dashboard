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


def _resample_weekly(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """Aggregate daily rows into weekly bins (week-ending Sunday, sum)."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    weekly = (
        df.set_index(date_col)[value_col]
        .resample("W")
        .sum()
        .reset_index()
    )
    weekly.columns = [date_col, value_col]
    return weekly.dropna().reset_index(drop=True)


def _compute_metrics(values: np.ndarray, fitted: np.ndarray) -> dict:
    residuals = values - fitted
    r2   = float(r2_score(values, fitted))
    rmse = float(np.sqrt(mean_squared_error(values, fitted)))
    mae  = float(mean_absolute_error(values, fitted))
    nonzero = np.abs(values) > 1e-6
    mape = (
        float(np.mean(np.abs(residuals[nonzero] / values[nonzero])) * 100)
        if nonzero.any() else None
    )
    return {
        "r2":   round(r2, 3),
        "rmse": round(rmse, 2),
        "mae":  round(mae, 2),
        "mape": round(mape, 2) if mape is not None else None,
    }


def _linear_forecast(values: np.ndarray, n_forecast: int, allow_negative: bool = False):
    """
    OLS baseline: fit LinearRegression on equally-spaced values, project n_forecast steps.
    Returns (forecast, lower_95, upper_95, metrics, trend_pct).
    """
    X_hist = np.arange(len(values)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(X_hist, values)

    y_fitted = model.predict(X_hist)
    res_std = float(np.std(values - y_fitted))
    metrics = _compute_metrics(values, y_fitted)

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

    baseline  = float(model.predict([[len(values) - 1]])[0])
    end_val   = float(model.predict([[len(values) + n_forecast - 1]])[0])
    trend_pct = round((end_val - baseline) / abs(baseline) * 100, 1) if abs(baseline) > 1 else 0.0

    return forecast, lower, upper, metrics, trend_pct


def _sarima_forecast(values: np.ndarray, n_forecast: int, allow_negative: bool = False):
    """
    Seasonal ARIMA (1,1,1)(1,0,1,4): captures trend differencing and weekly-to-monthly
    seasonality (period 4 ≈ 4 weeks per month).
    Returns (forecast, lower_95, upper_95, metrics, trend_pct) or raises on failure.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    model = SARIMAX(
        values,
        order=(1, 1, 1),
        seasonal_order=(1, 0, 1, 4),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    res = model.fit(disp=False)

    metrics = _compute_metrics(values, res.fittedvalues)

    fc_obj = res.get_forecast(steps=n_forecast)
    fc_mean = fc_obj.predicted_mean
    ci = fc_obj.conf_int(alpha=0.05)

    if allow_negative:
        forecast = [round(float(v), 2) for v in fc_mean]
        lower    = [round(float(v), 2) for v in ci.iloc[:, 0]]
    else:
        forecast = [round(max(0.0, float(v)), 2) for v in fc_mean]
        lower    = [round(max(0.0, float(v)), 2) for v in ci.iloc[:, 0]]
    upper = [round(float(v), 2) for v in ci.iloc[:, 1]]

    baseline  = float(values[-1])
    end_val   = float(fc_mean.iloc[-1])
    trend_pct = round((end_val - baseline) / abs(baseline) * 100, 1) if abs(baseline) > 1 else 0.0

    return forecast, lower, upper, metrics, trend_pct


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE FORECAST  (weekly bins + SARIMA alongside OLS)
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
    df = df[df["day"] >= cutoff].copy()

    # ── aggregate daily → weekly to smooth high-frequency transactional noise ──
    weekly = _resample_weekly(df, "day", "revenue")
    if len(weekly) < 4:
        return {"error": "Need at least 4 weeks of completed sales data for forecasting."}

    weeks_ahead = max(1, round(days_ahead / 7))
    values = weekly["revenue"].values.astype(float)

    # OLS baseline
    ols_fc, ols_lo, ols_hi, ols_metrics, ols_trend = _linear_forecast(values, weeks_ahead)

    # Seasonal ARIMA (requires ≥ 8 weeks so the seasonal period of 4 has two full cycles)
    sarima_fc = sarima_lo = sarima_hi = sarima_metrics = sarima_trend = None
    if len(weekly) >= 8:
        try:
            sarima_fc, sarima_lo, sarima_hi, sarima_metrics, sarima_trend = _sarima_forecast(
                values, weeks_ahead
            )
        except Exception:
            pass

    # Primary forecast: SARIMA when available, OLS as fallback
    if sarima_fc is not None:
        fc, lo, hi, metrics, trend_pct = sarima_fc, sarima_lo, sarima_hi, sarima_metrics, sarima_trend
        model_name = "sarima"
    else:
        fc, lo, hi, metrics, trend_pct = ols_fc, ols_lo, ols_hi, ols_metrics, ols_trend
        model_name = "linear_regression"

    last_date = weekly["day"].max()
    historical = [
        {"date": row["day"].strftime("%Y-%m-%d"), "value": round(float(row["revenue"]), 2)}
        for _, row in weekly.iterrows()
    ]
    forecast = [
        {
            "date": (last_date + timedelta(days=7 * (i + 1))).strftime("%Y-%m-%d"),
            "value": fc[i], "lower": lo[i], "upper": hi[i],
        }
        for i in range(weeks_ahead)
    ]

    trend = "up" if trend_pct > 0 else "down"
    r2 = metrics["r2"]
    return {
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "trend_pct": trend_pct,
        "metrics": metrics,
        "ols_metrics": ols_metrics,
        "r2_score": r2,
        "model": model_name,
        "weeks_ahead": weeks_ahead,
        "days_ahead": days_ahead,
        "summary": (
            f"Weekly revenue is forecast to {'increase' if trend == 'up' else 'decrease'} "
            f"by {abs(trend_pct):.1f}% over the next {weeks_ahead} weeks "
            f"({model_name.upper()}: R²={r2:.3f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}"
            + (f", MAPE={metrics['mape']:.1f}%" if metrics['mape'] is not None else "")
            + f"; OLS baseline R²={ols_metrics['r2']:.3f})."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CASH FLOW FORECAST  (weekly bins + SARIMA alongside OLS)
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
    df = df[df["day"] >= cutoff].copy()

    # ── aggregate daily → weekly to smooth high-frequency transactional noise ──
    weekly = _resample_weekly(df, "day", "cashflow")
    if len(weekly) < 4:
        return {"error": "Need at least 4 weeks of cash flow data for forecasting."}

    weeks_ahead = max(1, round(days_ahead / 7))
    values = weekly["cashflow"].values.astype(float)

    # OLS baseline (allow_negative=True — cash flow can be negative)
    ols_fc, ols_lo, ols_hi, ols_metrics, ols_trend = _linear_forecast(
        values, weeks_ahead, allow_negative=True
    )

    sarima_fc = sarima_lo = sarima_hi = sarima_metrics = sarima_trend = None
    if len(weekly) >= 8:
        try:
            sarima_fc, sarima_lo, sarima_hi, sarima_metrics, sarima_trend = _sarima_forecast(
                values, weeks_ahead, allow_negative=True
            )
        except Exception:
            pass

    if sarima_fc is not None:
        fc, lo, hi, metrics, trend_pct = sarima_fc, sarima_lo, sarima_hi, sarima_metrics, sarima_trend
        model_name = "sarima"
    else:
        fc, lo, hi, metrics, trend_pct = ols_fc, ols_lo, ols_hi, ols_metrics, ols_trend
        model_name = "linear_regression"

    last_date = weekly["day"].max()
    historical = [
        {"date": row["day"].strftime("%Y-%m-%d"), "value": round(float(row["cashflow"]), 2)}
        for _, row in weekly.iterrows()
    ]
    forecast = [
        {
            "date": (last_date + timedelta(days=7 * (i + 1))).strftime("%Y-%m-%d"),
            "value": fc[i], "lower": lo[i], "upper": hi[i],
        }
        for i in range(weeks_ahead)
    ]

    trend = "up" if trend_pct > 0 else "down"
    r2 = metrics["r2"]
    return {
        "historical": historical,
        "forecast": forecast,
        "trend": trend,
        "trend_pct": trend_pct,
        "metrics": metrics,
        "ols_metrics": ols_metrics,
        "r2_score": r2,
        "model": model_name,
        "weeks_ahead": weeks_ahead,
        "days_ahead": days_ahead,
        "summary": (
            f"Weekly cash flow is forecast to {'improve' if trend == 'up' else 'decline'} "
            f"by {abs(trend_pct):.1f}% over the next {weeks_ahead} weeks "
            f"({model_name.upper()}: R²={r2:.3f}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}"
            + (f", MAPE={metrics['mape']:.1f}%" if metrics['mape'] is not None else "")
            + f"; OLS baseline R²={ols_metrics['r2']:.3f})."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE FORECAST (monthly — OLS, already aggregated at source)
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
