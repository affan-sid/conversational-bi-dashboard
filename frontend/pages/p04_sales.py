import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from header_footer import render_header, render_footer
import pandas as pd
from api_client import get_sales, get_marketing
from config import currency_symbol, PERIOD_OPTIONS, DEFAULT_PERIOD, PERIOD_API_MAP

def show():
    SYM = currency_symbol(st.session_state.get("currency", "CAD"))
    render_header("Sales & Marketing")
    period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))
    period_api = PERIOD_API_MAP.get(period, "last_3_months")
    sales_data = get_sales(period_api); mkt_data = get_marketing(period_api)
    if not sales_data: st.error("Could not load data."); return
    if sales_data.get("has_data") is False:
        st.info("📁 No sales or service data uploaded yet. Upload your CSV to see this dashboard.")
        if st.button("Go to Upload →", key="sales_upload_btn"):
            st.session_state.page = "upload"; st.rerun()
        return

    sk = sales_data["kpis"]
    mk = mkt_data.get("kpis", {}) if mkt_data and mkt_data.get("has_data") else {}

    has_products = bool(sales_data.get("top_products"))
    has_services = bool(sales_data.get("top_services"))

    st.subheader("Sales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders / Bookings", f"{sk['total_orders']:,}")
    c2.metric("Avg Order Value", f"{SYM}{sk['avg_order_value']:.2f}")
    c3.metric("Total Revenue", f"{SYM}{sk['total_revenue']:,.0f}")
    c4.metric("Return Rate", f"{sk.get('return_rate', 0):.1f}%")

    # Show product vs service revenue split when company has both
    prod_rev = sk.get("product_revenue", 0)
    svc_rev  = sk.get("service_revenue", 0)
    if prod_rev > 0 and svc_rev > 0:
        st.markdown("---")
        st.subheader("Revenue split")
        r1, r2 = st.columns(2)
        r1.metric("Product Revenue", f"{SYM}{prod_rev:,.0f}")
        r2.metric("Service Revenue", f"{SYM}{svc_rev:,.0f}")

    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Revenue by channel")
        if sales_data.get("revenue_by_channel"):
            df_ch = pd.DataFrame(sales_data["revenue_by_channel"]).set_index("channel")
            st.bar_chart(df_ch["revenue"])
            for row in sales_data["revenue_by_channel"]:
                st.caption(f"• {row['channel'].title()}: {row['orders']:,} orders — {SYM}{row['revenue']:,.0f}")
        else:
            st.info("No channel data for this period.")

    with c_right:
        if has_products and has_services:
            # Both: show products in right column, services below
            st.subheader("Top products")
            df_prod = pd.DataFrame(sales_data["top_products"]).set_index("product_name")
            st.bar_chart(df_prod["revenue"])
            for row in sales_data["top_products"]:
                st.caption(f"• {row['product_name']}: {row['units_sold']:,} units — {SYM}{row['revenue']:,.0f}")
        elif has_products:
            st.subheader("Top products")
            df_prod = pd.DataFrame(sales_data["top_products"]).set_index("product_name")
            st.bar_chart(df_prod["revenue"])
            for row in sales_data["top_products"]:
                st.caption(f"• {row['product_name']}: {row['units_sold']:,} units — {SYM}{row['revenue']:,.0f}")
        elif has_services:
            st.subheader("Top services")
            df_svc = pd.DataFrame(sales_data["top_services"]).set_index("service_name")
            st.bar_chart(df_svc["revenue"])
            for row in sales_data["top_services"]:
                st.caption(f"• {row['service_name']}: {row['total_sessions']:,} sessions — {SYM}{row['revenue']:,.0f}")

    # If both products and services, show services as a separate full-width section
    if has_products and has_services:
        st.markdown("---")
        st.subheader("Top services")
        df_svc = pd.DataFrame(sales_data["top_services"]).set_index("service_name")
        s_left, s_right = st.columns(2)
        with s_left:
            st.bar_chart(df_svc["revenue"])
        with s_right:
            for row in sales_data["top_services"]:
                st.caption(f"• {row['service_name']}: {row['total_sessions']:,} sessions — {SYM}{row['revenue']:,.0f}")

    st.markdown("---")
    st.subheader("Monthly revenue trend")
    if sales_data.get("monthly_revenue"):
        df_rev = pd.DataFrame(sales_data["monthly_revenue"]).set_index("month")
        st.line_chart(df_rev["revenue"])
    else:
        st.info("No revenue trend data for this period.")

    st.markdown("---")
    st.subheader("Marketing")
    if mk:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Ad Spend", f"{SYM}{mk['total_spend']:,.0f}")
        c2.metric("Attributed Revenue", f"{SYM}{mk['total_attributed']:,.0f}")
        c3.metric("Overall ROI", f"{mk['overall_roi']:.2f}x")
        c4.metric("Cost per Acquisition", f"{SYM}{mk['cpa']:.2f}")
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
                df_d["spend"]   = df_d["spend"].apply(lambda x: f"{SYM}{x:,.0f}")
                df_d["revenue"] = df_d["revenue"].apply(lambda x: f"{SYM}{x:,.0f}")
                df_d["roi"]     = df_d["roi"].apply(lambda x: f"{x:.2f}x")
                df_d.columns = ["Campaign","Spend","Revenue","ROI","Conversions"]
                st.dataframe(df_d, use_container_width=True, hide_index=True)
            else:
                st.info("No campaign data available.")
    else:
        st.info("No marketing data available.")

    render_footer()
