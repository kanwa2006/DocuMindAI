"""
Task 6-F3: PDF table extraction preserving row/column structure.
Task 6-F4: Indian financial format normalization.
Task 6-F8: IFRS / Ind AS / US GAAP detection + line-item aliases.
"""
import re
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # graceful degradation if not installed

# ── Task 6-F4: Indian numeric pattern ─────────────────────────────────────────

INDIAN_NUMERIC_PATTERN = re.compile(
    r'[₹\$€£]?\s?(\d{1,2}(?:,\d{2})*(?:,\d{3})?(?:\.\d{1,2})?)'
    r'|\b(\d+(?:\.\d+)?)\s*(lakh|lac|crore|cr|thousand|k)\b',
    re.IGNORECASE,
)


def normalize_indian_number(value_str: str) -> Optional[float]:
    """
    Convert Indian financial notation to absolute float.
    Examples:
        "₹1,23,456"   → 123456.0
        "45.5 crore"  → 455000000.0
        "12 lakh"     → 1200000.0
    """
    value_str = value_str.strip().replace(",", "")
    multiplier = 1.0

    if re.search(r'crore|cr\.?\b', value_str, re.I):
        multiplier = 10_000_000.0
        value_str = re.sub(r'crore|cr\.?\b', '', value_str, flags=re.I)
    elif re.search(r'lakh|lac\b', value_str, re.I):
        multiplier = 100_000.0
        value_str = re.sub(r'lakh|lac\b', '', value_str, flags=re.I)

    value_str = re.sub(r'[₹\$€£\s]', '', value_str)

    try:
        return float(value_str) * multiplier
    except ValueError:
        return None


def detect_statement_unit(table: dict) -> tuple:
    """
    Detect if a table's values are in thousands, lakhs, or crores.
    Returns (unit_label, multiplier).
    """
    all_text = " ".join(table.get("headers", [])).lower()
    if "crore" in all_text or "cr." in all_text:
        return "crores", 10_000_000.0
    if "lakh" in all_text or "lac" in all_text:
        return "lakhs", 100_000.0
    if "thousand" in all_text:
        return "thousands", 1_000.0
    if "million" in all_text:
        return "millions", 1_000_000.0
    return "absolute", 1.0


# ── Task 6-F3: PDF table extraction ───────────────────────────────────────────

def extract_financial_tables(pdf_path: str) -> list:
    """
    Extract all tables from a PDF preserving row/column structure.
    Returns list of tables, each with page_number, headers, and rows.
    """
    if not pdfplumber:
        return []

    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_tables = page.extract_tables(table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
            })
            for table in (page_tables or []):
                if not table or len(table) < 2:
                    continue
                headers = [str(cell or "").strip() for cell in table[0]]
                rows = [
                    [str(cell or "").strip() for cell in row]
                    for row in table[1:]
                ]
                tables.append({
                    "page_number": page_num,
                    "headers": headers,
                    "rows": rows,
                    "raw_text": str(table),
                })
    return tables


def identify_financial_table_type(table: dict) -> str:
    """Classify which financial statement a table belongs to."""
    text = " ".join(table.get("headers", []) + [
        cell for row in table.get("rows", []) for cell in row
    ]).lower()
    if any(k in text for k in ["revenue", "profit", "loss", "ebitda", "income"]):
        return "profit_loss"
    if any(k in text for k in ["assets", "liabilities", "equity", "balance"]):
        return "balance_sheet"
    if any(k in text for k in ["cash", "operating", "investing", "financing"]):
        return "cash_flow"
    return "unknown"


# ── Task 6-F8: Accounting standard detection ──────────────────────────────────

IFRS_MARKERS = ["IFRS", "IAS", "International Financial Reporting Standards"]
IND_AS_MARKERS = ["Ind AS", "Indian Accounting Standard", "ICAI", "Companies Act 2013"]
US_GAAP_MARKERS = ["US GAAP", "FASB", "ASC 606", "Generally Accepted Accounting"]


def detect_accounting_standard(document_text: str) -> str:
    for marker in IFRS_MARKERS:
        if marker.lower() in document_text.lower():
            return "IFRS"
    for marker in IND_AS_MARKERS:
        if marker.lower() in document_text.lower():
            return "IND_AS"
    for marker in US_GAAP_MARKERS:
        if marker.lower() in document_text.lower():
            return "US_GAAP"
    return "UNKNOWN"


LINE_ITEM_ALIASES = {
    "revenue": [
        "Revenue", "Turnover", "Net Sales", "Revenue from Operations",
        "Revenue from Contracts with Customers",
    ],
    "operating_profit": ["PBIT", "Operating Profit", "EBIT", "Profit from Operations"],
    "net_profit": [
        "PAT", "Profit After Tax", "Net Income", "Net Profit", "Profit for the year",
    ],
    "current_assets": ["Current Assets", "Total Current Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
    "total_equity": [
        "Shareholders' Equity", "Net Worth", "Equity",
        "Total Equity", "Shareholders' Funds",
    ],
    "inventory": ["Inventories", "Stock", "Inventory"],
    "accounts_receivable": ["Trade Receivables", "Debtors", "Accounts Receivable"],
}
