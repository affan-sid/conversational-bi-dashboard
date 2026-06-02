"""
One-time seeding logic for the Wouessi Digital Agency demo company and KP Fashion Store.
Called by the /api/admin/seed-demo endpoint so it runs inside Render using the
backend's own database connection (no need to expose or share the DB URL).
"""
import hashlib
import random
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text


_SEED = 42
random.seed(_SEED)

TODAY      = date(2026, 5, 26)
START_DATE = date(2025, 1, 1)


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _s(conn, sql, params=None):
    r = conn.execute(text(sql), params or {}).scalar()
    return r


def _ins(engine, df, table):
    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=500)
    return len(df)


# ─────────────────────────────────────────────────────────────────────────────
def seed_wouessi(engine) -> dict:
    """Seed / re-seed the Wouessi Digital Agency (services-only) demo company.

    Idempotent: wipes all existing data for demo@wouessi.com's company_id first.
    Returns a summary dict.
    """
    random.seed(_SEED)

    DEMO_EMAIL = "demo@wouessi.com"
    DEMO_PW    = "WouessDemo2024!"

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, company_id FROM dim_users WHERE email=:e"),
            {"e": DEMO_EMAIL}
        ).fetchone()

        if row:
            W_USER_ID, CID_W = int(row[0]), int(row[1])
            # Wipe old data
            for t in ["fact_service_bookings", "dim_services", "fact_expenses",
                      "fact_marketing", "fact_cash_flow", "dim_customers", "dim_campaigns",
                      "fact_sales", "dim_products"]:
                conn.execute(text(f"DELETE FROM {t} WHERE company_id=:cid"), {"cid": CID_W})
            conn.commit()
        else:
            CID_W = int(_s(conn, "SELECT COALESCE(MAX(company_id),0)+1 FROM dim_companies"))
            conn.execute(text(
                "INSERT INTO dim_companies(company_id,company_name,industry,country,currency,created_at)"
                " VALUES(:cid,'Wouessi Digital Agency','Digital Services','Canada','CAD',NOW())"
            ), {"cid": CID_W})
            conn.commit()
            W_USER_ID = int(_s(conn, "SELECT COALESCE(MAX(user_id),0)+1 FROM dim_users"))
            conn.execute(text(
                "INSERT INTO dim_users(user_id,company_id,full_name,email,role,password_hash,created_at)"
                " VALUES(:uid,:cid,'Wouessi Demo',:email,'viewer',:ph,NOW())"
            ), {"uid": W_USER_ID, "cid": CID_W, "email": DEMO_EMAIL, "ph": _hash(DEMO_PW)})
            conn.commit()

    # ── Services ──────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        wsvc_base = int(_s(conn, "SELECT COALESCE(MAX(service_id),0) FROM dim_services")) + 1

    wou_services_raw = [
        ("Website Design & Development", "Web Development", 2400, 4500.00, 800.00, 0),
        ("Brand Identity Package",       "Branding",         960, 2800.00, 500.00, 0),
        ("SEO Monthly Retainer",         "SEO",              120,  950.00, 180.00, 1),
        ("Social Media Management",      "Social Media",      80,  750.00, 140.00, 1),
        ("Digital Strategy Consultation","Strategy",         120,  550.00,  90.00, 0),
        ("Google Ads Management",        "Paid Ads",          60,  850.00, 160.00, 1),
        ("E-Commerce Setup",             "Web Development",  1920, 3200.00, 580.00, 0),
    ]
    W_SERVICES = [
        {"service_id": wsvc_base + i, "company_id": CID_W,
         "service_name": sv[0], "category": sv[1], "duration_minutes": sv[2],
         "price": sv[3], "recurring_flag": sv[5], "active_flag": 1,
         "description": f"{sv[0]} — professional {sv[1].lower()} service"}
        for i, sv in enumerate(wou_services_raw)
    ]
    svc_count = _ins(engine, pd.DataFrame(W_SERVICES), "dim_services")

    # ── Clients (25 SME clients) ───────────────────────────────────────────────
    with engine.connect() as conn:
        wcust_base = int(_s(conn, "SELECT COALESCE(MAX(customer_id),0) FROM dim_customers")) + 1

    company_names = [
        "Maple Leaf Retail","BlueSky Fitness","North Star Bakery","Rideau Law Group",
        "Lakeside Dental","Prairie Apparel","GreenPath Landscaping","Summit Consulting",
        "Harbour Coffee","Coastal Realty","TechNova Solutions","BrightMind Education",
        "Urban Threads","Peak Performance Gym","River Valley Cafe","NextGen Logistics",
        "Polar Bear Outfitters","Sunrise Wellness","Canyon Accounting","Lakeview Dental",
        "Fern & Oak Design","Echo Marketing","Spruce Grove Auto","Horizon Veterinary","Cedar Hill Bistro",
    ]
    wseg  = ["SME"] * 18 + ["Corporate"] * 7
    wcity = ["Toronto","Vancouver","Montreal","Calgary","Ottawa","Edmonton","Winnipeg","Halifax"]
    W_CUSTOMERS = [
        {"customer_id": wcust_base + i, "company_id": CID_W,
         "full_name": company_names[i],
         "email": f"contact{i}@{company_names[i].lower().replace(' ','').replace('&','')}.demo",
         "phone": f"+1-416-{2000+i:04d}",
         "segment": wseg[i], "city": random.choice(wcity),
         "country": "Canada",
         "created_at": (START_DATE + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d")}
        for i in range(25)
    ]
    cust_count = _ins(engine, pd.DataFrame(W_CUSTOMERS), "dim_customers")

    # ── Campaigns ─────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        wcamp_base = int(_s(conn, "SELECT COALESCE(MAX(campaign_id),0) FROM dim_campaigns")) + 1

    wou_camps_raw = [
        ("LinkedIn Lead Gen",    "LinkedIn",  8000),
        ("Google Search Ads",    "Google Ads",6000),
        ("Email Nurture Series", "Email",     2500),
        ("Content & SEO Push",   "Organic",   1500),
    ]
    W_CAMPAIGNS = [
        {"campaign_id": wcamp_base + i, "company_id": CID_W,
         "campaign_name": c[0], "platform": c[1],
         "start_date": START_DATE.strftime("%Y-%m-%d"),
         "end_date": "2026-12-31", "budget": c[2]}
        for i, c in enumerate(wou_camps_raw)
    ]
    camp_count = _ins(engine, pd.DataFrame(W_CAMPAIGNS), "dim_campaigns")

    # ── Service Bookings (18 months) ───────────────────────────────────────────
    wou_monthly = {
        "2025-01": 22000, "2025-02": 25000, "2025-03": 29000, "2025-04": 33000,
        "2025-05": 36000, "2025-06": 39000, "2025-07": 37000, "2025-08": 38000,
        "2025-09": 41000, "2025-10": 43000, "2025-11": 46000, "2025-12": 49000,
        "2026-01": 45000, "2026-02": 47000, "2026-03": 51000, "2026-04": 54000,
        "2026-05": 25000,
    }

    with engine.connect() as conn:
        wbooking_id = int(_s(conn, "SELECT COALESCE(MAX(booking_id),0) FROM fact_service_bookings")) + 1

    RECURRING_SVCS = [sv for sv in W_SERVICES if sv["recurring_flag"] == 1]
    PROJECT_SVCS   = [sv for sv in W_SERVICES if sv["recurring_flag"] == 0]
    wchannels = ["direct", "referral", "website", "email"]
    wweights  = [0.40, 0.30, 0.20, 0.10]

    wbooking_rows = []
    for month_str in wou_monthly:
        yr, mo = int(month_str[:4]), int(month_str[5:])
        m_start = date(yr, mo, 1)
        m_end   = min(
            date(yr, mo+1, 1) - timedelta(days=1) if mo < 12 else date(yr+1, 1, 1) - timedelta(days=1),
            TODAY
        )

        active_recurring_clients = random.sample(W_CUSTOMERS, min(12, len(W_CUSTOMERS)))
        for client in active_recurring_clients:
            sv = random.choice(RECURRING_SVCS)
            bdate  = m_start + timedelta(days=random.randint(1, (m_end - m_start).days))
            uprice = round(sv["price"] * random.uniform(0.97, 1.03), 2)
            ltotal = round(uprice, 2)
            gp     = round(uprice - sv["price"] * 0.19, 2)
            wbooking_rows.append({
                "booking_id":   wbooking_id,
                "service_id":   sv["service_id"],
                "company_id":   CID_W,
                "customer_id":  client["customer_id"],
                "booking_date": bdate.strftime("%Y-%m-%d"),
                "sessions":     1,
                "unit_price":   uprice,
                "line_total":   ltotal,
                "gross_profit": gp,
                "channel":      random.choices(wchannels, weights=wweights)[0],
                "status":       "cancelled" if random.random() < 0.04 else "completed",
            })
            wbooking_id += 1

        for _ in range(random.randint(3, 6)):
            sv    = random.choice(PROJECT_SVCS)
            bdate = m_start + timedelta(days=random.randint(1, (m_end - m_start).days))
            uprice = round(sv["price"] * random.uniform(0.90, 1.10), 2)
            ltotal = round(uprice, 2)
            gp     = round((uprice - sv["price"] * 0.18), 2)
            client = random.choice(W_CUSTOMERS)
            wbooking_rows.append({
                "booking_id":   wbooking_id,
                "service_id":   sv["service_id"],
                "company_id":   CID_W,
                "customer_id":  client["customer_id"],
                "booking_date": bdate.strftime("%Y-%m-%d"),
                "sessions":     1,
                "unit_price":   uprice,
                "line_total":   ltotal,
                "gross_profit": gp,
                "channel":      random.choices(wchannels, weights=wweights)[0],
                "status":       "cancelled" if random.random() < 0.05 else "completed",
            })
            wbooking_id += 1

    booking_count = _ins(engine, pd.DataFrame(wbooking_rows), "fact_service_bookings")

    # ── Expenses (monthly) ────────────────────────────────────────────────────
    with engine.connect() as conn:
        wexp_id = int(_s(conn, "SELECT COALESCE(MAX(expense_id),0) FROM fact_expenses")) + 1

    wexp_rows = []
    for month_str, rev in wou_monthly.items():
        yr, mo = int(month_str[:4]), int(month_str[5:])
        dt = date(yr, mo, 1).strftime("%Y-%m-%d")
        for cat, vendor, amt_fn in [
            ("Payroll",   "HR Payroll",      lambda r: r * 0.38),
            ("Software",  "SaaS Tools",      lambda r: 1850.0),
            ("Rent",      "Office Landlord", lambda r: 2800.0),
            ("Marketing", "Ad Agency",       lambda r: r * 0.06),
            ("Utilities", "City Utilities",  lambda r: 320.0),
            ("Supplies",  "Office Depot",    lambda r: r * 0.01),
        ]:
            amt = round(amt_fn(rev) * random.uniform(0.93, 1.07), 2)
            wexp_rows.append({
                "expense_id": wexp_id, "company_id": CID_W, "date": dt,
                "expense_category": cat, "vendor_name": vendor,
                "amount": amt, "recurring_flag": 1
            })
            wexp_id += 1
    exp_count = _ins(engine, pd.DataFrame(wexp_rows), "fact_expenses")

    # ── Marketing (daily) ──────────────────────────────────────────────────────
    with engine.connect() as conn:
        wmkt_id = int(_s(conn, "SELECT COALESCE(MAX(record_id),0) FROM fact_marketing")) + 1

    wcamp_w = [0.35, 0.30, 0.20, 0.15]
    wmkt_rows = []
    d_w = START_DATE
    while d_w <= TODAY:
        ms_w   = d_w.strftime("%Y-%m")
        rev_w  = wou_monthly.get(ms_w, 40000)
        daily_spend_w = (rev_w * 0.06) / 30
        for i, camp in enumerate(W_CAMPAIGNS):
            spend_w = round(daily_spend_w * wcamp_w[i] * random.uniform(0.8, 1.2), 2)
            imp_w   = int(spend_w * random.uniform(120, 250))
            clk_w   = int(imp_w   * random.uniform(0.03, 0.10))
            lds_w   = int(clk_w   * random.uniform(0.15, 0.35))
            conv_w  = int(lds_w   * random.uniform(0.08, 0.20))
            wmkt_rows.append({
                "record_id": wmkt_id, "campaign_id": camp["campaign_id"],
                "date": d_w.strftime("%Y-%m-%d"),
                "impressions": imp_w, "clicks": clk_w, "leads": lds_w, "conversions": conv_w,
                "spend": spend_w,
                "revenue_attributed": round(spend_w * random.uniform(2.5, 5.5), 2),
                "company_id": CID_W,
            })
            wmkt_id += 1
        d_w += timedelta(days=1)
    mkt_count = _ins(engine, pd.DataFrame(wmkt_rows), "fact_marketing")

    # ── Cash flow (monthly) ────────────────────────────────────────────────────
    with engine.connect() as conn:
        wcf_id = int(_s(conn, "SELECT COALESCE(MAX(transaction_id),0) FROM fact_cash_flow")) + 1

    wcf_rows = []
    wbalance = 55000.0
    wcf_rows.append({
        "transaction_id": wcf_id, "company_id": CID_W,
        "date": "2025-01-01 00:00:00", "type": "inflow",
        "category": "Opening Balance", "amount": wbalance,
        "payment_method": "bank_transfer", "source_id": None,
        "description": "Opening cash balance", "signed_amount": wbalance
    })
    wcf_id += 1

    def _wou_exp_total(rev):
        return rev * 0.38 + 1850 + 2800 + rev * 0.06 + 320 + rev * 0.01

    for month_str, rev in wou_monthly.items():
        yr, mo = int(month_str[:4]), int(month_str[5:])
        dt = f"{yr}-{mo:02d}-15 00:00:00"
        collected = round(rev * 0.93, 2)
        wcf_rows.append({
            "transaction_id": wcf_id, "company_id": CID_W, "date": dt,
            "type": "inflow", "category": "Service Revenue", "amount": collected,
            "payment_method": "bank_transfer", "source_id": None,
            "description": f"Services {month_str}", "signed_amount": collected
        })
        wcf_id += 1

        total_wexp = round(_wou_exp_total(rev), 2)
        wcf_rows.append({
            "transaction_id": wcf_id, "company_id": CID_W,
            "date": f"{yr}-{mo:02d}-15 12:00:00",
            "type": "outflow", "category": "Operating Expenses", "amount": total_wexp,
            "payment_method": "bank_transfer", "source_id": None,
            "description": f"Expenses {month_str}", "signed_amount": -total_wexp
        })
        wcf_id += 1
    cf_count = _ins(engine, pd.DataFrame(wcf_rows), "fact_cash_flow")

    return {
        "status": "ok",
        "company_id": CID_W,
        "user_id": W_USER_ID,
        "rows": {
            "dim_services":          svc_count,
            "dim_customers":         cust_count,
            "dim_campaigns":         camp_count,
            "fact_service_bookings": booking_count,
            "fact_expenses":         exp_count,
            "fact_marketing":        mkt_count,
            "fact_cash_flow":        cf_count,
        }
    }
