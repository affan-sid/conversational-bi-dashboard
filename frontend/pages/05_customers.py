import streamlit as st
import pandas as pd
from api_client import get_customers
from config import CURRENCY_SYMBOL, PERIOD_OPTIONS, DEFAULT_PERIOD

st.title("Customers")

# ── PERIOD SELECTOR ──────────────────────────────────────
period = st.selectbox("Period", PERIOD_OPTIONS, index=PERIOD_OPTIONS.index(DEFAULT_PERIOD))

data = get_customers(period)
if not data:
    st.error("Could not load customer data.")
    st.stop()

kpis = data["kpis"]

# ── KPI CARDS ────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Customers",  f"{kpis['total_customers']}")
c2.metric("Active Customers", f"{kpis['active_customers']}")
c3.metric("Repeat Rate",      f"{kpis['repeat_rate']:.1f}%",
          delta="Low" if kpis["repeat_rate"] < 30 else None,
          delta_color="inverse")
c4.metric("Churn Rate",       f"{kpis['churn_rate']:.1f}%")

c1, c2 = st.columns(2)
c1.metric("Avg Customer Lifetime Value", f"{CURRENCY_SYMBOL}{kpis['avg_clv']:,.0f}")
c2.metric("New This Period",             f"{kpis['new_this_period']}")

st.markdown("---")

# ── REVENUE BY SEGMENT + GROWTH TREND ────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Revenue by segment")
    # Segments from your real CSV: Retail, SME, Corporate
    df_seg = pd.DataFrame(data["revenue_by_segment"])
    df_seg = df_seg.set_index("segment")
    st.bar_chart(df_seg["revenue"])
    for row in data["revenue_by_segment"]:
        st.caption(f"• {row['segment']}: {row['customers']} customers — {CURRENCY_SYMBOL}{row['revenue']:,}")

with col_right:
    st.subheader("Customer growth")
    df_growth = pd.DataFrame(data["growth_trend"])
    df_growth = df_growth.set_index("month")
    st.line_chart(df_growth[["new_customers", "churned"]])

st.markdown("---")

# ── TOP CUSTOMERS ─────────────────────────────────────────
st.subheader("Top customers by revenue")
df_top = pd.DataFrame(data["top_customers"])
df_top["total_revenue"] = df_top["total_revenue"].apply(lambda x: f"{CURRENCY_SYMBOL}{x:,}")
df_top.columns = ["ID", "Name", "Revenue", "Orders", "Segment"]
st.dataframe(df_top, use_container_width=True, hide_index=True)

st.markdown("---")

# ── CHURN RISK LIST ───────────────────────────────────────
st.subheader("High churn risk customers")
st.caption("Customers with no order in 60+ days and high risk score.")

churn_list = data["churn_risk_list"]
if churn_list:
    for c in churn_list:
        score = c["churn_risk_score"]
        days  = c["last_order_days_ago"]
        color = "🔴" if score >= 0.9 else "🟡"
        st.warning(
            f"{color} **{c['full_name']}** — "
            f"Risk score: {score:.2f} — "
            f"Last order: {days} days ago"
        )
else:
    st.success("No high churn risk customers right now.")
