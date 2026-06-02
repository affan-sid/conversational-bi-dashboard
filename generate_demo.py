"""
Generates 18 months of realistic e-commerce data for kenilp156@gmail.com,
inserts it into the DB, then tests every backend endpoint and compares
expected vs actual values.

Run:  python generate_demo.py
"""
import os, random, hashlib, requests
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "postgresql://postgres:Mayank1717%40%40@localhost:5432/bi_dashboard"
from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine(os.environ["DATABASE_URL"])
random.seed(42)

API      = "http://localhost:8000"
EMAIL    = "kenilp156@gmail.com"
PASSWORD = "Demo1234!"

# ─────────────────────────────────────────────────────────────────────────────
def s(sql, params=None):
    with engine.connect() as c:
        return c.execute(text(sql), params or {}).scalar()

def ins(df, table):
    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=500)
    print(f"  Inserted {len(df):,} rows -> {table}")

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

TODAY      = date(2026, 5, 26)
START_DATE = date(2025, 1, 1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1  Create company + user
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 1: Create company & user ===")
with engine.connect() as conn:
    existing = conn.execute(
        text("SELECT user_id, company_id FROM dim_users WHERE email=:e"), {"e": EMAIL}
    ).fetchone()
    if existing:
        USER_ID, CID = existing[0], existing[1]
        print(f"  User already exists: user_id={USER_ID}, company_id={CID} — wiping old data")
        for t in ["fact_sales","fact_expenses","fact_marketing","fact_cash_flow",
                  "dim_customers","dim_products","dim_campaigns",
                  "fact_service_bookings","dim_services"]:
            conn.execute(text(f"DELETE FROM {t} WHERE company_id=:cid"), {"cid": CID})
        conn.commit()
    else:
        CID = int(conn.execute(text("SELECT COALESCE(MAX(company_id),0)+1 FROM dim_companies")).scalar())
        conn.execute(text(
            "INSERT INTO dim_companies(company_id,company_name,industry,country,currency,created_at)"
            " VALUES(:cid,'KP Fashion Store','Retail','Canada','CAD',NOW())"
        ), {"cid": CID})
        conn.commit()
        USER_ID = int(conn.execute(text("SELECT COALESCE(MAX(user_id),0)+1 FROM dim_users")).scalar())
        conn.execute(text(
            "INSERT INTO dim_users(user_id,company_id,full_name,email,role,password_hash,created_at)"
            " VALUES(:uid,:cid,'KP Store Manager',:email,'manager',:ph,NOW())"
        ), {"uid": USER_ID, "cid": CID, "email": EMAIL, "ph": hash_pw(PASSWORD)})
        conn.commit()
        print(f"  Created company_id={CID}, user_id={USER_ID}")
print(f"  EMAIL={EMAIL}  PASSWORD={PASSWORD}  company_id={CID}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2  Products (25 fashion/lifestyle items)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 2: Products ===")
prod_base_id = int(s("SELECT COALESCE(MAX(product_id),0) FROM dim_products")) + 1
products_raw = [
    ("Casual T-Shirt",     "Apparel",      29.99,  9.00),
    ("Denim Jacket",       "Apparel",      89.99, 28.00),
    ("Running Shoes",      "Footwear",    119.99, 42.00),
    ("Yoga Pants",         "Apparel",      54.99, 18.00),
    ("Leather Belt",       "Accessories",  39.99, 12.00),
    ("Canvas Tote Bag",    "Accessories",  34.99, 10.00),
    ("Baseball Cap",       "Accessories",  24.99,  7.00),
    ("Wireless Earbuds",   "Electronics",  79.99, 25.00),
    ("Phone Case",         "Electronics",  19.99,  5.00),
    ("Water Bottle",       "Lifestyle",    34.99, 11.00),
    ("Sunglasses",         "Accessories",  49.99, 15.00),
    ("Classic Watch",      "Accessories", 149.99, 55.00),
    ("Backpack",           "Bags",         74.99, 24.00),
    ("Hoodie",             "Apparel",      64.99, 20.00),
    ("Sneakers",           "Footwear",     99.99, 35.00),
    ("Wallet",             "Accessories",  44.99, 14.00),
    ("Scarf",              "Apparel",      29.99,  8.00),
    ("Gym Bag",            "Bags",         59.99, 19.00),
    ("Sunscreen SPF50",    "Lifestyle",    22.99,  6.00),
    ("Travel Pillow",      "Lifestyle",    27.99,  8.00),
    ("Cargo Shorts",       "Apparel",      44.99, 14.00),
    ("Sandals",            "Footwear",     49.99, 16.00),
    ("Crossbody Bag",      "Bags",         69.99, 22.00),
    ("Fitness Tracker",    "Electronics",  89.99, 32.00),
    ("Reusable Straw Set", "Lifestyle",    14.99,  4.00),
]
PRODUCTS = [
    {"product_id": prod_base_id+i, "company_id": CID,
     "product_name": p[0], "category": p[1], "price": p[2], "cost": p[3], "active_flag": 1}
    for i, p in enumerate(products_raw)
]
ins(pd.DataFrame(PRODUCTS), "dim_products")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2.5  Services (5 styling/consultation services for the fashion store)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 2.5: Services ===")
svc_base_id = int(s("SELECT COALESCE(MAX(service_id),0) FROM dim_services")) + 1
services_raw = [
    ("Personal Styling Session", "Consulting",  60,  75.00, 20.00),
    ("Wardrobe Consultation",    "Consulting",  90, 120.00, 35.00),
    ("Custom Alteration",        "Tailoring",   30,  45.00, 12.00),
    ("Style Workshop",           "Education",  120, 150.00, 40.00),
    ("Gift Styling Package",     "Consulting",  45,  90.00, 25.00),
]
SERVICES = [
    {"service_id": svc_base_id + i, "company_id": CID,
     "service_name": sv[0], "category": sv[1], "duration_minutes": sv[2],
     "price": sv[3], "recurring_flag": 0, "active_flag": 1,
     "description": f"{sv[0]} — professional {sv[1].lower()} service"}
    for i, sv in enumerate(services_raw)
]
ins(pd.DataFrame(SERVICES), "dim_services")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3  Customers (150)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 3: Customers ===")
cust_base_id = int(s("SELECT COALESCE(MAX(customer_id),0) FROM dim_customers")) + 1
first_names = ["Alice","Bob","Carol","David","Eva","Frank","Grace","Henry","Iris","James",
               "Karen","Leo","Mia","Noah","Olivia","Peter","Quinn","Rachel","Sam","Tina",
               "Uma","Victor","Wendy","Xander","Yasmine","Zach","Amber","Blake","Chloe","Derek",
               "Elena","Felix","Gina","Hank","Isla","Jake","Kira","Liam","Mona","Nate"]
last_names  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Moore",
               "Taylor","Anderson","Thomas","Jackson","White","Harris","Martin","Thompson","Lee","Walker"]
