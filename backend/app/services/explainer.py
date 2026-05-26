import requests
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False

import os
from dotenv import load_dotenv
load_dotenv()

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL   = "gpt-4o-mini"

_IF_CONTAMINATION = 0.05


def _extract_table_name(sql: str) -> str:
    sql_lower = sql.lower()
    if "fact_marketing" in sql_lower:
        return "marketing_performance"
    elif "fact_sales" in sql_lower:
        return "transactions"
    elif "fact_expenses" in sql_lower:
        return "expenses"
    elif "customer_metrics" in sql_lower or "dim_customers" in sql_lower:
        return "customers"
    elif "fact_cash_flow" in sql_lower:
        return "cash_flow"
    return "data"


def _rule_based_action(user_query: str, result: dict = None) -> str:
    """Return a rule-based action suggestion when the LLM is unavailable."""
    q = user_query.lower()
    rows = (result or {}).get("rows", [])
    top_name = str(rows[0][0]) if rows and rows[0] else ""

    if any(w in q for w in ["campaign", "roi", "marketing", "wasting"]):
        if top_name:
            return (
                f"Pause campaign '{top_name}' and run a side-by-side comparison of its cost-per-conversion against your best-performing campaign. "
                f"If its ROI is below 1.0x, reallocate that entire budget to the campaign delivering the highest return — even a partial shift can meaningfully improve your overall marketing efficiency. "
                f"Set a 2-week review window to measure whether the reallocation lifts total revenue before committing to a permanent budget change."
            )
        return (
            "Audit every active campaign this week: list each one's total spend alongside the revenue it directly generated, then calculate a simple ROI (revenue ÷ spend). "
            "Pause any campaign sitting below 1.0x ROI immediately — every dollar spent on a loss-making campaign is a dollar taken away from one that works. "
            "Redirect that freed budget to your single highest-ROI channel and monitor results over the next two weeks."
        )

    if any(w in q for w in ["churn", "at risk", "losing customer"]):
        return (
            "This week, export your list of at-risk customers and segment them by how much revenue each represents — prioritise the top 20% by value first. "
            "Send each segment a personalised message: a loyalty discount, an exclusive early-access offer, or a simple check-in call can recover 20–30% of at-risk accounts before they fully lapse. "
            "Track which outreach method gets the best response rate so you can scale the most effective approach across the broader at-risk list."
        )

    if any(w in q for w in ["revenue", "profit", "drop", "decline"]):
        return (
            "Compare this period's revenue by channel and product against the same period last quarter to pinpoint exactly where the drop occurred. "
            "Once you've identified the underperforming segment, check whether the cause is lower volume, lower prices, or higher returns — each requires a different fix. "
            "In parallel, identify your strongest-performing channel and increase its budget or promotional activity to offset the decline while you address the root cause."
        )

    if any(w in q for w in ["expense", "cost", "spend", "burn"]):
        return (
            "Pull up your expense breakdown for the last 30 days and rank every category by total spend — your top three categories likely account for 70–80% of all costs. "
            "Pick the largest discretionary line item in that top three and negotiate a 10% reduction this month, whether through a supplier discount, a subscription downgrade, or deferred purchasing. "
            "Small cost reductions compound quickly: a 10% cut on a $5,000/month category saves $6,000 per year and extends your cash runway by weeks."
        )

    if any(w in q for w in ["cash", "runway"]):
        return (
            "Calculate your exact runway today: divide your current cash balance by your average monthly burn rate to get how many months you have left. "
            "If that number is below three months, immediately contact your top five customers with outstanding invoices and offer a small early-payment discount to accelerate cash collection. "
            "At the same time, defer all non-essential capital expenditure and review any recurring subscriptions or retainers you can pause — preserving cash now gives you more time to grow revenue rather than scramble for financing."
        )

    if any(w in q for w in ["customer", "best", "top", "segment"]):
        if top_name:
            return (
                f"Your relationship with '{top_name}' is one of your most valuable assets — protect it proactively rather than reactively. "
                f"Reach out this week with a personalised thank-you and offer them loyalty pricing, early access to new products, or a dedicated account review call. "
                f"Customers who feel recognised and valued are significantly less likely to churn, and retaining one high-value customer costs far less than acquiring a replacement."
            )
        return (
            "Identify your top 20% of customers by revenue — this group typically generates 80% of your income and deserves a differentiated experience. "
            "Create a simple VIP tier: offer them first access to new products, a small loyalty discount, or a quarterly business review call. "
            "Even a light-touch retention programme for this segment can dramatically reduce churn risk and increase their lifetime value over the next 12 months."
        )

    if any(w in q for w in ["product", "sell", "selling"]):
        if top_name:
            return (
                f"'{top_name}' is your strongest product — double down on it before competitors do. "
                f"Review your current inventory levels and ensure you have at least 4–6 weeks of stock on hand, then increase its share of your marketing budget by 20–30% to drive further volume. "
                f"Also consider whether you can introduce a premium version, a bundle, or a subscription option around this product to increase revenue per customer."
            )
        return (
            "Rank your products by total revenue and identify the top three — these proven sellers should receive the majority of your inventory investment and ad spend. "
            "For each of the top three, check whether you are consistently in stock, competitively priced, and actively promoted across your key channels. "
            "Avoid spreading budget evenly across all SKUs; concentrating resources on proven performers delivers far better returns than trying to lift slow-moving products."
        )

    return (
        "Review this result against your targets and identify the single biggest gap between where you are and where you want to be. "
        "Break that gap into one concrete action you can start this week — even a small, focused step moves the metric in the right direction faster than broad, unfocused effort. "
        "Set a specific review date in 7–14 days to measure whether your action had the intended effect and adjust from there."
    )


