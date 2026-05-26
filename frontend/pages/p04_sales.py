import streamlit as st
import pandas as pd
from api_client import get_sales, get_marketing
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD, PERIOD_API_MAP

def show():
    st.title("Sales & Marketing")
    period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))
    period_api = PERIOD_API_MAP.get(period, "last_3_months")
    sales_data = get_sales(period_api); mkt_data = get_marketing(period_api)
    if not sales_data: st.error("Could not load data."); return
    if sales_data.get("has_data") is False:
        st.info("📁 No sales data uploaded yet. Upload your sales CSV to see this dashboard.")
        if st.button("Go to Upload →", key="sales_upload_btn"):
            st.session_state.page = "upload"; st.rerun()
        return
    sk = sales_data["kpis"]
    mk = mkt_data.get("kpis", {}) if mkt_data and mkt_data.get("has_data") else {}
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
            st.caption(f"• {row['channel'].title()}: {row['orders']:,} orders — {CURRENCY_SYMBOL}{row['revenue']:,.0f}")
    with c_right:
        st.subheader("Top products")
        df_prod = pd.DataFrame(sales_data["top_products"]).set_index("product_name")
        st.bar_chart(df_prod["revenue"])
        for row in sales_data["top_products"]:
            st.caption(f"• {row['product_name']}: {row['units_sold']:,} units — {CURRENCY_SYMBOL}{row['revenue']:,.0f}")
    st.markdown("---")
    st.subheader("Monthly revenue trend")
    if sales_data.get("monthly_revenue"):
        df_rev = pd.DataFrame(sales_data["monthly_revenue"]).set_index("month")
        st.line_chart(df_rev["revenue"])
    else:
        st.info("No revenue trend data for this period.")
    st.markdown("---")
    st.subheader("Marketing")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Ad Spend", f"{CURRENCY_SYMBOL}{mk['total_spend']:,.0f}")
    c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mk['total_attributed']:,.0f}")
    c3.metric("Overall ROI", f"{mk['overall_roi']:.2f}x")
    c4.metric("Cost per Acquisition", f"{CURRENCY_SYMBOL}{mk['cpa']:.2f}")
    st.markdown("---")
    camp_perf = mkt_data.get("campaign_performance", [])
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Campaign ROI")
        if camp_perf:
            df_camp = pd.DataFrame(camp_perf).set_index("campaign_name")
            st.bar_chart(df_camp["roi"])
        else:
            st.info("No campaign data available.")
    with c_right:
        st.subheader("Campaign details")
        if camp_perf:
            df_d = pd.DataFrame(camp_perf)
            df_d["spend"]   = df_d["spend"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,.0f}")
            df_d["revenue"] = df_d["revenue"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,.0f}")
            df_d["roi"]     = df_d["roi"].apply(lambda x: f"{x:.2f}x")
            df_d.columns = ["Campaign","Spend","Revenue","ROI","Conversions"]
            st.dataframe(df_d, use_container_width=True, hide_index=True)
        else:
            st.info("No campaign data available.")