segments = ["Retail"]*105 + ["SME"]*33 + ["Corporate"]*12
cities   = ["Toronto","Vancouver","Montreal","Calgary","Ottawa","Edmonton","Winnipeg","Halifax"]
random.shuffle(segments)

CUSTOMERS = []
for i in range(150):
    joined = START_DATE + timedelta(days=random.randint(0, (TODAY - START_DATE).days - 30))
    CUSTOMERS.append({
        "customer_id": cust_base_id + i,
        "company_id":  CID,
        "full_name":   f"{random.choice(first_names)} {random.choice(last_names)}",
        "email":       f"customer{i}@kpstore.demo",
        "phone":       f"+1-555-{1000+i:04d}",
        "segment":     segments[i],
        "city":        random.choice(cities),
        "country":     "Canada",
        "created_at":  joined.strftime("%Y-%m-%d"),
    })
ins(pd.DataFrame(CUSTOMERS), "dim_customers")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4  Campaigns (5)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 4: Campaigns ===")
camp_base_id = int(s("SELECT COALESCE(MAX(campaign_id),0) FROM dim_campaigns")) + 1
campaigns_raw = [
    ("Instagram Fashion Ads", "Instagram",  18000),
    ("Google Shopping",       "Google Ads", 22000),
    ("Email Newsletter",      "Email",       5000),
    ("TikTok Viral Push",     "TikTok",     12000),
    ("Facebook Retargeting",  "Facebook",   10000),
]
CAMPAIGNS = [
    {"campaign_id": camp_base_id+i, "company_id": CID,
     "campaign_name": c[0], "platform": c[1],
     "start_date": START_DATE.strftime("%Y-%m-%d"),
     "end_date": "2026-12-31", "budget": c[2]}
    for i, c in enumerate(campaigns_raw)
]
ins(pd.DataFrame(CAMPAIGNS), "dim_campaigns")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5  Sales (18 months, realistic seasonal trend)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 5: Sales ===")

