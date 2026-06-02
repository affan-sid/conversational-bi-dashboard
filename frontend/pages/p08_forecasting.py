import streamlit as st
import pandas as pd
import sys, os

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from header_footer import render_header, render_footer
import api_client as _ac

get_forecasts = _ac.get_forecasts


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _trend_delta(trend: str, pct: float, sym: str = ""):
    label = f"{'+' if pct > 0 else ''}{pct:.1f}%"
    color = "normal" if trend == "up" else "inverse"
    return label, color


def _section(title: str, data: dict, sym: str, x_label: str = "Date"):
    if not data or data.get("error"):
        st.warning(f"⚠ {data.get('error', 'No data available for this forecast.')}")
        return

    trend    = data.get("trend", "up")
    pct      = data.get("trend_pct", 0)
    r2       = data.get("r2_score", 0)
    days     = data.get("days_ahead") or data.get("months_ahead", "—")
    summary  = data.get("summary", "")

    # ── Metric row ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    delta_label, delta_color = _trend_delta(trend, pct)
    c1.metric(
        f"Projected Change ({days} {'days' if 'days_ahead' in data else 'months'})",
        delta_label,
        delta_color if False else None,   # keep it simple — just the label
    )
    c2.metric("Model Accuracy (R²)", f"{r2*100:.0f}%")
    c3.metric("Direction", ("↑ Increasing" if trend == "up" else "↓ Decreasing"))

    # ── Chart ────────────────────────────────────────────────────
    hist = pd.DataFrame(data.get("historical", []))
    fore = pd.DataFrame(data.get("forecast",   []))

    if hist.empty:
        st.info("No historical data to display.")
        return

    hist = hist.rename(columns={"value": "Historical"})
    fore = fore.rename(columns={"value": "Forecast", "lower": "Lower (95% CI)", "upper": "Upper (95% CI)"})

    combined = pd.merge(hist, fore[["date", "Forecast", "Lower (95% CI)", "Upper (95% CI)"]],
                        on="date", how="outer")
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.set_index("date").sort_index()

    # Format values with currency symbol for tooltips
    chart_cols = ["Historical", "Forecast"]
    available  = [c for c in chart_cols if c in combined.columns]
    st.line_chart(combined[available], use_container_width=True)

    # Show CI bounds as a table under an expander
    if not fore.empty and "Lower (95% CI)" in fore.columns:
        with st.expander("Show 95% confidence interval details"):
            display = fore[["date", "Forecast", "Lower (95% CI)", "Upper (95% CI)"]].copy()
            display.columns = [x_label, f"Forecast ({sym})", f"Lower ({sym})", f"Upper ({sym})"]
            st.dataframe(display.set_index(x_label), use_container_width=True)

    if summary:
        st.info(f"📊 {summary}")


# ── PAGE ─────────────────────────────────────────────────────────────────────

def show():
    render_header("Predictive Analytics")

    from config import currency_symbol
    SYM = currency_symbol(st.session_state.get("currency", "CAD"))

    # ── Horizon selector ─────────────────────────────────────────
    col_sel, _ = st.columns([2, 5])
    with col_sel:
        horizon = st.selectbox(
            "Forecast horizon (days)",
            options=[14, 30, 60, 90],
            index=1,
            key="forecast_horizon",
        )

    st.markdown("---")

    with st.spinner(f"Running {horizon}-day forecasts…"):
        data = get_forecasts(days_ahead=horizon)

    if data is None:
        render_footer()
        return

    # ── Revenue ──────────────────────────────────────────────────
    st.subheader("📈 Revenue Forecast")
    _section(f"Revenue — next {horizon} days", data.get("revenue", {}), SYM)

    st.markdown("---")

    # ── Cash Flow ─────────────────────────────────────────────────
    st.subheader("💳 Cash Flow Forecast")
    _section(f"Cash Flow — next {horizon} days", data.get("cashflow", {}), SYM)

    st.markdown("---")

    # ── Expenses ─────────────────────────────────────────────────
    st.subheader("📉 Expense Forecast (Monthly)")
    _section("Expenses — next 3 months", data.get("expenses", {}), SYM, x_label="Month")

    render_footer()
