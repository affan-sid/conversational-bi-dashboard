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

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL   = "llama-3.1-8b-instant"

_IF_CONTAMINATION = 0.05


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
# GROQ HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    try:
        response = requests.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {_GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": _GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=20
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