monthly_targets = {
    "2025-01": 22000, "2025-02": 27000, "2025-03": 32000, "2025-04": 36000,
    "2025-05": 40000, "2025-06": 47000, "2025-07": 44000, "2025-08": 41000,
    "2025-09": 38000, "2025-10": 45000, "2025-11": 64000, "2025-12": 82000,
    "2026-01": 35000, "2026-02": 42000, "2026-03": 51000, "2026-04": 59000,
    "2026-05": 27000,
}

channels        = ["website","marketplace","whatsapp","sales_rep"]
channel_weights = [0.45, 0.25, 0.18, 0.12]

order_id = int(s("SELECT COALESCE(MAX(order_id),0) FROM fact_sales")) + 1
item_id  = int(s("SELECT COALESCE(MAX(order_item_id),0) FROM fact_sales")) + 1

sales_rows = []
for month_str, target_rev in monthly_targets.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    m_start = date(yr, mo, 1)
    m_end   = min(date(yr, mo+1, 1) - timedelta(days=1) if mo < 12 else date(yr+1,1,1) - timedelta(days=1), TODAY)
    days    = (m_end - m_start).days + 1
    base_daily = max(3, int(target_rev / (days * 80)))
    running = 0.0
    d = m_start
    while d <= m_end and running < target_rev * 1.03:
        mult    = 1.3 if d.weekday() >= 4 else 1.0
        n_ord   = max(1, int(base_daily * mult * random.uniform(0.7, 1.4)))
        for _ in range(n_ord):
            if running >= target_rev * 1.03: break
            prod   = random.choice(PRODUCTS)
            qty    = random.choices([1,2,3], weights=[0.65,0.25,0.10])[0]
            unit   = round(prod["price"] * random.uniform(0.88, 1.06), 2)
            line   = round(unit * qty, 2)
            gp     = round((unit - prod["cost"]) * qty, 2)
            cust   = random.choice(CUSTOMERS)
            chan   = random.choices(channels, weights=channel_weights)[0]
            status = "returned" if random.random() < 0.034 else "completed"
            sales_rows.append({
                "order_item_id": item_id,  "order_id":   order_id,
                "product_id":    prod["product_id"], "quantity": qty,
                "unit_price":    unit, "cost_price": prod["cost"],
                "line_total":    line, "gross_profit": gp,
                "order_date":    d.strftime("%Y-%m-%d"),
                "customer_id":   cust["customer_id"],
                "channel":       chan, "status": status, "company_id": CID,
            })
            running  += line
            item_id  += 1
            order_id += 1
        d += timedelta(days=1)

ins(pd.DataFrame(sales_rows), "fact_sales")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5.5  Service Bookings (18 months, ~8% of monthly revenue)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 5.5: Service Bookings ===")

booking_id = int(s("SELECT COALESCE(MAX(booking_id),0) FROM fact_service_bookings")) + 1
svc_booking_rows = []
for month_str, target_rev in monthly_targets.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    m_start = date(yr, mo, 1)
    m_end   = min(date(yr, mo+1, 1) - timedelta(days=1) if mo < 12 else date(yr+1,1,1) - timedelta(days=1), TODAY)
    monthly_svc_target = target_rev * 0.08
    running_svc = 0.0
    d_svc = m_start
    while d_svc <= m_end and running_svc < monthly_svc_target:
        n_books = max(0, int(random.gauss(2, 1)))
        for _ in range(n_books):
            if running_svc >= monthly_svc_target:
                break
            sv     = random.choice(SERVICES)
            sess   = random.choices([1, 2, 3], weights=[0.70, 0.22, 0.08])[0]
            uprice = round(sv["price"] * random.uniform(0.95, 1.05), 2)
            ltotal = round(uprice * sess, 2)
            gp     = round((uprice - sv["price"] * 0.27) * sess, 2)
            cust   = random.choice(CUSTOMERS)
            chan   = random.choices(channels, weights=channel_weights)[0]
            status = "cancelled" if random.random() < 0.06 else "completed"
            svc_booking_rows.append({
                "booking_id":  booking_id,
                "service_id":  sv["service_id"],
                "company_id":  CID,
                "customer_id": cust["customer_id"],
                "booking_date": d_svc.strftime("%Y-%m-%d"),
                "sessions":    sess,
                "unit_price":  uprice,
                "line_total":  ltotal,
                "gross_profit": gp,
                "channel":     chan,
                "status":      status,
            })
            running_svc += ltotal
            booking_id  += 1
        d_svc += timedelta(days=1)

ins(pd.DataFrame(svc_booking_rows), "fact_service_bookings")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6  Expenses (monthly, 18 months)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 6: Expenses ===")

