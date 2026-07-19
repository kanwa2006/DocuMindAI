from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any, Optional
import uuid
import asyncio
import re
import json
import time
import logging
from datetime import datetime

from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.finance import FinancialDocument, Transaction, AuditFinding, FinancialRule
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.legal_analysis import ExtractionAudit
from app.schemas.finance import FinancialDocumentResponse, AuditFindingResponse, InvoiceExtractionSchema, AnomalyDetectionSchema
from app.services.llm_service import llm_service
from app.services.financial_table_extractor import (
    detect_accounting_standard, LINE_ITEM_ALIASES, normalize_indian_number,
)
from app.workers.tasks.finance_tasks import process_finance_batch

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Task 6-F1: Numerical integrity pattern ────────────────────────────────────

NUMBER_PATTERN = re.compile(
    r'[₹$€£¥]?\s?\d{1,3}(?:[,.]\d{2,3})*(?:\.\d{1,2})?'
)

# ── Task 6-F2 / 6-F5: Ratio formula reference ────────────────────────────────

RATIO_FORMULAS = {
    "Current Ratio":          "Current Assets / Current Liabilities",
    "Quick Ratio":            "Quick Assets / Current Liabilities",
    "Cash Ratio":             "Cash & Equivalents / Current Liabilities",
    "Net Profit Margin":      "(Net Profit / Revenue) × 100",
    "Gross Margin":           "((Revenue - COGS) / Revenue) × 100",
    "Operating Margin":       "(Operating Profit / Revenue) × 100",
    "EBITDA Margin":          "(EBITDA / Revenue) × 100",
    "Return on Equity (ROE)": "(Net Profit / Total Equity) × 100",
    "Debt-to-Equity":         "Total Liabilities / Total Equity",
    "Debt-to-Assets":         "Total Liabilities / Total Assets",
    "Interest Coverage":      "EBITDA or Operating Profit / Interest Expense",
    "Inventory Turnover":     "COGS / Inventory",
    "Receivables Turnover":   "Revenue / Accounts Receivable",
    "Asset Turnover":         "Revenue / Total Assets",
    "Payables Days":          "(Accounts Payable / COGS) × 365",
    "Receivables Days (DSO)": "(Accounts Receivable / Revenue) × 365",
}

# ── Request/Response schemas ──────────────────────────────────────────────────

class RatioRequest(BaseModel):
    document_ids: List[str]

class CompareRequest(BaseModel):
    period_doc_ids: dict  # e.g. {"FY2022": "doc_id_1", "FY2023": "doc_id_2"}

# ── Task 6-F2: Core ratio computation — Python ONLY, never LLM ───────────────

def _safe_div(num, denom) -> Optional[float]:
    """Division guard: returns None on zero/None denominator."""
    if num is None or denom is None or denom == 0:
        return None
    return round(num / denom, 4)


def _get(extracted: dict, key: str) -> Optional[float]:
    val = extracted.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _make_ratio(name: str, value, inputs_used: dict, source_citation: str = "") -> dict:
    return {
        "name": name,
        "value": value,
        "formula": RATIO_FORMULAS.get(name, ""),
        "inputs_used": inputs_used,
        "source_citation": source_citation,
    }


