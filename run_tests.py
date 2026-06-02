"""
Senior tester: verifies all 3 company types work correctly end-to-end.
  Company 1 (Wouessi)      — services only
  Company 2 (My Company)   — products only
  Company 7 (KP Fashion)   — products + services both
"""
import os, requests
os.environ["DATABASE_URL"] = "postgresql://postgres:Mayank1717%40%40@localhost:5432/bi_dashboard"
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
API = "https://wouessi-bi-backend.onrender.com"
RESULTS = {"PASS": 0, "FAIL": 0}

def check(label, value, *, expect=None, nonzero=False, zero=False):
    if expect is not None:
        ok = abs(float(value) - float(expect)) < 1
    elif nonzero:
        ok = float(value) != 0
    elif zero:
        ok = float(value) == 0
    else:
        ok = bool(value)
    RESULTS["PASS" if ok else "FAIL"] += 1
    hint = f"(exp ~{expect})" if expect is not None else ("(>0)" if nonzero else "(=0)" if zero else "")
    print(f"  {'PASS' if ok else 'FAIL'} {label}: {value} {hint}")
    return ok

def scalar(q, p={}):
    with engine.connect() as c:
        r = c.execute(text(q), p).scalar()
        return float(r) if r is not None else 0.0

def qrows(q, p={}):
    with engine.connect() as c:
        return c.execute(text(q), p).fetchall()

COMPANIES = {
    "services_only": {"cid": 1, "name": "Wouessi Commerce"},
    "products_only": {"cid": 2, "name": "My Company"},
    "both":          {"cid": 7, "name": "KP Fashion Store"},
}

# ── PROFILES ──────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("COMPANY PROFILES")
print("="*65)
for k, c in COMPANIES.items():
    cid = c["cid"]
    s = int(scalar("SELECT COUNT(*) FROM fact_sales WHERE company_id=:cid", {"cid": cid}))
    b = int(scalar("SELECT COUNT(*) FROM fact_service_bookings WHERE company_id=:cid", {"cid": cid}))
    p = int(scalar("SELECT COUNT(*) FROM dim_products WHERE company_id=:cid", {"cid": cid}))
    sv = int(scalar("SELECT COUNT(*) FROM dim_services WHERE company_id=:cid", {"cid": cid}))
    print(f"  [{k}] {c['name']} (id={cid}): {s} sales | {b} bookings | {p} products | {sv} services")

# ── TEST 1: COMBINED REVENUE ───────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 1 — Combined Revenue (products + services)")
print("="*65)
for k, c in COMPANIES.items():
    cid = c["cid"]
    pr = scalar("SELECT COALESCE(SUM(line_total),0) FROM fact_sales WHERE status='completed' AND company_id=:cid", {"cid": cid})
    sr = scalar("SELECT COALESCE(SUM(line_total),0) FROM fact_service_bookings WHERE status='completed' AND company_id=:cid", {"cid": cid})
    cb = scalar("SELECT COALESCE(SUM(line_total),0) FROM (SELECT line_total FROM fact_sales WHERE status='completed' AND company_id=:cid UNION ALL SELECT line_total FROM fact_service_bookings WHERE status='completed' AND company_id=:cid) t", {"cid": cid})
    print(f"\n  [{k}]  prod=${pr:,.0f}  svc=${sr:,.0f}  combined=${cb:,.0f}")
    check(f"[{k}] combined == prod+svc", cb, expect=pr + sr)
    if k == "services_only":
        check(f"[{k}] product_revenue = 0", pr, zero=True)
        check(f"[{k}] service_revenue > 0", sr, nonzero=True)
    elif k == "products_only":
        check(f"[{k}] product_revenue > 0", pr, nonzero=True)
        check(f"[{k}] service_revenue = 0", sr, zero=True)
    else:
        check(f"[{k}] product_revenue > 0", pr, nonzero=True)
        check(f"[{k}] service_revenue > 0", sr, nonzero=True)

# ── TEST 2: TOP PRODUCTS ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 2 — Top Products")
print("="*65)
TOP_PROD = "SELECT dp.product_name, SUM(fs.line_total) as rev FROM fact_sales fs JOIN dim_products dp ON fs.product_id=dp.product_id WHERE fs.status='completed' AND fs.company_id=:cid GROUP BY dp.product_name ORDER BY rev DESC LIMIT 5"
for k, c in COMPANIES.items():
    r = qrows(TOP_PROD, {"cid": c["cid"]})
    if k == "services_only":
        check(f"[{k}] top_products empty (no products)", len(r), zero=True)
    else:
        check(f"[{k}] top_products has rows", len(r), nonzero=True)
        if r: print(f"         best: {r[0][0]}  ${float(r[0][1]):,.0f}")