def exp_amt(cat, rev):
    return {"Payroll":0.28,"Marketing":0.12,"Shipping":0.07,"Supplies":0.02,"Sales":0.04}.get(cat, 0) * rev \
        if cat not in ("Rent","Software","Utilities") \
        else {"Rent":3800,"Software":820,"Utilities":520}[cat]

exp_id = int(s("SELECT COALESCE(MAX(expense_id),0) FROM fact_expenses")) + 1
exp_rows = []
for month_str, rev in monthly_targets.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    dt = date(yr, mo, 1).strftime("%Y-%m-%d")
    for cat, vendor in [("Payroll","HR Payroll"),("Marketing","Ad Agency"),("Shipping","Canada Post"),
                         ("Rent","Property Landlord"),("Software","SaaS Tools"),
                         ("Utilities","City Utilities"),("Supplies","Office Depot"),("Sales","Commission")]:
        amt = round(exp_amt(cat, rev) * random.uniform(0.92, 1.08), 2)
        exp_rows.append({"expense_id":exp_id,"company_id":CID,"date":dt,
                          "expense_category":cat,"vendor_name":vendor,
                          "amount":amt,"recurring_flag":1})
        exp_id += 1
ins(pd.DataFrame(exp_rows), "fact_expenses")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7  Marketing (daily, 18 months)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 7: Marketing ===")

camp_weights = [0.28, 0.32, 0.08, 0.20, 0.12]
mkt_id = int(s("SELECT COALESCE(MAX(record_id),0) FROM fact_marketing")) + 1
mkt_rows = []
d = START_DATE
while d <= TODAY:
    ms  = d.strftime("%Y-%m")
    rev = monthly_targets.get(ms, 40000)
    daily_spend = (rev * 0.12) / 30
    for i, camp in enumerate(CAMPAIGNS):
        spend = round(daily_spend * camp_weights[i] * random.uniform(0.8,1.2), 2)
        imp   = int(spend * random.uniform(180,320))
        clk   = int(imp  * random.uniform(0.025,0.09))
        lds   = int(clk  * random.uniform(0.12,0.30))
        conv  = int(lds  * random.uniform(0.06,0.18))
        mkt_rows.append({
            "record_id":mkt_id,"campaign_id":camp["campaign_id"],"date":d.strftime("%Y-%m-%d"),
            "impressions":imp,"clicks":clk,"leads":lds,"conversions":conv,
            "spend":spend,"revenue_attributed":round(spend*random.uniform(1.8,4.2),2),
            "company_id":CID,
        })
        mkt_id += 1
    d += timedelta(days=1)
ins(pd.DataFrame(mkt_rows), "fact_marketing")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8  Cash flow (monthly summaries)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 8: Cash flow ===")

cf_id   = int(s("SELECT COALESCE(MAX(transaction_id),0) FROM fact_cash_flow")) + 1
cf_rows = []
balance = 80000.0
cf_rows.append({"transaction_id":cf_id,"company_id":CID,"date":"2025-01-01 00:00:00",
                 "type":"inflow","category":"Opening Balance","amount":balance,
                 "payment_method":"bank_transfer","source_id":None,
                 "description":"Opening cash balance","signed_amount":balance})
cf_id += 1

for month_str, rev in monthly_targets.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    dt = f"{yr}-{mo:02d}-15 00:00:00"
    collected = round(rev * 0.90, 2)
    cf_rows.append({"transaction_id":cf_id,"company_id":CID,"date":dt,
                     "type":"inflow","category":"Sales Revenue","amount":collected,
                     "payment_method":"bank_transfer","source_id":None,
                     "description":f"Sales {month_str}","signed_amount":collected})
    cf_id  += 1; balance += collected

    total_exp = sum(round(exp_amt(c, rev), 2) for c in
                    ["Payroll","Marketing","Shipping","Rent","Software","Utilities","Supplies","Sales"])
    cf_rows.append({"transaction_id":cf_id,"company_id":CID,"date":f"{yr}-{mo:02d}-15 12:00:00",
                     "type":"outflow","category":"Operating Expenses","amount":total_exp,
                     "payment_method":"bank_transfer","source_id":None,
                     "description":f"Expenses {month_str}","signed_amount":-total_exp})
    cf_id  += 1; balance -= total_exp

ins(pd.DataFrame(cf_rows), "fact_cash_flow")

# =============================================================================
# WOUESSI DIGITAL AGENCY — services-only demo company
# This is the company shown when users click "Try Demo".
# The demo@wouessi.com account is pre-created here so /auth/demo-login reuses it.
# =============================================================================

DEMO_EMAIL_W  = "demo@wouessi.com"
DEMO_PW_W     = "WouessDemo2024!"