def generate_insight(user_query: str, answer_summary: str, result: dict = None, sql: str = "") -> dict:
    """
    Call the LLM to produce structured explainability: reason, two evidence items,
    and a concrete action. Falls back to rule-based suggestions if the LLM is unavailable
    so that an action is always returned.
    """
    table_source = _extract_table_name(sql) if sql else "data"

    data_context = ""
    if result and result.get("rows") and result.get("columns"):
        rows = result["rows"]
        cols = result["columns"]
        sample = []
        for row in rows[:3]:
            sample.append(str(dict(zip(cols, row))))
        data_context = f"\nActual query result (from {table_source}):\n" + "\n".join(sample)

    prompt = f"""You are a business intelligence assistant for a small business owner.

The owner asked: "{user_query}"
The data answer is: {answer_summary}{data_context}

Reply using EXACTLY these six labelled lines. Each label must appear once. Do not add any other lines.

REASON: [one sentence explaining WHY this result occurred based on the data]
EVIDENCE1_SOURCE: [table or data area, e.g. marketing_performance]
EVIDENCE1_DETAIL: [one specific number or comparison from the data]
EVIDENCE2_SOURCE: [second data area]
EVIDENCE2_DETAIL: [second specific data point]
ACTION: [Write 2-3 full sentences all on this single line. Sentence 1: the specific action to take right now using the actual names/numbers from the data. Sentence 2: why it matters — quantify the impact using figures from the result. Sentence 3: one concrete follow-up step to measure success within 2 weeks.]"""

    raw = _call_groq(prompt)
    reason = action = ""
    ev1_source = ev1_detail = ev2_source = ev2_detail = ""

    if raw:
        action_lines = []
        in_action = False
        for line in raw.splitlines():
            if line.startswith("REASON:"):
                reason = line[7:].strip()
                in_action = False
            elif line.startswith("EVIDENCE1_SOURCE:"):
                ev1_source = line[17:].strip()
                in_action = False
            elif line.startswith("EVIDENCE1_DETAIL:"):
                ev1_detail = line[17:].strip()
                in_action = False
            elif line.startswith("EVIDENCE2_SOURCE:"):
                ev2_source = line[17:].strip()
                in_action = False
            elif line.startswith("EVIDENCE2_DETAIL:"):
                ev2_detail = line[17:].strip()
                in_action = False
            elif line.startswith("ACTION:"):
                action_lines = [line[7:].strip()]
                in_action = True
            elif in_action and line.strip():
                action_lines.append(line.strip())
        action = " ".join(action_lines).strip()

    evidence = []
    if ev1_source and ev1_detail:
        evidence.append({"source": ev1_source, "detail": ev1_detail})
    if ev2_source and ev2_detail:
        evidence.append({"source": ev2_source, "detail": ev2_detail})

    # Use rule-based if LLM returned nothing or a single short sentence (< 200 chars)
    if not action or len(action) < 200:
        action = _rule_based_action(user_query, result)

    return {"reason": reason, "evidence": evidence, "action": action}


