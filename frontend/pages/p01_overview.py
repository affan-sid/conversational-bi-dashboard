import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
from api_client import get_overview
from config import CURRENCY_SYMBOL

def _no_data_prompt(domain: str = ""):
    st.markdown("---")
    msg = f"No {domain} data uploaded yet." if domain else "No data uploaded yet."
    st.info(f"📁 {msg} Upload your CSV files to see this dashboard.")
    if st.button("Go to Upload →", key=f"upload_btn_{domain}"):
        st.session_state.page = "upload"; st.rerun()


def show():
    render_header("Executive Overview")
    data = get_overview()
    if not data:
        st.error("Could not load overview data."); return
    if data.get("has_data") is False:
        _no_data_prompt(); return
    fin = data["finance"]; sal = data["sales"]; mkt = data["marketing"]; cust = data["customers"]
    for alert in data.get("alerts", []):
        if alert["level"] == "high": st.error(f"🔴 {alert['message']}")
        elif alert["level"] == "medium": st.warning(f"🟡 {alert['message']}")
        else: st.info(f"🔵 {alert['message']}")
    st.markdown("---")
    st.subheader("Finance")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Revenue", f"{CURRENCY_SYMBOL}{fin['total_revenue']:,.0f}")
    c2.metric("Total Expenses", f"{CURRENCY_SYMBOL}{fin['total_expenses']:,.0f}")
    c3.metric("Net Profit", f"{CURRENCY_SYMBOL}{fin['net_profit']:,.0f}")
    c4.metric("Cash Runway", f"{fin['cash_runway_months']:.1f} months",
              delta="⚠ Below 3 months" if fin["cash_runway_months"] < 3 else None, delta_color="inverse")
    st.markdown("---")
    st.subheader("Sales")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Orders", f"{sal['total_orders']:,}")
    c2.metric("Avg Order Value", f"{CURRENCY_SYMBOL}{sal['avg_order_value']:.2f}")
    c3.metric("Top Channel", sal.get("top_channel", "N/A").title())
    c4.metric("Revenue Trend", sal.get("revenue_trend", "stable").replace("_"," ").title())
    st.markdown("---")
    st.subheader("Marketing")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Ad Spend", f"{CURRENCY_SYMBOL}{mkt['total_spend']:,.0f}")
    c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mkt['total_attributed']:,.0f}")
    c3.metric("Overall ROI", f"{mkt['overall_roi']:.2f}x")
    c4.metric("Best Campaign", mkt.get("best_campaign", "N/A"))
    st.markdown("---")
    st.subheader("Customers")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Active Customers", f"{cust['active_customers']}")
    c2.metric("Repeat Rate", f"{cust.get('repeat_rate', 0):.1f}%")
    c3.metric("High Churn Risk", f"{cust.get('churn_risk_high', 0)} customers")
    segs = cust.get("segments", {})
    c4.metric("Segments", ", ".join(segs.keys()) if segs else "N/A")
    st.markdown("---")
    st.subheader("Quick actions")
    c1,c2,c3 = st.columns(3)
    if c1.button("💬 Ask about profit"): st.session_state.page = "chat"; st.rerun()
    if c2.button("📈 View top products"): st.session_state.page = "sales"; st.rerun()
    if c3.button("📊 Check marketing ROI"): st.session_state.page = "sales"; st.rerun()
    render_footer()