print("\n=== WOUESSI DEMO: Company & user ===")

def hash_pw_w(p): return hashlib.sha256(p.encode()).hexdigest()

with engine.connect() as conn:
    existing_w = conn.execute(
        text("SELECT user_id, company_id FROM dim_users WHERE email=:e"), {"e": DEMO_EMAIL_W}
    ).fetchone()

    if existing_w:
        W_USER_ID, CID_W = existing_w[0], existing_w[1]
        print(f"  Wouessi user exists: user_id={W_USER_ID}, company_id={CID_W} — wiping old data")
        for t in ["fact_service_bookings", "dim_services", "fact_expenses",
                  "fact_marketing", "fact_cash_flow", "dim_customers", "dim_campaigns",
                  "fact_sales", "dim_products"]:
            conn.execute(text(f"DELETE FROM {t} WHERE company_id=:cid"), {"cid": CID_W})
        conn.commit()
    else:
        CID_W = int(conn.execute(text("SELECT COALESCE(MAX(company_id),0)+1 FROM dim_companies")).scalar())
        conn.execute(text(
            "INSERT INTO dim_companies(company_id,company_name,industry,country,currency,created_at)"
            " VALUES(:cid,'Wouessi Digital Agency','Digital Services','Canada','CAD',NOW())"
        ), {"cid": CID_W})
        conn.commit()
        W_USER_ID = int(conn.execute(text("SELECT COALESCE(MAX(user_id),0)+1 FROM dim_users")).scalar())
        conn.execute(text(
            "INSERT INTO dim_users(user_id,company_id,full_name,email,role,password_hash,created_at)"
            " VALUES(:uid,:cid,'Wouessi Demo','demo@wouessi.com','viewer',:ph,NOW())"
        ), {"uid": W_USER_ID, "cid": CID_W, "ph": hash_pw_w(DEMO_PW_W)})
        conn.commit()
        print(f"  Created Wouessi company_id={CID_W}, user_id={W_USER_ID}")

print(f"  Demo login will use company_id={CID_W}")

# ── Wouessi services catalogue ────────────────────────────────────────────────
print("\n=== WOUESSI DEMO: Services ===")
wsvc_base = int(s("SELECT COALESCE(MAX(service_id),0) FROM dim_services")) + 1
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
ins(pd.DataFrame(W_SERVICES), "dim_services")

# ── Wouessi clients (25 SME clients) ─────────────────────────────────────────
print("\n=== WOUESSI DEMO: Clients ===")
wcust_base = int(s("SELECT COALESCE(MAX(customer_id),0) FROM dim_customers")) + 1
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
     "email": f"contact{i}@{company_names[i].lower().replace(' ','')}.demo",
     "phone": f"+1-416-{2000+i:04d}",
     "segment": wseg[i], "city": random.choice(wcity),
     "country": "Canada",
     "created_at": (START_DATE + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d")}
    for i in range(25)
]
ins(pd.DataFrame(W_CUSTOMERS), "dim_customers")

# ── Wouessi campaigns (4 digital campaigns) ───────────────────────────────────
print("\n=== WOUESSI DEMO: Campaigns ===")
wcamp_base = int(s("SELECT COALESCE(MAX(campaign_id),0) FROM dim_campaigns")) + 1
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
ins(pd.DataFrame(W_CAMPAIGNS), "dim_campaigns")

# ── Wouessi service bookings (18 months) ──────────────────────────────────────
print("\n=== WOUESSI DEMO: Service Bookings ===")

# Recurring services: each active client books once per month
# Project services: random bookings throughout the year
RECURRING_SVCS = [sv for sv in W_SERVICES if sv["recurring_flag"] == 1]
PROJECT_SVCS   = [sv for sv in W_SERVICES if sv["recurring_flag"] == 0]

wou_monthly = {
    "2025-01": 22000, "2025-02": 25000, "2025-03": 29000, "2025-04": 33000,
    "2025-05": 36000, "2025-06": 39000, "2025-07": 37000, "2025-08": 38000,
    "2025-09": 41000, "2025-10": 43000, "2025-11": 46000, "2025-12": 49000,
    "2026-01": 45000, "2026-02": 47000, "2026-03": 51000, "2026-04": 54000,
    "2026-05": 25000,
}

wbooking_id = int(s("SELECT COALESCE(MAX(booking_id),0) FROM fact_service_bookings")) + 1
wbooking_rows = []
wchannels = ["direct", "referral", "website", "email"]
wweights  = [0.40, 0.30, 0.20, 0.10]

