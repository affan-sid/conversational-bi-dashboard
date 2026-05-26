import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer, render_empty_state
from api_client import get_overview
from config import CURRENCY_SYMBOL

def show():
    import streamlit as st
    st.markdown("""
<style>
@media (max-width: 480px) {
    [data-testid="stMainBlockContainer"] { padding: 12px 10px !important; }
    [data-testid="stMetric"] { min-width: 0 !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 17px !important; }
    h3 { font-size: 15px !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 140px !important; flex: 1 !important; }
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] { padding: 16px 12px !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; }
}
/* Accessibility — improved text contrast */
[data-testid="stMetricLabel"] { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: #F4F1EB !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
/* Chart labels contrast */
.element-container p { color: #C8C8D8 !important; }
/* Selectbox contrast */
[data-testid="stSelectbox"] label { color: #C8C8D8 !important; font-size: 13px !important; }
[data-testid="stSelectbox"] > div > div {
    background: #1C1A3A !important;
    border-color: rgba(123,92,245,0.3) !important;
    color: #F4F1EB !important;
}
/* File uploader contrast */
[data-testid="stFileUploader"] label { color: #C8C8D8 !important; }
/* Dataframe contrast */
[data-testid="stDataFrame"] { border: 1px solid rgba(123,92,245,0.15) !important; }
/* Focus indicators for keyboard navigation */
button:focus, input:focus, select:focus {
    outline: 2px solid #7B5CF5 !important;
    outline-offset: 2px !important;
}
</style>
""", unsafe_allow_html=True)
    render_header("Executive Overview")
    data = get_overview()
    if not data:
        render_empty_state()
        return
    fin = data["finance"]; sal = data["sales"]; mkt = data["marketing"]; cust = data["customers"]
    for alert in data.get("alerts", []):
        if alert["level"] == "high": st.error(f"🔴 {alert['message']}")
        elif alert["level"] == "medium": st.warning(f"🟡 {alert['message']}")
        else: st.info(f"🔵 {alert['message']}")
    st.markdown("---")
    st.subheader("Finance")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Revenue", f"{CURRENCY_SYMBOL}{fin['total_revenue']:,.2f}")
    c2.metric("Total Expenses", f"{CURRENCY_SYMBOL}{fin['total_expenses']:,.2f}")
    c3.metric("Net Profit", f"{CURRENCY_SYMBOL}{fin['net_profit']:,.2f}")
    c4.metric("Cash Runway", f"{fin['cash_runway_months']:.1f} months",
              delta="⚠ Below 3 months" if fin["cash_runway_months"] < 3 else None, delta_color="inverse")
    st.markdown("---")
    st.subheader("Sales")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Orders", f"{sal['total_orders']:,}")
    c2.metric("Avg Order Value", f"{CURRENCY_SYMBOL}{sal['avg_order_value']:,.2f}")
    c3.metric("Top Channel", sal["top_channel"].title())
    c4.metric("Revenue Trend", sal["revenue_trend"].replace("_"," ").title())
    st.markdown("---")
    st.subheader("Marketing")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Ad Spend", f"{CURRENCY_SYMBOL}{mkt['total_spend']:,.2f}")
    c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mkt['total_attributed']:,.2f}")
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
    render_footer()