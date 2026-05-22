import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
import pandas as pd
from api_client import get_finance
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD

def show():
    render_header("Finance Dashboard")
    period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))
    data = get_finance(period)
    if not data: st.error("Could not load finance data."); return
    kpis = data["kpis"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Revenue", f"{CURRENCY_SYMBOL}{kpis['total_revenue']:,.0f}")
    c2.metric("Total Expenses", f"{CURRENCY_SYMBOL}{kpis['total_expenses']:,.0f}")
    c3.metric("Net Profit", f"{CURRENCY_SYMBOL}{kpis['net_profit']:,.0f}")
    c4.metric("Profit Margin", f"{kpis['profit_margin']:.1f}%",
              delta="Low" if kpis["profit_margin"] < 15 else None, delta_color="inverse")
    c1,c2,c3 = st.columns(3)
    c1.metric("Cash in Bank", f"{CURRENCY_SYMBOL}{kpis['cash_in_bank']:,.0f}")
    c2.metric("Monthly Burn Rate", f"{CURRENCY_SYMBOL}{kpis['monthly_burn']:,.0f}")
    c3.metric("Cash Runway", f"{kpis['cash_runway_months']:.1f} months",
              delta="⚠ Critical" if kpis["cash_runway_months"] < 3 else "Healthy",
              delta_color="inverse" if kpis["cash_runway_months"] < 3 else "normal")
    st.markdown("---")
    st.subheader("Revenue vs Expenses")
    df_trend = pd.DataFrame(data["monthly_trend"]).set_index("month")
    st.line_chart(df_trend[["revenue","expenses"]])
    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Expense breakdown")
        df_exp = pd.DataFrame(data["expense_breakdown"]).set_index("category")
        st.bar_chart(df_exp["amount"])
    with c_right:
        st.subheader("Monthly profit trend")
        df_profit = pd.DataFrame(data["monthly_trend"]).set_index("month")
        st.bar_chart(df_profit["profit"])
    st.markdown("---")
    st.subheader("Cash balance trend")
    df_cash = pd.DataFrame(data["cash_trend"]).set_index("date")
    st.area_chart(df_cash["closing_balance"])
    st.caption(f"Monthly burn rate: **{CURRENCY_SYMBOL}{kpis['monthly_burn']:,.0f}** — Runway: **{kpis['cash_runway_months']:.1f} months**")
    render_footer()
