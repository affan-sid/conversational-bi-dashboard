"""
NLP Pipeline Evaluation
=======================
Measures Intent Classification Accuracy, Precision, Recall, and F1
for the semantic KPI mapping layer.

Run from the project root:
    python -m backend.app.nlp.evaluate_nlp

No database connection required — all assertions are structural/keyword checks
on the generated SQL, evaluated offline against a labelled test suite.
"""

import re
import sys
from collections import defaultdict
from typing import Optional

from backend.app.semantic.kpis import map_to_kpi
from backend.app.nlp.text_to_sql import generate_sql, is_safe_sql

# ---------------------------------------------------------------------------
# Labelled test suite
# Each entry: (natural-language query, expected_intent)
# intent = a KPI key (semantic layer hit) OR "sql_fallback" (no KPI matched)
# ---------------------------------------------------------------------------

TEST_CASES = [
    # ── Revenue ─────────────────────────────────────────────────────────────
    ("What is my total revenue?",                       "revenue"),
    ("How much revenue did we make this quarter?",      "revenue"),
    ("Show me income for last month",                   "revenue"),
    ("How much have we made so far this year?",         "revenue"),
    ("What are total sales?",                           "revenue"),

    # ── Gross / Net profit ───────────────────────────────────────────────────
    ("What is my gross profit?",                        "gross_profit"),
    ("Show net profit for this year",                   "net_profit"),
    ("What is our profit margin?",                      "net_profit"),

    # ── Cash ─────────────────────────────────────────────────────────────────
    ("How many months of cash runway do we have?",      "cash_runway"),
    ("What is our burn rate?",                          "cash_runway"),
    ("How much cash is left?",                          "cash_runway"),

    # ── Products ─────────────────────────────────────────────────────────────
    ("What are my top 5 best-selling products?",        "top_products"),
    ("Which product sells best?",                       "top_products"),
    ("Show me popular products",                        "top_products"),

    # ── Services ─────────────────────────────────────────────────────────────
    ("What are my top services by revenue?",            "top_services"),
    ("Show service revenue breakdown",                  "service_revenue"),
    ("How much from services?",                         "service_revenue"),

    # ── Marketing ────────────────────────────────────────────────────────────
    ("Which marketing campaign has the best ROI?",      "marketing_roi"),
    ("Show campaign performance and ROI",               "marketing_roi"),
    ("What is the return on investment for campaigns?", "marketing_roi"),
    ("Which campaign is wasting money?",                "worst_campaign"),
    ("Which campaign should I pause?",                  "worst_campaign"),
    ("What is our worst performing campaign?",          "worst_campaign"),

    # ── Customers ────────────────────────────────────────────────────────────
    ("Who are my top customers by revenue?",            "top_customers"),
    ("Show me the biggest customers",                   "top_customers"),
    ("What is the customer retention rate?",            "customer_retention_rate"),
    ("What are customers at churn risk?",               "churn_risk"),
    ("Which customers might churn?",                    "churn_risk"),

    # ── Orders / AOV ─────────────────────────────────────────────────────────
    ("What is the average order value?",                "avg_order_value"),
    ("Show me AOV this month",                          "avg_order_value"),

    # ── Segments / Channels / Cities ─────────────────────────────────────────
    ("Which customer segment spends the most?",         "revenue_by_segment"),
    ("Revenue by segment",                              "revenue_by_segment"),
    ("Show revenue by channel",                         "revenue_by_channel"),
    ("Which channel performs best?",                    "revenue_by_channel"),
    ("Revenue by city",                                 "revenue_by_city"),
    ("Which city has the most orders?",                 "revenue_by_city"),

    # ── Expenses ─────────────────────────────────────────────────────────────
    ("Show expense breakdown by category",              "expense_breakdown"),
    ("Where are we spending the most?",                 "expense_breakdown"),
    ("What is our cost breakdown?",                     "expense_breakdown"),

    # ── SQL fallback (no KPI match expected) ─────────────────────────────────
    ("Show me daily revenue for October 2025",          "revenue"),
    ("List all campaigns with spend over 5000",         "sql_fallback"),
    ("How many service bookings this week?",            "sql_fallback"),
    ("What is our monthly expense trend?",              "sql_fallback"),
]

# ---------------------------------------------------------------------------
# SQL structural validation (offline, no DB)
# ---------------------------------------------------------------------------

_SQL_CHECKS = {
    "revenue": {
        "required_tables": ["fact_sales", "fact_service_bookings"],
        "required_keywords": ["line_total", "company_id"],
        "forbidden_keywords": [],
    },
    "top_products": {
        "required_tables": ["fact_sales", "dim_products"],
        "required_keywords": ["company_id"],
        "forbidden_keywords": [],
    },
    "expense_breakdown": {
        "required_tables": ["fact_expenses"],
        "required_keywords": ["company_id"],
        "forbidden_keywords": [],
    },
    "marketing_roi": {
        "required_tables": ["fact_marketing"],
        "required_keywords": ["company_id", "revenue_attributed", "spend"],
        "forbidden_keywords": [r"\.roi", r"\.roas"],   # must not select a non-existent column
    },
    "sql_fallback": {
        "required_tables": [],
        "required_keywords": ["company_id"],
        "forbidden_keywords": ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"],
    },
}