def compute_ratios(extracted: dict) -> list:
    """
    CRITICAL: Python computes ALL ratios. LLM never does arithmetic.
    `extracted` is the dict of raw line items from LLM extraction.
    Returns list of 15 ratio dicts.
    """
    ratios = []

    # ── Liquidity ─────────────────────────────────────────────────────────────
    cr = _safe_div(_get(extracted, "current_assets"), _get(extracted, "current_liabilities"))
    ratios.append(_make_ratio("Current Ratio", cr, {
        "current_assets": _get(extracted, "current_assets"),
        "current_liabilities": _get(extracted, "current_liabilities"),
    }))

    qr = _safe_div(_get(extracted, "quick_assets"), _get(extracted, "current_liabilities"))
    ratios.append(_make_ratio("Quick Ratio", qr, {
        "quick_assets": _get(extracted, "quick_assets"),
        "current_liabilities": _get(extracted, "current_liabilities"),
    }))

    cash_r = _safe_div(_get(extracted, "cash_and_equivalents"), _get(extracted, "current_liabilities"))
    ratios.append(_make_ratio("Cash Ratio", cash_r, {
        "cash_and_equivalents": _get(extracted, "cash_and_equivalents"),
        "current_liabilities": _get(extracted, "current_liabilities"),
    }))

    # ── Profitability ─────────────────────────────────────────────────────────
    npm_raw = _safe_div(_get(extracted, "net_profit"), _get(extracted, "revenue"))
    npm = round(npm_raw * 100, 4) if npm_raw is not None else None
    ratios.append(_make_ratio("Net Profit Margin", npm, {
        "net_profit": _get(extracted, "net_profit"),
        "revenue": _get(extracted, "revenue"),
    }))

    revenue, cogs = _get(extracted, "revenue"), _get(extracted, "cogs")
    gross_profit = (revenue - cogs) if (revenue is not None and cogs is not None) else None
    gm_raw = _safe_div(gross_profit, revenue)
    gm = round(gm_raw * 100, 4) if gm_raw is not None else None
    ratios.append(_make_ratio("Gross Margin", gm, {"revenue": revenue, "cogs": cogs}))

    opm_raw = _safe_div(_get(extracted, "operating_profit"), _get(extracted, "revenue"))
    opm = round(opm_raw * 100, 4) if opm_raw is not None else None
    ratios.append(_make_ratio("Operating Margin", opm, {
        "operating_profit": _get(extracted, "operating_profit"),
        "revenue": _get(extracted, "revenue"),
    }))

    ebitda_m_raw = _safe_div(_get(extracted, "ebitda"), _get(extracted, "revenue"))
    ebitda_m = round(ebitda_m_raw * 100, 4) if ebitda_m_raw is not None else None
    ratios.append(_make_ratio("EBITDA Margin", ebitda_m, {
        "ebitda": _get(extracted, "ebitda"),
        "revenue": _get(extracted, "revenue"),
    }))

    roe_raw = _safe_div(_get(extracted, "net_profit"), _get(extracted, "total_equity"))
    roe = round(roe_raw * 100, 4) if roe_raw is not None else None
    ratios.append(_make_ratio("Return on Equity (ROE)", roe, {
        "net_profit": _get(extracted, "net_profit"),
        "total_equity": _get(extracted, "total_equity"),
    }))

    # ── Leverage ──────────────────────────────────────────────────────────────
    dte = _safe_div(_get(extracted, "total_liabilities"), _get(extracted, "total_equity"))
    ratios.append(_make_ratio("Debt-to-Equity", dte, {
        "total_liabilities": _get(extracted, "total_liabilities"),
        "total_equity": _get(extracted, "total_equity"),
    }))

    dta = _safe_div(_get(extracted, "total_liabilities"), _get(extracted, "total_assets"))
    ratios.append(_make_ratio("Debt-to-Assets", dta, {
        "total_liabilities": _get(extracted, "total_liabilities"),
        "total_assets": _get(extracted, "total_assets"),
    }))

    # ── Coverage ──────────────────────────────────────────────────────────────
    interest = _get(extracted, "interest_expense")
    ebitda_or_op = _get(extracted, "ebitda") or _get(extracted, "operating_profit")
    if interest == 0:
        ratios.append({
            "name": "Interest Coverage", "value": None,
            "formula": RATIO_FORMULAS["Interest Coverage"],
            "error": "No debt", "inputs_used": {}, "source_citation": "",
        })
    else:
        ic = _safe_div(ebitda_or_op, interest)
        ratios.append(_make_ratio("Interest Coverage", ic, {
            "ebitda_or_operating_profit": ebitda_or_op,
            "interest_expense": interest,
        }))

    # ── Efficiency ────────────────────────────────────────────────────────────
    inventory = _get(extracted, "inventory")
    if inventory == 0:
        ratios.append({
            "name": "Inventory Turnover", "value": None,
            "formula": RATIO_FORMULAS["Inventory Turnover"],
            "error": "N/A", "inputs_used": {}, "source_citation": "",
        })
    else:
        it_val = _safe_div(_get(extracted, "cogs"), inventory)
        ratios.append(_make_ratio("Inventory Turnover", it_val, {
            "cogs": _get(extracted, "cogs"),
            "inventory": inventory,
        }))

    rt = _safe_div(_get(extracted, "revenue"), _get(extracted, "accounts_receivable"))
    ratios.append(_make_ratio("Receivables Turnover", rt, {
        "revenue": _get(extracted, "revenue"),
        "accounts_receivable": _get(extracted, "accounts_receivable"),
    }))

    at = _safe_div(_get(extracted, "revenue"), _get(extracted, "total_assets"))
    ratios.append(_make_ratio("Asset Turnover", at, {
        "revenue": _get(extracted, "revenue"),
        "total_assets": _get(extracted, "total_assets"),
    }))

    pd_raw = _safe_div(_get(extracted, "accounts_payable"), _get(extracted, "cogs"))
    pd_val = round(pd_raw * 365, 4) if pd_raw is not None else None
    ratios.append(_make_ratio("Payables Days", pd_val, {
        "accounts_payable": _get(extracted, "accounts_payable"),
        "cogs": _get(extracted, "cogs"),
    }))

    dso_raw = _safe_div(_get(extracted, "accounts_receivable"), _get(extracted, "revenue"))
    dso = round(dso_raw * 365, 4) if dso_raw is not None else None
    ratios.append(_make_ratio("Receivables Days (DSO)", dso, {
        "accounts_receivable": _get(extracted, "accounts_receivable"),
        "revenue": _get(extracted, "revenue"),
    }))

    return ratios