for month_str in wou_monthly:
    yr, mo = int(month_str[:4]), int(month_str[5:])
    m_start = date(yr, mo, 1)
    m_end   = min(date(yr, mo+1, 1) - timedelta(days=1) if mo < 12 else date(yr+1,1,1) - timedelta(days=1), TODAY)

    # Recurring: each client on a recurring service gets one booking this month
    active_recurring_clients = random.sample(W_CUSTOMERS, min(12, len(W_CUSTOMERS)))
    for client in active_recurring_clients:
        sv = random.choice(RECURRING_SVCS)
        bdate = m_start + timedelta(days=random.randint(1, (m_end - m_start).days))
        uprice = round(sv["price"] * random.uniform(0.97, 1.03), 2)
        ltotal = round(uprice, 2)
        gp     = round(uprice - sv["price"] * 0.19, 2)
        wbooking_rows.append({
            "booking_id":   wbooking_id, "service_id":  sv["service_id"],
            "company_id":   CID_W,       "customer_id": client["customer_id"],
            "booking_date": bdate.strftime("%Y-%m-%d"),
            "sessions":     1, "unit_price": uprice, "line_total": ltotal,
            "gross_profit": gp,
            "channel":      random.choices(wchannels, weights=wweights)[0],
            "status":       "cancelled" if random.random() < 0.04 else "completed",
        })
        wbooking_id += 1

    # Projects: 3-6 new project bookings per month
    for _ in range(random.randint(3, 6)):
        sv    = random.choice(PROJECT_SVCS)
        bdate = m_start + timedelta(days=random.randint(1, (m_end - m_start).days))
        uprice = round(sv["price"] * random.uniform(0.90, 1.10), 2)
        sess  = 1
        ltotal = round(uprice * sess, 2)
        gp     = round((uprice - sv["price"] * 0.18) * sess, 2)
        client = random.choice(W_CUSTOMERS)
        wbooking_rows.append({
            "booking_id":   wbooking_id, "service_id":  sv["service_id"],
            "company_id":   CID_W,       "customer_id": client["customer_id"],
            "booking_date": bdate.strftime("%Y-%m-%d"),
            "sessions":     sess, "unit_price": uprice, "line_total": ltotal,
            "gross_profit": gp,
            "channel":      random.choices(wchannels, weights=wweights)[0],
            "status":       "cancelled" if random.random() < 0.05 else "completed",
        })
        wbooking_id += 1

ins(pd.DataFrame(wbooking_rows), "fact_service_bookings")

# ── Wouessi expenses (monthly) ────────────────────────────────────────────────
print("\n=== WOUESSI DEMO: Expenses ===")
wexp_id = int(s("SELECT COALESCE(MAX(expense_id),0) FROM fact_expenses")) + 1
wexp_rows = []
for month_str, rev in wou_monthly.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    dt = date(yr, mo, 1).strftime("%Y-%m-%d")
    for cat, vendor, amt_fn in [
        ("Payroll",   "HR Payroll",       lambda r: r * 0.38),
        ("Software",  "SaaS Tools",       lambda r: 1850.0),
        ("Rent",      "Office Landlord",  lambda r: 2800.0),
        ("Marketing", "Ad Agency",        lambda r: r * 0.06),
        ("Utilities", "City Utilities",   lambda r: 320.0),
        ("Supplies",  "Office Depot",     lambda r: r * 0.01),
    ]:
        amt = round(amt_fn(rev) * random.uniform(0.93, 1.07), 2)
        wexp_rows.append({"expense_id": wexp_id, "company_id": CID_W, "date": dt,
                           "expense_category": cat, "vendor_name": vendor,
                           "amount": amt, "recurring_flag": 1})
        wexp_id += 1
ins(pd.DataFrame(wexp_rows), "fact_expenses")

# ── Wouessi marketing performance ────────────────────────────────────────────
print("\n=== WOUESSI DEMO: Marketing ===")
wcamp_w = [0.35, 0.30, 0.20, 0.15]
wmkt_id = int(s("SELECT COALESCE(MAX(record_id),0) FROM fact_marketing")) + 1
wmkt_rows = []
d_w = START_DATE
while d_w <= TODAY:
    ms_w = d_w.strftime("%Y-%m")
    rev_w = wou_monthly.get(ms_w, 40000)
    daily_spend_w = (rev_w * 0.06) / 30
    for i, camp in enumerate(W_CAMPAIGNS):
        spend_w = round(daily_spend_w * wcamp_w[i] * random.uniform(0.8, 1.2), 2)
        imp_w   = int(spend_w * random.uniform(120, 250))
        clk_w   = int(imp_w  * random.uniform(0.03, 0.10))
        lds_w   = int(clk_w  * random.uniform(0.15, 0.35))
        conv_w  = int(lds_w  * random.uniform(0.08, 0.20))
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
ins(pd.DataFrame(wmkt_rows), "fact_marketing")

