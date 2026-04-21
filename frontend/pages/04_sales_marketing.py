import streamlit as st
import pandas as pd
from api_client import get_sales, get_marketing
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD

st.title("Sales & Marketing")

# ── PERIOD SELECTOR ──────────────────────────────────────
period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))

sales_data = get_sales(period)
mkt_data   = get_marketing(period)

if not sales_data or not mkt_data:
    st.error("Could not load sales/marketing data.")
    st.stop()

sk = sales_data["kpis"]
mk = mkt_data["kpis"]

# ── SALES KPI CARDS ──────────────────────────────────────
st.subheader("Sales")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Orders",     f"{sk['total_orders']:,}")
c2.metric("Returned Orders",  f"{sk['returned_orders']:,}")
c3.metric("Avg Order Value",  f"{CURRENCY_SYMBOL}{sk['avg_order_value']:.2f}")
c4.metric("Return Rate",      f"{sk['return_rate']:.1f}%")

st.markdown("---")

# ── REVENUE BY CHANNEL + TOP PRODUCTS ────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Revenue by channel")
    df_ch = pd.DataFrame(sales_data["revenue_by_channel"])
    df_ch = df_ch.set_index("channel")
    st.bar_chart(df_ch["revenue"])

    st.caption("Order count by channel")
    for row in sales_data["revenue_by_channel"]:
        st.caption(f"• {row['channel'].title()}: {row['orders']:,} orders — {CURRENCY_SYMBOL}{row['revenue']:,}")

with col_right:
    st.subheader("Top products")
    df_prod = pd.DataFrame(sales_data["top_products"])
    df_prod = df_prod.set_index("product_name")
    st.bar_chart(df_prod["revenue"])

    st.caption("Units sold")
    for row in sales_data["top_products"]:
        st.caption(f"• {row['product_name']}: {row['units_sold']:,} units — {CURRENCY_SYMBOL}{row['revenue']:,}")

st.markdown("---")

# ── MONTHLY REVENUE TREND ────────────────────────────────
st.subheader("Monthly revenue trend")
df_rev = pd.DataFrame(sales_data["monthly_revenue"])
df_rev = df_rev.set_index("month")
st.line_chart(df_rev["revenue"])

st.markdown("---")

# ── MARKETING KPI CARDS ──────────────────────────────────
st.subheader("Marketing")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Ad Spend",     f"{CURRENCY_SYMBOL}{mk['total_spend']:,.0f}")
c2.metric("Attributed Revenue", f"{CURRENCY_SYMBOL}{mk['total_attributed']:,.0f}")
c3.metric("Overall ROI",        f"{mk['overall_roi']:.2f}x")
c4.metric("Cost per Acquisition", f"{CURRENCY_SYMBOL}{mk['cpa']:.2f}")

c1, c2, c3 = st.columns(3)
c1.metric("Total Impressions", f"{mk['total_impressions']:,}")
c2.metric("Total Clicks",      f"{mk['total_clicks']:,}")
c3.metric("Click-through Rate", f"{mk['ctr']:.2f}%")

st.markdown("---")

# ── CAMPAIGN ROI TABLE + CHART ────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Campaign ROI")
    df_camp = pd.DataFrame(mkt_data["campaign_performance"])
    df_camp = df_camp.set_index("campaign_name")
    st.bar_chart(df_camp["roi"])

with col_right:
    st.subheader("Campaign details")
    df_display = pd.DataFrame(mkt_data["campaign_performance"])
    df_display["spend"]   = df_display["spend"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,}")
    df_display["revenue"] = df_display["revenue"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,}")
    df_display["roi"]     = df_display["roi"].apply(lambda x: f"{x:.2f}x")
    df_display.columns    = ["Campaign", "Spend", "Revenue", "ROI", "Conversions"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

st.markdown("---")

# ── SPEND VS REVENUE TREND ───────────────────────────────
st.subheader("Ad spend vs attributed revenue")
df_spend = pd.DataFrame(mkt_data["spend_trend"])
df_spend = df_spend.set_index("month")
st.line_chart(df_spend[["spend", "revenue"]])