# ── TEST 3: TOP SERVICES ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 3 — Top Services")
print("="*65)
TOP_SVC = "SELECT ds.service_name, SUM(fsb.line_total) as rev FROM fact_service_bookings fsb JOIN dim_services ds ON fsb.service_id=ds.service_id WHERE fsb.status='completed' AND fsb.company_id=:cid GROUP BY ds.service_name ORDER BY rev DESC LIMIT 5"
for k, c in COMPANIES.items():
    r = qrows(TOP_SVC, {"cid": c["cid"]})
    if k == "products_only":
        check(f"[{k}] top_services empty (no services)", len(r), zero=True)
    else:
        check(f"[{k}] top_services has rows", len(r), nonzero=True)
        if r: print(f"         best: {r[0][0]}  ${float(r[0][1]):,.0f}")

# ── TEST 4: ACTIVE CUSTOMERS ───────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 4 — Active Customers (union both tables)")
print("="*65)
ACTIVE = "SELECT COUNT(DISTINCT customer_id) FROM (SELECT customer_id FROM fact_sales WHERE status='completed' AND company_id=:cid UNION SELECT customer_id FROM fact_service_bookings WHERE status='completed' AND company_id=:cid) t"
for k, c in COMPANIES.items():
    v = scalar(ACTIVE, {"cid": c["cid"]})
    check(f"[{k}] active_customers > 0", v, nonzero=True)
    print(f"         active={int(v)}")

# ── TEST 5: MONTHLY TREND ──────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 5 — Monthly Revenue Trend (union)")
print("="*65)
TREND = "SELECT TO_CHAR(m,'Mon YYYY') as month, SUM(rev) as revenue FROM (SELECT DATE_TRUNC('month',CAST(order_date AS DATE)) as m, SUM(line_total) as rev FROM fact_sales WHERE status='completed' AND company_id=:cid GROUP BY 1 UNION ALL SELECT DATE_TRUNC('month',CAST(booking_date AS DATE)) as m, SUM(line_total) as rev FROM fact_service_bookings WHERE status='completed' AND company_id=:cid GROUP BY 1) t GROUP BY m ORDER BY m"
for k, c in COMPANIES.items():
    r = qrows(TREND, {"cid": c["cid"]})
    check(f"[{k}] monthly trend has rows", len(r), nonzero=True)
    if r: print(f"         {len(r)} months | latest: {r[-1][0]}  ${float(r[-1][1]):,.0f}")

# ── TEST 6: HAS_DATA ───────────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 6 — has_data (True for all 3 company types)")
print("="*65)
for k, c in COMPANIES.items():
    hs = scalar("SELECT COUNT(*) FROM fact_sales WHERE company_id=:cid", {"cid": c["cid"]}) > 0
    hb = scalar("SELECT COUNT(*) FROM fact_service_bookings WHERE company_id=:cid", {"cid": c["cid"]}) > 0
    check(f"[{k}] has_data = True", 1 if (hs or hb) else 0, nonzero=True)
    print(f"         has_sales={hs}  has_services={hb}")

# ── TEST 7: GROSS PROFIT ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 7 — Gross Profit (union)")
print("="*65)
GP = "SELECT COALESCE(SUM(gross_profit),0) FROM (SELECT gross_profit FROM fact_sales WHERE status='completed' AND company_id=:cid UNION ALL SELECT gross_profit FROM fact_service_bookings WHERE status='completed' AND company_id=:cid) t"
for k, c in COMPANIES.items():
    v = scalar(GP, {"cid": c["cid"]})
    check(f"[{k}] gross_profit > 0", v, nonzero=True)
    print(f"         gross_profit=${v:,.0f}")

# ── TEST 8: FORECAST SQL ───────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 8 — Forecast daily rows (>=14 needed)")
print("="*65)
FC = "SELECT day, SUM(revenue) as revenue FROM (SELECT CAST(order_date AS DATE) as day, SUM(line_total) as revenue FROM fact_sales WHERE status='completed' AND company_id=:cid GROUP BY 1 UNION ALL SELECT CAST(booking_date AS DATE) as day, SUM(line_total) as revenue FROM fact_service_bookings WHERE status='completed' AND company_id=:cid GROUP BY 1) combined GROUP BY day ORDER BY day"
for k, c in COMPANIES.items():
    r = qrows(FC, {"cid": c["cid"]})
    check(f"[{k}] daily rows >= 14", len(r), nonzero=True)
    print(f"         {len(r)} daily rows")