def _ratio_status(name: str, value) -> str:
    """Derive Good/Caution/Risk status for frontend ratio cards."""
    if value is None:
        return "N/A"
    benchmarks = {
        "Current Ratio":      (2.0, 1.0),
        "Quick Ratio":        (1.0, 0.5),
        "Cash Ratio":         (0.5, 0.2),
        "Net Profit Margin":  (10.0, 0.0),
        "Gross Margin":       (30.0, 10.0),
        "Operating Margin":   (15.0, 0.0),
        "EBITDA Margin":      (20.0, 5.0),
        "Return on Equity (ROE)": (15.0, 5.0),
        "Debt-to-Equity":     (None, 2.0),   # lower = better
        "Debt-to-Assets":     (None, 0.6),
        "Interest Coverage":  (3.0, 1.5),
        "Inventory Turnover": (6.0, 2.0),
        "Asset Turnover":     (1.0, 0.5),
    }
    b = benchmarks.get(name)
    if not b:
        return "N/A"
    high, low = b
    if high is None:
        # lower-is-better ratios
        return "Good" if value <= low else "Risk"
    return "Good" if value >= high else ("Caution" if value >= low else "Risk")


# ── Task 6-F1: Numerical integrity validation ─────────────────────────────────

def _validate_values(response_text: str, source_chunks: list) -> list:
    """
    Extract all numerical values from LLM response and assign confidence
    based on whether they appear in source chunks.
    """
    extracted_values = NUMBER_PATTERN.findall(response_text)
    flagged = []
    chunk_text = " ".join(c.get("text_content", "") for c in source_chunks)

    for val in extracted_values:
        val_clean = val.replace(",", "").replace("₹", "").replace("$", "").strip()
        if not val_clean:
            continue
        if val_clean in chunk_text.replace(",", ""):
            confidence = 0.95
            verified = True
        else:
            try:
                num = float(val_clean)
                # check approximate match within 5%
                approx_found = any(
                    abs(float(t) - num) / max(abs(num), 1) <= 0.05
                    for t in re.findall(r'\d+(?:\.\d+)?', chunk_text)
                    if t
                )
                confidence = 0.70 if approx_found else 0.35
                verified = approx_found
            except ValueError:
                confidence = 0.35
                verified = False
        flagged.append({"value": val, "confidence": confidence, "verified": verified})

    return flagged


# ── Helper: fetch and concatenate document chunks ─────────────────────────────

async def _get_document_text(db: AsyncSession, document_id: uuid.UUID) -> tuple:
    """Returns (full_text, chunks_list) for a document."""
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    text = "\n".join(c.text_content for c in chunks)
    chunks_data = [{"text_content": c.text_content, "chunk_index": c.chunk_index} for c in chunks]
    return text, chunks_data


# ── Helper: LLM extraction prompt for financial line items ────────────────────

def _build_extraction_prompt(doc_text: str, accounting_standard: str) -> tuple:
    aliases_hint = "\n".join(
        f'  "{k}": also known as {", ".join(v)}'
        for k, v in LINE_ITEM_ALIASES.items()
    )
    system_prompt = (
        "You are a financial data extraction assistant. "
        "Return ONLY a valid JSON object — no prose, no markdown, no explanation. "
        "Extract the following financial line items from the provided document text. "
        f"Detected accounting standard: {accounting_standard}. "
        "Use these aliases to find values under different terminology:\n"
        f"{aliases_hint}\n\n"
        "For each field, return an object with: value (float or null), raw_text (the exact "
        "text you read), page_number (int or null), table_row (str or null), "
        "table_column (str or null), confidence (0.0-1.0).\n"
        "Fields: current_assets, current_liabilities, total_assets, total_liabilities, "
        "net_profit, total_equity, revenue, cogs, inventory, accounts_receivable, "
        "quick_assets, ebitda, interest_expense, depreciation_amortization, "
        "operating_profit, accounts_payable, short_term_borrowings, "
        "cash_and_equivalents, capital_expenditure, long_term_debt."
    )
    user_prompt = f"Document text (first 12000 chars):\n{doc_text[:12000]}"
    return system_prompt, user_prompt