# ── Wouessi cash flow ─────────────────────────────────────────────────────────
print("\n=== WOUESSI DEMO: Cash flow ===")
wcf_id  = int(s("SELECT COALESCE(MAX(transaction_id),0) FROM fact_cash_flow")) + 1
wcf_rows = []
wbalance = 55000.0
wcf_rows.append({"transaction_id": wcf_id, "company_id": CID_W,
                  "date": "2025-01-01 00:00:00", "type": "inflow",
                  "category": "Opening Balance", "amount": wbalance,
                  "payment_method": "bank_transfer", "source_id": None,
                  "description": "Opening cash balance", "signed_amount": wbalance})
wcf_id += 1

def wou_exp_total(rev):
    return rev*0.38 + 1850 + 2800 + rev*0.06 + 320 + rev*0.01

for month_str, rev in wou_monthly.items():
    yr, mo = int(month_str[:4]), int(month_str[5:])
    dt = f"{yr}-{mo:02d}-15 00:00:00"
    collected = round(rev * 0.93, 2)
    wcf_rows.append({"transaction_id": wcf_id, "company_id": CID_W, "date": dt,
                      "type": "inflow", "category": "Service Revenue", "amount": collected,
                      "payment_method": "bank_transfer", "source_id": None,
                      "description": f"Services {month_str}", "signed_amount": collected})
    wcf_id += 1; wbalance += collected

    total_wexp = round(wou_exp_total(rev), 2)
    wcf_rows.append({"transaction_id": wcf_id, "company_id": CID_W,
                      "date": f"{yr}-{mo:02d}-15 12:00:00",
                      "type": "outflow", "category": "Operating Expenses", "amount": total_wexp,
                      "payment_method": "bank_transfer", "source_id": None,
                      "description": f"Expenses {month_str}", "signed_amount": -total_wexp})
    wcf_id += 1; wbalance -= total_wexp

ins(pd.DataFrame(wcf_rows), "fact_cash_flow")

