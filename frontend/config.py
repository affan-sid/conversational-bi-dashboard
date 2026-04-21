import os

# ── API CONNECTION ───────────────────────────────────────────────
# Flip to False once Affan's FastAPI backend is running
USE_MOCK = True

# Update this when Affan deploys the backend
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── APP SETTINGS ─────────────────────────────────────────────────
APP_TITLE        = "BI Dashboard"
APP_ICON         = "📊"
CURRENCY_SYMBOL  = "$"
CURRENCY_CODE    = "CAD"
DATE_FORMAT      = "%d/%m/%Y"       # display format across the UI

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
PERIOD_OPTIONS   = ["Last 30 days", "Last 3 months", "Last 6 months", "All time"]