# ── Task 6-F7: Trend computation — Python ONLY ────────────────────────────────

def _compute_trend(period_values: dict) -> str:
    values = [v for v in period_values.values() if v is not None]
    if len(values) < 2:
        return "insufficient_data"
    if values[-1] > values[0] * 1.05:
        return "improving"
    if values[-1] < values[0] * 0.95:
        return "declining"
    return "stable"


def _compute_yoy(period_values: dict) -> dict:
    periods = list(period_values.keys())
    yoy = {}
    for i in range(1, len(periods)):
        prev_key, curr_key = periods[i - 1], periods[i]
        prev_val, curr_val = period_values[prev_key], period_values[curr_key]
        if prev_val is not None and curr_val is not None and prev_val != 0:
            change = round(((curr_val - prev_val) / abs(prev_val)) * 100, 2)
            yoy[f"{prev_key}→{curr_key}"] = change
    return yoy

@router.post("/process")
async def process_financial_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC FINANCE PROCESSING
    Offloads heavy table extraction and audit finding generation to Celery workers.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_finance_batch.delay(str(document_id), str(workspace_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/finance/{document_id}")
async def sse_finance_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push finance processing status.
    """
    # M-1: real Document.status transitions instead of a fake heartbeat.
    from app.services.processing_events import document_status_event_stream
    return StreamingResponse(
        document_status_event_stream(document_id, current_user["id"]),
        media_type="text/event-stream",
    )

@router.get("/transactions/search")
async def semantic_search_transactions(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: FINANCIAL VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across historical transactions.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    
    # Generate query embedding
    query_embedding = await llm_service.get_embedding(query)
    
    # Search closest transactions via <-> L2 distance
    stmt = (
        select(Transaction, FinancialDocument)
        .join(FinancialDocument, Transaction.financial_doc_id == FinancialDocument.id)
        .where(Transaction.workspace_id == workspace_id)
        .order_by(Transaction.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for txn, doc in result.all():
        matches.append({
            "vendor_name": doc.vendor_name,
            "description": txn.description,
            "amount": txn.amount,
            "currency": txn.currency,
            "is_anomaly": txn.is_anomaly,
            "anomaly_reason": txn.anomaly_reason
        })
    return matches

@router.get("/documents", response_model=List[FinancialDocumentResponse])
async def list_financial_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(FinancialDocument).where(FinancialDocument.workspace_id == workspace_id).order_by(FinancialDocument.created_at.desc()))
    return result.scalars().all()

@router.get("/findings", response_model=List[AuditFindingResponse])
async def list_audit_findings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(AuditFinding).where(AuditFinding.workspace_id == workspace_id).order_by(AuditFinding.created_at.desc()))
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6-F — NEW ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ratios")
async def compute_financial_ratios(
    request: RatioRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Task 6-F2 + 6-F5 + 6-F6 + 6-F8:
    LLM extracts line items → Python computes all 15 ratios with full traceability.
    NEVER lets the LLM compute ratios.
    """
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="At least one document_id is required.")

    doc_id = uuid.UUID(request.document_ids[0])

    # Verify document ownership
    doc = (await db.execute(
        select(Document).where(Document.id == doc_id)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Fetch document chunks
    doc_text, chunks_data = await _get_document_text(db, doc_id)
    if not doc_text.strip():
        raise HTTPException(status_code=422, detail="Document has no extractable text.")

    # Detect accounting standard (Task 6-F8)
    accounting_standard = detect_accounting_standard(doc_text)

    # LLM extraction — structured JSON only
    t0 = time.time()
    system_prompt, user_prompt = _build_extraction_prompt(doc_text, accounting_standard)
    try:
        raw_llm = await llm_service.generate(system_prompt, user_prompt)
        # Strip markdown fences if present
        raw_llm = re.sub(r'^```(?:json)?\s*', '', raw_llm.strip(), flags=re.MULTILINE)
        raw_llm = re.sub(r'```\s*$', '', raw_llm.strip(), flags=re.MULTILINE)
        extraction_data = json.loads(raw_llm)
    except Exception as exc:
        logger.warning(f"[finance/ratios] LLM extraction parse failed: {exc}")
        extraction_data = {}

    # Normalize: extract .value from each field if nested
    extracted: dict = {}
    extraction_spans: dict = {}
    for field, data in extraction_data.items():
        if isinstance(data, dict):
            raw_val = data.get("value")
            extracted[field] = raw_val
            extraction_spans[field] = {
                "value": raw_val,
                "raw_text": data.get("raw_text", ""),
                "page_number": data.get("page_number"),
                "table_row": data.get("table_row", ""),
                "table_column": data.get("table_column", ""),
                "confidence": data.get("confidence", 0.5),
                "verified": data.get("confidence", 0.5) >= 0.85,
            }
        else:
            extracted[field] = data

    # Apply Indian number normalization to string values (Task 6-F4)
    for field, val in extracted.items():
        if isinstance(val, str):
            normalized = normalize_indian_number(val)
            if normalized is not None:
                extracted[field] = normalized

    # Python computes ALL 15 ratios (Task 6-F2 / 6-F5)
    ratios = compute_ratios(extracted)

    # Enrich ratios with traceability (Task 6-F6) and status
    for ratio in ratios:
        ratio["status"] = _ratio_status(ratio["name"], ratio.get("value"))
        # Attach input traceability
        inputs_trace = {}
        for inp_name in ratio.get("inputs_used", {}):
            if inp_name in extraction_spans:
                inputs_trace[inp_name] = extraction_spans[inp_name]
        if inputs_trace:
            ratio["inputs"] = inputs_trace

    # Task 6-F1: Numerical integrity validation on extracted values
    flagged_values = _validate_values(
        " ".join(str(v) for v in extracted.values() if v is not None),
        chunks_data,
    )

    # Persist extraction audit rows (Task 6-F6)
    try:
        for field, span in extraction_spans.items():
            if span.get("value") is not None:
                audit_row = ExtractionAudit(
                    document_id=doc_id,
                    line_item=field,
                    extracted_value=span["value"],
                    raw_text_span=str(span.get("raw_text", ""))[:500],
                    page_number=span.get("page_number"),
                    table_row=str(span.get("table_row", ""))[:200],
                    table_column=str(span.get("table_column", ""))[:100],
                    confidence=span.get("confidence"),
                )
                db.add(audit_row)
        await db.commit()
    except Exception as exc:
        logger.warning(f"[finance/ratios] Audit row persistence failed: {exc}")

    return {
        "accounting_standard": accounting_standard,
        "extracted_line_items": extracted,
        "ratios": ratios,
        "flagged_values": flagged_values,
        "document_id": str(doc_id),
        "filename": doc.filename,
    }


@router.post("/compare")
async def compare_financial_periods(
    request: CompareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Task 6-F7: Multi-period ratio comparison.
    Runs full ratio extraction for each period and computes YoY trends.
    """
    if len(request.period_doc_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two periods required for comparison.",
        )

    period_ratios: dict = {}

    for period_label, doc_id_str in request.period_doc_ids.items():
        try:
            doc_id = uuid.UUID(doc_id_str)
            doc_text, _ = await _get_document_text(db, doc_id)
            if not doc_text.strip():
                period_ratios[period_label] = {}
                continue
            accounting_standard = detect_accounting_standard(doc_text)
            system_prompt, user_prompt = _build_extraction_prompt(doc_text, accounting_standard)
            raw_llm = await llm_service.generate(system_prompt, user_prompt)
            raw_llm = re.sub(r'^```(?:json)?\s*', '', raw_llm.strip(), flags=re.MULTILINE)
            raw_llm = re.sub(r'```\s*$', '', raw_llm.strip(), flags=re.MULTILINE)
            extraction_data = json.loads(raw_llm)
            extracted = {
                k: (v.get("value") if isinstance(v, dict) else v)
                for k, v in extraction_data.items()
            }
            # Normalize Indian numbers
            for field, val in extracted.items():
                if isinstance(val, str):
                    n = normalize_indian_number(val)
                    if n is not None:
                        extracted[field] = n
            ratios = compute_ratios(extracted)
            period_ratios[period_label] = {r["name"]: r.get("value") for r in ratios}
        except Exception as exc:
            logger.warning(f"[finance/compare] Period {period_label} failed: {exc}")
            period_ratios[period_label] = {}

    # Build comparison response — Python computes trends
    periods = list(request.period_doc_ids.keys())
    all_ratio_names = list(RATIO_FORMULAS.keys())
    comparison_ratios = []

    for ratio_name in all_ratio_names:
        period_values = {p: period_ratios.get(p, {}).get(ratio_name) for p in periods}
        trend = _compute_trend(period_values)
        yoy = _compute_yoy(period_values)
        comparison_ratios.append({
            "name": ratio_name,
            "formula": RATIO_FORMULAS.get(ratio_name, ""),
            "values": period_values,
            "trend": trend,
            "yoy_changes": yoy,
        })

    return {
        "periods": periods,
        "ratios": comparison_ratios,
    }
