import streamlit as st
from api_client import get_overview
from config import CURRENCY_SYMBOL

def show():
    st.title("Executive Overview")
    data = get_overview()
    if not data:
        st.error("Could not load overview data."); return
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
    c3.metric("Top Channel", sal["top_channel"].title())
    c4.metric("Revenue Trend", sal["revenue_trend"].replace("_"," ").title())
    st.markdown("---")
    st.subheader("Marketing")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Ad Spend", f"{CURRENCY_SYMBOL}{mkt['total_spend']:,.0f}")
    c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mkt['total_attributed']:,.0f}")
    c3.metric("Overall ROI", f"{mkt['overall_roi']:.2f}x")
    c4.metric("Best Campaign", mkt["best_campaign"])
    st.markdown("---")
    st.subheader("Customers")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Active Customers", f"{cust['active_customers']}")
    c2.metric("Repeat Rate", f"{cust['repeat_rate']:.1f}%")
    c3.metric("High Churn Risk", f"{cust['churn_risk_high']} customers")
    c4.metric("Segments", ", ".join(cust["segments"].keys()))
    st.markdown("---")
    st.subheader("Quick actions")
    c1,c2,c3 = st.columns(3)
    if c1.button("💬 Ask about profit"): st.session_state.page = "chat"; st.rerun()
    if c2.button("📈 View top products"): st.session_state.page = "sales"; st.rerun()
    if c3.button("📊 Check marketing ROI"): st.session_state.page = "sales"; st.rerun()
