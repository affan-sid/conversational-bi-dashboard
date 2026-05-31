import os

# ── API CONNECTION ───────────────────────────────────────────────
# Flip to False once Affan's FastAPI backend is running
USE_MOCK = False

# Update this when Affan deploys the backend
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── APP SETTINGS ─────────────────────────────────────────────────
APP_TITLE        = "BI Dashboard"
APP_ICON         = "📊"
CURRENCY_SYMBOL  = "$"        # fallback only — pages use currency_symbol() below
CURRENCY_CODE    = "CAD"
DATE_FORMAT      = "%d/%m/%Y"       # display format across the UI

# ── CURRENCY ──────────────────────────────────────────────
CURRENCY_MAP = {
    "USD": "$",     "CAD": "CA$",   "AUD": "A$",    "NZD": "NZ$",
    "GBP": "£",     "EUR": "€",      "INR": "₹",      "JPY": "¥",
    "CNY": "¥",     "CHF": "CHF ",  "SGD": "S$",    "HKD": "HK$",
    "ZAR": "R",     "BRL": "R$",    "MXN": "MX$",   "SEK": "kr",
    "NOK": "kr",    "DKK": "kr",    "AED": "AED ",  "SAR": "SAR ",
    "NGN": "₦",     "KES": "KSh",
}

CURRENCY_OPTIONS = [
    ("CAD – Canadian Dollar",    "CAD"),
    ("USD – US Dollar",          "USD"),
    ("AUD – Australian Dollar",  "AUD"),
    ("GBP – British Pound",      "GBP"),
    ("EUR – Euro",               "EUR"),
    ("INR – Indian Rupee",       "INR"),
    ("NZD – New Zealand Dollar", "NZD"),
    ("SGD – Singapore Dollar",   "SGD"),
    ("HKD – Hong Kong Dollar",   "HKD"),
    ("CHF – Swiss Franc",        "CHF"),
    ("JPY – Japanese Yen",       "JPY"),
    ("AED – UAE Dirham",         "AED"),
    ("NGN – Nigerian Naira",     "NGN"),
    ("KES – Kenyan Shilling",    "KES"),
]

def currency_symbol(code: str = None) -> str:
    """Return display prefix for a currency code, e.g. 'CAD' -> 'CA$'."""
    c = (code or CURRENCY_CODE).upper()
    return CURRENCY_MAP.get(c, c + " ")

# ── DATA CONSTANTS (from your real CSV data) ─────────────────────
SALES_CHANNELS   = ["website", "whatsapp", "sales_rep", "marketplace"]
CUSTOMER_SEGMENTS = ["Retail", "SME", "Corporate"]
EXPENSE_CATEGORIES = [
    "Shipping", "Marketing", "Sales", "Utilities",
    "Supplies", "Payroll", "Rent", "Software"
]
ORDER_STATUSES   = ["completed", "returned"]

# ── ALERT THRESHOLDS ─────────────────────────────────────────────
CASH_RUNWAY_CRITICAL_MONTHS = 3
PROFIT_MARGIN_LOW_PCT       = 15.0
CHURN_RISK_HIGH_THRESHOLD   = 0.7
REPEAT_RATE_LOW_PCT         = 30.0
CAMPAIGN_ROI_MIN            = 0.0

# ── DEFAULT PERIOD ────────────────────────────────────────────────
DEFAULT_PERIOD   = "Last 3 months"
PERIOD_OPTIONS   = ["Last 7 days", "Last 30 days", "Last 3 months", "Last 6 months", "All time"]
PERIOD_API_MAP   = {
    "Last 7 days":   "last_7_days",
    "Last 30 days":  "last_30_days",
    "Last 3 months": "last_3_months",
    "Last 6 months": "last_6_months",
    "All time":      "all_time",
}