def explain_result(user_query: str, result: dict) -> str:
    if not result or result.get("error"):
        return f"Sorry, I couldn't retrieve that data: {result.get('error', 'unknown error')}."

    rows = result.get("rows", [])
    cols = result.get("columns", [])

    if not rows:
        return "No data found for your query in the current period."

    q = user_query.lower()

    # Single-value result (e.g. SUM, COUNT, AVG)
    if len(rows) == 1 and len(rows[0]) == 1:
        val = rows[0][0]
        col = cols[0] if cols else "value"
        if isinstance(val, float):
            return f"The {col.replace('_', ' ')} is **${val:,.2f}**."
        return f"The {col.replace('_', ' ')} is **{val}**."

    # Multi-row result — build a readable summary
    n = len(rows)
    col_labels = [c.replace("_", " ").title() for c in cols]

    # Try to give a context-aware intro
    # Find the first text column (name) and first numeric column (value)
    def _first_text(row, cols_list):
        for i, v in enumerate(row):
            if isinstance(v, str):
                return v, cols_list[i] if i < len(cols_list) else ""
        return str(row[0]), cols_list[0] if cols_list else ""

    def _first_num(row):
        for v in row:
            if isinstance(v, (int, float)):
                return v
        return None

    top = rows[0]
    name_val, _ = _first_text(top, cols)
    num_val = _first_num(top)

    if any(w in q for w in ["best customer", "top customer", "who are"]):
        intro = f"Your best customer is **{name_val}**"
        intro += f" with **${num_val:,.0f}** in revenue." if num_val is not None else "."
        intro += f" Here are the top {min(n, 5)} customers:"

    elif any(w in q for w in ["product", "sell", "best selling"]):
        intro = f"Your best-selling product is **{name_val}**"
        intro += f" generating **${num_val:,.0f}** in revenue." if num_val is not None else "."
        intro += f" Showing top {min(n, 5)} products:"

    elif any(w in q for w in ["campaign", "marketing", "roi", "wasting"]):
        intro = f"Top campaign: **{name_val}**"
        intro += f" generating **${num_val:,.0f}**." if num_val is not None else "."
        intro += f" Showing all {n} campaigns:"

    elif any(w in q for w in ["channel"]):
        intro = f"The top channel is **{name_val}**"
        intro += f" generating **${num_val:,.0f}** in revenue." if num_val is not None else "."
        intro += f" Showing all {n} channels:" if n > 1 else ""

    elif any(w in q for w in ["revenue", "profit", "expense", "cost"]):
        intro = f"Here are **{n}** result(s):"

    else:
        intro = f"Found **{n}** result(s) for your query:"

    # Build a bullet-point summary of top rows (max 5)
    bullets = []
    for row in rows[:5]:
        parts = [f"{col_labels[i]}: {('$'+f'{v:,.0f}') if isinstance(v, float) else v}"
                 for i, v in enumerate(row)]
        bullets.append("• " + " | ".join(parts))

    return intro + "\n\n" + "\n".join(bullets)


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", _OPENAI_API_KEY)
    if not api_key:
        return ""
    try:
        response = requests.post(
            _OPENAI_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": _OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=30
        )
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE FALLBACK (used when Ollama is unavailable)
# ─────────────────────────────────────────────────────────────────────────────