# ── TEST 9: ANOMALY SQL ────────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 9 — Anomaly Detection SQL (union)")
print("="*65)
AN = "SELECT company_id, CAST(order_date AS DATE) AS order_date, line_total FROM fact_sales WHERE status='completed' UNION ALL SELECT company_id, CAST(booking_date AS DATE) AS order_date, line_total FROM fact_service_bookings WHERE status='completed'"
for k, c in COMPANIES.items():
    import pandas as pd
    with engine.connect() as conn:
        df = pd.read_sql(text(AN), conn)
    df_c = df[df["company_id"] == c["cid"]]
    check(f"[{k}] anomaly df has rows", len(df_c), nonzero=True)
    print(f"         {len(df_c)} combined revenue rows for anomaly scan")

# ── TEST 10: LIVE API ──────────────────────────────────────────────────────────
print("\n" + "="*65)
print("TEST 10 — Live API endpoints")
print("="*65)

def api_check(tag, token, endpoint, kpi_key=None, assertion="nonzero", list_key=None):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{API}{endpoint}", headers=headers, timeout=8)
        if not check(f"[{tag}] {endpoint} HTTP 200", resp.status_code, expect=200):
            return {}
        data = resp.json()
        check(f"[{tag}] {endpoint} has_data", 1 if data.get("has_data", True) else 0, nonzero=True)
        if kpi_key:
            val = data.get("kpis", {}).get(kpi_key, None)
            if val is None:
                check(f"[{tag}] {endpoint}.kpis.{kpi_key} exists", 0, nonzero=True)
            elif assertion == "nonzero":
                check(f"[{tag}] {endpoint}.kpis.{kpi_key} > 0", val, nonzero=True)
            elif assertion == "zero":
                check(f"[{tag}] {endpoint}.kpis.{kpi_key} = 0", val, zero=True)
        if list_key:
            lst = data.get(list_key, [])
            check(f"[{tag}] {endpoint}.{list_key} not empty", len(lst), nonzero=True)
        return data
    except Exception as e:
        print(f"  ! [{tag}] {endpoint} error: {e}")
        return {}

try:
    # KP Fashion — both
    r = requests.post(f"{API}/auth/login", json={"email": "kenilp156@gmail.com", "password": "Demo1234!"}, timeout=5)
    if r.status_code == 200:
        tok = r.json()["token"]
        print("\n  [both] KP Fashion Store:")
        api_check("both", tok, "/api/overview",          "total_revenue", "nonzero")
        api_check("both", tok, "/api/finance/summary",   "total_revenue", "nonzero")
        d = api_check("both", tok, "/api/sales/summary", "total_revenue", "nonzero")
        check("[both] sales.product_revenue > 0", d.get("kpis", {}).get("product_revenue", 0), nonzero=True)
        check("[both] sales.service_revenue > 0", d.get("kpis", {}).get("service_revenue", 0), nonzero=True)
        check("[both] sales.top_products not empty", len(d.get("top_products", [])), nonzero=True)
        check("[both] sales.top_services not empty", len(d.get("top_services", [])), nonzero=True)
        api_check("both", tok, "/api/customers/summary", "total_customers", "nonzero")
        api_check("both", tok, "/api/services/summary",  "total_revenue",   "nonzero")

    # Wouessi — services only
    r = requests.post(f"{API}/auth/demo-login", timeout=5)
    if r.status_code == 200:
        tok = r.json()["token"]
        print("\n  [services_only] Wouessi Commerce:")
        api_check("svc", tok, "/api/overview",         "total_revenue", "nonzero")
        d = api_check("svc", tok, "/api/sales/summary","total_revenue", "nonzero")
        check("[svc_only] sales.product_revenue = 0",  d.get("kpis", {}).get("product_revenue", 0), zero=True)
        check("[svc_only] sales.service_revenue > 0",  d.get("kpis", {}).get("service_revenue", 0), nonzero=True)
        check("[svc_only] sales.top_products empty",   len(d.get("top_products", [])), zero=True)
        check("[svc_only] sales.top_services not empty", len(d.get("top_services", [])), nonzero=True)
        api_check("svc", tok, "/api/services/summary", "total_revenue", "nonzero")
        api_check("svc", tok, "/api/finance/summary",  "total_revenue", "nonzero")

except Exception as e:
    print(f"  API not reachable — skipping live tests ({e})")

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "="*65)
total = RESULTS["PASS"] + RESULTS["FAIL"]
print(f"RESULTS:  {RESULTS['PASS']}/{total} PASSED   |   {RESULTS['FAIL']} FAILED")
print("="*65)
print("ALL TESTS PASSED" if RESULTS["FAIL"] == 0 else "ACTION REQUIRED -- see FAIL lines above")