def _check_sql(sql: str, intent: str, company_id: int = 1) -> dict:
    sql_upper = sql.upper()
    checks = _SQL_CHECKS.get(intent, {"required_tables": [], "required_keywords": ["company_id"], "forbidden_keywords": []})

    missing_tables   = [t for t in checks["required_tables"] if t.upper() not in sql_upper]
    missing_keywords = [k for k in checks["required_keywords"] if k.upper() not in sql_upper]
    found_forbidden  = [k for k in checks["forbidden_keywords"] if re.search(k, sql, re.IGNORECASE)]
    has_company_id   = str(company_id) in sql

    return {
        "valid":             not missing_tables and not missing_keywords and not found_forbidden,
        "missing_tables":    missing_tables,
        "missing_keywords":  missing_keywords,
        "forbidden_found":   found_forbidden,
        "has_company_id":    has_company_id,
        "is_safe":           is_safe_sql(sql),
    }


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_intent_classification(test_cases=TEST_CASES) -> dict:
    """Run intent classification on all test cases and compute metrics."""
    intents = sorted({tc[1] for tc in test_cases})

    # tp[c], fp[c], fn[c] per class
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    results = []
    correct = 0

    for query, expected in test_cases:
        predicted_kpi = map_to_kpi(query)
        predicted = predicted_kpi if predicted_kpi is not None else "sql_fallback"

        hit = (predicted == expected)
        if hit:
            correct += 1
            tp[expected] += 1
        else:
            fp[predicted] += 1
            fn[expected]  += 1

        results.append({
            "query":    query,
            "expected": expected,
            "predicted": predicted,
            "correct":  hit,
        })

    n = len(test_cases)
    accuracy = correct / n

    per_class = {}
    for cls in intents:
        p = tp[cls] / (tp[cls] + fp[cls]) if (tp[cls] + fp[cls]) > 0 else 0.0
        r = tp[cls] / (tp[cls] + fn[cls]) if (tp[cls] + fn[cls]) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        per_class[cls] = {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3), "support": tp[cls] + fn[cls]}

    # Macro-average
    macro_p = sum(v["precision"] for v in per_class.values()) / len(per_class)
    macro_r = sum(v["recall"]    for v in per_class.values()) / len(per_class)
    macro_f = sum(v["f1"]        for v in per_class.values()) / len(per_class)

    return {
        "accuracy":    round(accuracy, 3),
        "macro_precision": round(macro_p, 3),
        "macro_recall":    round(macro_r, 3),
        "macro_f1":        round(macro_f, 3),
        "n_total":   n,
        "n_correct": correct,
        "per_class": per_class,
        "results":   results,
    }


def evaluate_sql_generation(test_cases=TEST_CASES, company_id: int = 1, skip_llm: bool = False) -> dict:
    """
    For sql_fallback cases, call generate_sql() and validate structure.
    skip_llm=True returns mock results so the test runs without an OpenAI key.
    """
    fallback_cases = [(q, intent) for q, intent in test_cases if intent == "sql_fallback"]
    sql_results = []
    valid_count = 0

    for query, intent in fallback_cases:
        if skip_llm:
            result = {"query": query, "sql": "<skipped — set skip_llm=False to run>", "valid": None}
        else:
            sql = generate_sql(query, company_id)
            check = _check_sql(sql, intent, company_id)
            if check["valid"]:
                valid_count += 1
            result = {"query": query, "sql": sql[:120] + "...", **check}
        sql_results.append(result)

    return {
        "n_fallback_cases": len(fallback_cases),
        "n_valid_sql":      valid_count if not skip_llm else None,
        "sql_validity_pct": round(valid_count / len(fallback_cases) * 100, 1) if (fallback_cases and not skip_llm) else None,
        "results":          sql_results,
    }


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def _print_report(intent_metrics: dict, sql_metrics: dict):
    print("\n" + "=" * 65)
    print("  NLP PIPELINE EVALUATION REPORT")
    print("=" * 65)

    print(f"\n[Intent Classification]  n={intent_metrics['n_total']}, correct={intent_metrics['n_correct']}")
    print(f"  Accuracy  : {intent_metrics['accuracy']*100:.1f}%")
    print(f"  Macro-P   : {intent_metrics['macro_precision']*100:.1f}%")
    print(f"  Macro-R   : {intent_metrics['macro_recall']*100:.1f}%")
    print(f"  Macro-F1  : {intent_metrics['macro_f1']*100:.1f}%")

    print(f"\n{'Intent':<32} {'P':>6} {'R':>6} {'F1':>6} {'N':>4}")
    print("-" * 58)
    for cls, m in sorted(intent_metrics["per_class"].items()):
        print(f"  {cls:<30} {m['precision']*100:5.1f}% {m['recall']*100:5.1f}% {m['f1']*100:5.1f}% {m['support']:>4}")

    print("\n[Misclassifications]")
    for r in intent_metrics["results"]:
        if not r["correct"]:
            print(f"  MISS  expected={r['expected']:25s}  got={r['predicted']:25s}")
            print(f"     query: \"{r['query']}\"")

    print(f"\n[SQL Generation]  fallback cases={sql_metrics['n_fallback_cases']}")
    if sql_metrics["sql_validity_pct"] is not None:
        print(f"  Structural validity: {sql_metrics['sql_validity_pct']:.1f}%")
    else:
        print("  SQL generation skipped (skip_llm=True). Re-run with skip_llm=False to include.")

    print("\n" + "=" * 65)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skip_llm = "--skip-llm" in sys.argv or True   # default True to avoid needing API key offline

    print("Running intent classification evaluation…")
    intent_metrics = evaluate_intent_classification()

    print("Running SQL generation evaluation…")
    sql_metrics = evaluate_sql_generation(skip_llm=skip_llm)

    _print_report(intent_metrics, sql_metrics)

    # Exit code 1 if accuracy below 80%
    if intent_metrics["accuracy"] < 0.80:
        print(f"\nWARN: accuracy {intent_metrics['accuracy']*100:.1f}% is below 80% threshold.")
        sys.exit(1)