def _template_explanation(anomaly: dict) -> str:
    atype = anomaly.get("type", "")
    value = anomaly.get("value")
    expected = anomaly.get("expected")
    deviation_pct = anomaly.get("deviation_pct")
    date = anomaly.get("date", "")
    unit = anomaly.get("unit", "")
    severity = anomaly.get("severity", "")
    domain = anomaly.get("domain", "")

    abs_dev = abs(deviation_pct) if deviation_pct is not None else 0
    direction = "higher than" if (deviation_pct or 0) > 0 else "lower than"

    date_part = f"On {date}, " if date else ""
    value_part = (
        f" ({unit}{value:,.0f} vs the usual {unit}{expected:,.0f})"
        if value is not None and expected is not None else ""
    )

    if "revenue" in atype:
        core = f"your revenue was {abs_dev:.1f}% {direction} normal{value_part}"
    elif "expense" in atype:
        category = atype.replace("_expense", "").replace("_", " ").title()
        core = f"your {category} expenses were {abs_dev:.1f}% {direction} normal{value_part}"
    elif "marketing" in atype or "pattern" in atype:
        spend_part = f" with a spend of {unit}{value:,.0f}" if value is not None else ""
        core = f"an unusual marketing activity pattern was detected{spend_part}"
    elif "cash" in atype or "cashflow" in atype:
        core = f"your cash balance changed unexpectedly by {abs_dev:.1f}%{value_part}"
    else:
        core = f"an unusual pattern was detected in your {domain} data"

    urgency = (
        " Immediate attention is recommended." if severity == "high"
        else " This warrants monitoring." if severity == "medium"
        else ""
    )

    return f"{date_part}{core}.{urgency}"


# ─────────────────────────────────────────────────────────────────────────────
# ANOMALY EXPLAINER (uses Ollama, falls back to template)
# ─────────────────────────────────────────────────────────────────────────────

def explain_anomaly(anomaly: dict) -> str:
    """
    Generate a plain-language explanation for a single anomaly dict.
    Uses Ollama (llama3.1) to produce a business-friendly 2-3 sentence
    explanation. Falls back to a rule-based template if Ollama is down.
    """
    domain = anomaly.get("domain", "")
    atype = anomaly.get("type", "").replace("_", " ")
    severity = anomaly.get("severity", "")
    value = anomaly.get("value")
    expected = anomaly.get("expected")
    deviation_pct = anomaly.get("deviation_pct")
    z_score = anomaly.get("z_score")
    date = anomaly.get("date", "unknown date")
    unit = anomaly.get("unit", "")
    method = anomaly.get("method", "statistical analysis")
    recommendation = anomaly.get("recommendation", "")

    value_str = f"{unit}{value:,.0f}" if value is not None else "N/A"
    expected_str = f"{unit}{expected:,.0f}" if expected is not None else "N/A"
    deviation_str = f"{deviation_pct:.1f}%" if deviation_pct is not None else "N/A"
    z_str = f"{z_score:.2f}" if z_score is not None else "N/A"

    prompt = f"""You are a business intelligence assistant explaining data anomalies to a non-technical small business owner.

An anomaly was detected with the following details:
- Business area: {domain}
- Anomaly type: {atype}
- Severity: {severity}
- Date: {date}
- Actual value: {value_str}
- Expected (normal) value: {expected_str}
- Deviation from normal: {deviation_str}
- Statistical score: {z_str}
- Detection method: {method}
- Suggested action: {recommendation}

Write exactly 2-3 sentences explaining what this means for the business owner.
Rules:
- Use simple, everyday English. No jargon (do not say z-score, Isolation Forest, or statistical).
- Clearly state what happened, why it matters, and what they should do.
- Be specific with numbers if available.
"""

    explanation = _call_groq(prompt)
    if explanation:
        return explanation

    return _template_explanation(anomaly)