print(f"\n  Wouessi demo ready — Try Demo will log in as company_id={CID_W}")
print(f"  Direct login: {DEMO_EMAIL_W} / {DEMO_PW_W}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9  Compute expected values from DB
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 9: Expected values (straight from DB) ===")

def qs(sql):
    with engine.connect() as c: return c.execute(text(sql)).scalar()
def qr(sql):
    with engine.connect() as c:
        r = c.execute(text(sql)); cols = list(r.keys())
        return [dict(zip(cols, row)) for row in r.fetchall()]

PERIODS = [
    ("all_time",      "100 years"),
    ("last_6_months", "6 months"),
    ("last_3_months", "3 months"),
    ("last_30_days",  "30 days"),
    ("last_7_days",   "7 days"),
]

expected = {}
for pkey, interval in PERIODS:
    rev  = float(qs(f"SELECT COALESCE(SUM(line_total),0) FROM fact_sales WHERE status='completed' AND company_id={CID} AND CAST(order_date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    exp_ = float(qs(f"SELECT COALESCE(SUM(amount),0) FROM fact_expenses WHERE company_id={CID} AND CAST(date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    ord_ = int(qs(f"SELECT COUNT(*) FROM fact_sales WHERE status='completed' AND company_id={CID} AND CAST(order_date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    ret_ = int(qs(f"SELECT COUNT(*) FROM fact_sales WHERE status='returned' AND company_id={CID} AND CAST(order_date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    cust = int(qs(f"SELECT COUNT(DISTINCT customer_id) FROM fact_sales WHERE status='completed' AND company_id={CID} AND CAST(order_date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    avg_ = float(qs(f"SELECT COALESCE(AVG(line_total),0) FROM fact_sales WHERE status='completed' AND company_id={CID} AND CAST(order_date AS DATE)>=NOW()-INTERVAL '{interval}'"))
    margin = round((rev-exp_)/rev*100,1) if rev else 0
    expected[pkey] = {"revenue":rev,"expenses":exp_,"net_profit":rev-exp_,
                       "profit_margin":margin,"orders":ord_,"returned":ret_,
                       "avg_order_value":round(avg_,2),"active_customers":cust}
    print(f"\n  [{pkey}]  Revenue=${rev:,.0f}  Expenses=${exp_:,.0f}  Margin={margin}%  Orders={ord_}  ActiveCust={cust}")

print("\n  [Monthly Revenue - last 6 months]")
for r in qr(f"""
    SELECT TO_CHAR(DATE_TRUNC('month',CAST(order_date AS DATE)),'Mon YYYY') AS month,
           SUM(line_total) AS revenue, COUNT(*) AS orders
    FROM fact_sales WHERE status='completed' AND company_id={CID}
      AND CAST(order_date AS DATE)>=NOW()-INTERVAL '6 months'
    GROUP BY DATE_TRUNC('month',CAST(order_date AS DATE))
    ORDER BY DATE_TRUNC('month',CAST(order_date AS DATE))
"""):
    print(f"    {r['month']}: ${float(r['revenue']):,.0f}  ({r['orders']} orders)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10  Login & test every API endpoint
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 10: API endpoint tests ===")

resp = requests.post(f"{API}/auth/login", json={"email":EMAIL,"password":PASSWORD})
if resp.status_code != 200:
    print(f"  LOGIN FAILED: {resp.text}"); exit(1)
token   = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"  Login OK")

def check(label, actual, expected_val, fmt=",.0f"):
    ok = abs(actual - expected_val) < 2
    tag = "OK" if ok else f"MISMATCH (expected {expected_val:{fmt}})"
    return f"{label}=${actual:{fmt}} [{tag}]"

print("\n  FINANCE:")
for pkey, _ in PERIODS:
    r = requests.get(f"{API}/api/finance/summary", params={"period":pkey}, headers=headers)
    if r.status_code != 200: print(f"    [{pkey}] HTTP {r.status_code}"); continue
    d = r.json()
    if not d.get("has_data",True): print(f"    [{pkey}] has_data=False"); continue
    k = d["kpis"]; e = expected[pkey]
    rev_ok = abs(k["total_revenue"] - e["revenue"]) < 2
    exp_ok = abs(k["total_expenses"] - e["expenses"]) < 2
    trend  = len(d.get("monthly_trend",[]))
    print(f"    [{pkey:15s}] Rev=${k['total_revenue']:>10,.0f} {'OK' if rev_ok else 'MISMATCH':8s} | Exp=${k['total_expenses']:>9,.0f} {'OK' if exp_ok else 'MISMATCH':8s} | trend_rows={trend}")

print("\n  SALES:")
for pkey, _ in PERIODS:
    r = requests.get(f"{API}/api/sales/summary", params={"period":pkey}, headers=headers)
    if r.status_code != 200: print(f"    [{pkey}] HTTP {r.status_code}"); continue
    d = r.json()
    if not d.get("has_data",True): print(f"    [{pkey}] has_data=False"); continue
    k = d["kpis"]; e = expected[pkey]
    ord_ok = k["total_orders"] == e["orders"]
    print(f"    [{pkey:15s}] Orders={k['total_orders']:>5} {'OK' if ord_ok else 'MISMATCH(exp '+str(e['orders'])+')':35s} | Channels={len(d.get('revenue_by_channel',[]))} | Products={len(d.get('top_products',[]))}")

print("\n  MARKETING:")
for pkey, _ in PERIODS:
    r = requests.get(f"{API}/api/marketing/summary", params={"period":pkey}, headers=headers)
    if r.status_code != 200: print(f"    [{pkey}] HTTP {r.status_code}"); continue
    d = r.json()
    if not d.get("has_data",True): print(f"    [{pkey}] has_data=False"); continue
    k = d["kpis"]
    print(f"    [{pkey:15s}] Spend=${k['total_spend']:>9,.0f} | ROI={k['overall_roi']:.2f}x | Campaigns={len(d.get('campaign_performance',[]))}")

print("\n  CUSTOMERS:")
for pkey, _ in PERIODS:
    r = requests.get(f"{API}/api/customers/summary", params={"period":pkey}, headers=headers)
    if r.status_code != 200: print(f"    [{pkey}] HTTP {r.status_code}"); continue
    d = r.json()
    if not d.get("has_data",True): print(f"    [{pkey}] has_data=False"); continue
    k = d["kpis"]; e = expected[pkey]
    tot_ok = k["total_customers"] == 150
    act_ok = k["active_customers"] == e["active_customers"]
    print(f"    [{pkey:15s}] Total={k['total_customers']} {'OK' if tot_ok else 'MISMATCH':6s} | Active={k['active_customers']:>4} {'OK' if act_ok else 'MISMATCH(exp '+str(e['active_customers'])+')':35s} | Repeat={k['repeat_rate']:.1f}%")

print(f"\n=== ALL DONE ===")
print(f"  Login: {EMAIL}  /  {PASSWORD}")
