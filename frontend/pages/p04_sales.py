import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer, render_empty_state
import pandas as pd
from api_client import get_sales, get_marketing
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD

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
    render_header("Sales & Marketing")
    period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))
    sales_data = get_sales(period); mkt_data = get_marketing(period)
    if not sales_data or not mkt_data: st.error("Could not load data."); return
    sk = sales_data["kpis"]; mk = mkt_data["kpis"]
    st.subheader("Sales")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Orders", f"{sk['total_orders']:,}")
    c2.metric("Returned Orders", f"{sk['returned_orders']:,}")
    c3.metric("Avg Order Value", f"{CURRENCY_SYMBOL}{sk['avg_order_value']:.2f}")
    c4.metric("Return Rate", f"{sk['return_rate']:.1f}%")
    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Revenue by channel")
        df_ch = pd.DataFrame(sales_data["revenue_by_channel"]).set_index("channel")
        st.bar_chart(df_ch["revenue"])
        for row in sales_data["revenue_by_channel"]:
            st.caption(f"• {row['channel'].title()}: {row['orders']:,} orders — {CURRENCY_SYMBOL}{row['revenue']:,}")
    with c_right:
        st.subheader("Top products")
        df_prod = pd.DataFrame(sales_data["top_products"]).set_index("product_name")
        st.bar_chart(df_prod["revenue"])
        for row in sales_data["top_products"]:
            st.caption(f"• {row['product_name']}: {row['units_sold']:,} units — {CURRENCY_SYMBOL}{row['revenue']:,}")
    st.markdown("---")
    st.subheader("Monthly revenue trend")
    df_rev = pd.DataFrame(sales_data["monthly_revenue"]).set_index("month")
    st.line_chart(df_rev["revenue"])
    st.markdown("---")
    st.subheader("Marketing")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Ad Spend", f"{CURRENCY_SYMBOL}{mk['total_spend']:,.2f}")
    c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mk['total_attributed']:,.2f}")
    c3.metric("Overall ROI", f"{mk['overall_roi']:.2f}x")
    c4.metric("Cost per Acquisition", f"{CURRENCY_SYMBOL}{mk['cpa']:.2f}")
    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Campaign ROI")
        df_camp = pd.DataFrame(mkt_data["campaign_performance"]).set_index("campaign_name")
        st.bar_chart(df_camp["roi"])
    with c_right:
        st.subheader("Campaign details")
        df_d = pd.DataFrame(mkt_data["campaign_performance"])
        df_d["spend"] = df_d["spend"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,}")
        df_d["revenue"] = df_d["revenue"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,}")
        df_d["roi"] = df_d["roi"].apply(lambda x: f"{x:.2f}x")
        df_d.columns = ["Campaign","Spend","Revenue","ROI","Conversions"]
        st.dataframe(df_d, use_container_width=True, hide_index=True)
    render_footer()