# ─────────────────────────────────────────────────────────────────────────────
# SHAP HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_FEATURE_LABELS = {
    "spend": "advertising spend",
    "conversions": "number of conversions",
    "revenue_attributed": "revenue from campaigns",
    "impressions": "ad impressions",
    "clicks": "ad clicks",
    "leads": "leads generated",
    "roi": "return on investment",
    "roas": "return on ad spend",
}


def _shap_to_plain_text(
    top_features: list,
    row: pd.Series,
    col_means: dict,
    unit: str = ""
) -> str:
    """Convert SHAP top-3 features into a single plain-English sentence."""
    if not top_features:
        return "Unusual activity detected with no single dominant driver."

    parts = []
    for feature, _ in top_features:
        label = _FEATURE_LABELS.get(feature, feature.replace("_", " "))
        raw_val = row.get(feature)
        mean_val = col_means.get(feature)
        if raw_val is not None and mean_val is not None:
            direction = "unusually high" if raw_val > mean_val else "unusually low"
            val_str = f"{unit}{raw_val:,.0f}"
        else:
            direction = "abnormal"
            val_str = ""
        parts.append(f"{label} was {direction}" + (f" ({val_str})" if val_str else ""))

    return "This anomaly was mainly driven by: " + "; ".join(parts) + "."


# ─────────────────────────────────────────────────────────────────────────────
# SHAP EXPLAINABILITY FOR ISOLATION FOREST
# ─────────────────────────────────────────────────────────────────────────────

def explain_marketing_anomalies_with_shap(
    features_df: pd.DataFrame,
    feature_names: list = None
) -> list:
    """
    Fit an Isolation Forest on features_df, compute SHAP values using
    TreeExplainer, and return a per-row explanation for each detected anomaly.

    Parameters
    ----------
    features_df : pd.DataFrame
        Feature data for marketing records. Expected columns:
        spend, conversions, revenue_attributed (plus others if present).
    feature_names : list, optional
        Subset of columns to use. Defaults to all numeric columns.

    Returns
    -------
    list of dicts — one entry per anomaly row:
        {
            "row_index"   : int,
            "shap_values" : {feature: float},
            "top_features": [(feature, shap_value), ...],   # top 3 by |shap|
            "explanation" : str,                            # plain English
        }
    """
    if not _SHAP_AVAILABLE:
        return []

    if feature_names is None:
        feature_names = [
            c for c in features_df.columns
            if features_df[c].dtype in [np.float64, np.int64, float, int]
        ]

    subset = features_df[feature_names].dropna()
    X = subset.values

    if len(X) < 10:
        return []

    clf = IsolationForest(
        contamination=_IF_CONTAMINATION,
        random_state=42,
        n_estimators=100
    )
    clf.fit(X)
    preds = clf.predict(X)

    col_means = subset.mean().to_dict()

    shap_explainer = shap.TreeExplainer(clf)
    # check_additivity=False required for IsolationForest
    shap_values = shap_explainer.shap_values(X, check_additivity=False)

    results = []
    for i, pred in enumerate(preds):
        if pred != -1:
            continue

        sv = shap_values[i]
        feature_shap = dict(zip(feature_names, sv.tolist()))

        top_features = sorted(
            feature_shap.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:3]

        row = subset.iloc[i]
        plain = _shap_to_plain_text(top_features, row, col_means)

        results.append({
            "row_index": int(subset.index[i]),
            "shap_values": {k: round(v, 4) for k, v in feature_shap.items()},
            "top_features": [(f, round(v, 4)) for f, v in top_features],
            "explanation": plain,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# BATCH ENRICHMENT — attaches plain-language explanation to every anomaly
# ─────────────────────────────────────────────────────────────────────────────

def enrich_anomalies_with_explanations(anomalies: list) -> list:
    """
    Add an 'explanation' field to every anomaly dict returned by
    run_all_detectors(). Used by the dashboard alert panel.

    Returns a new list (originals are not mutated).
    """
    enriched = []
    for anomaly in anomalies:
        copy = dict(anomaly)
        copy["explanation"] = explain_anomaly(anomaly)
        enriched.append(copy)
    return enriched
