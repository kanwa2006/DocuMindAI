"""
Exact Reconstruction Pipeline — page-level fidelity layer.

DOES NOT replace or modify the RAG pipeline.
Runs as a separate background job after upload.

For each page it stores:
  - Full-page image (PNG)  → for "Copy as image" / visual fidelity
  - OCR text               → copyable text layer
  - Tables (structured)    → copy as real table
  - Confidence score       → high/medium/low per page
  - Page metadata          → page size, type (digital/scanned)

Results stored under: storage/{user_id}/recon/{doc_uuid}/pages.json
                      storage/{user_id}/recon/{doc_uuid}/page_{N}.png
"""
import os
import io
import re
import json
import base64
import time
from typing import Optional


# ── Main entry point ───────────────────────────────────────────────────────────

def reconstruct_document(
    file_path: str,
    recon_dir: str,
    progress_callback=None,
) -> dict:
    """
    Process every page of a PDF and store page image + OCR + tables.

    progress_callback(page_num, total_pages, stage, eta_seconds)
    Returns summary dict.
    """
    os.makedirs(recon_dir, exist_ok=True)

    try:
        import fitz
    except ImportError:
        return {"error": "PyMuPDF not available", "pages": []}

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return {"error": str(e), "pages": []}

    total = len(doc)
    pages_meta = []
    start_time = time.time()

    for page_num in range(total):
        page_start = time.time()

        # ETA estimate (rolling average of time-per-page so far)
        elapsed = time.time() - start_time
        avg_per_page = elapsed / (page_num + 1) if page_num > 0 else 3.0
        remaining = (total - page_num - 1) * avg_per_page

        if progress_callback:
            progress_callback(page_num + 1, total, "rendering", int(remaining))

        try:
            page = doc[page_num]
            page_meta = _process_page(page, page_num, recon_dir, file_path)
            pages_meta.append(page_meta)
        except Exception as e:
            pages_meta.append({
                "page": page_num + 1,
                "error": str(e),
                "confidence": "low",
                "type": "unknown",
                "has_image": False,
                "has_text": False,
                "has_tables": False,
            })

        if progress_callback:
            progress_callback(page_num + 1, total, "done_page", int(remaining))

    doc.close()

    summary = {
        "total_pages": total,
        "pages": pages_meta,
        "ready": True,
    }
    # Persist to disk so we don't reprocess
    meta_path = os.path.join(recon_dir, "pages.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


# ── Per-page processing ────────────────────────────────────────────────────────

def _process_page(page, page_num: int, recon_dir: str, file_path: str) -> dict:
    """Extract image + text + tables + confidence for one page."""
    result = {
        "page": page_num + 1,
        "confidence": "high",
        "type": "digital",
        "has_image": False,
        "has_text": False,
        "has_tables": False,
        "text": "",
        "tables": [],
        "image_file": None,
        "ocr_used": False,
    }

    # 1. Render full-page image (150 DPI — good balance of quality/size)
    try:
        import fitz
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_filename = f"page_{page_num + 1}.png"
        img_path = os.path.join(recon_dir, img_filename)
        pix.save(img_path)
        result["has_image"] = True
        result["image_file"] = img_filename
    except Exception as e:
        result["image_error"] = str(e)

    # 2. Extract text (digital path)
    raw_text = ""
    try:
        raw_text = page.get_text("text") or ""
    except Exception:
        pass

    # 3. Decide: digital or scanned
    if len(raw_text.strip()) >= 80:
        # Digital page — use layout-aware extraction
        result["type"] = "digital"
        result["text"] = _extract_layout(page)
        result["confidence"] = _compute_confidence(result["text"])
        result["ocr_used"] = False
    else:
        # Scanned page — OCR
        result["type"] = "scanned"
        result["ocr_used"] = True
        ocr_text = _ocr_page(page, page_num)
        result["text"] = ocr_text
        result["confidence"] = _compute_confidence(ocr_text)

    # 4. ALWAYS attempt table extraction (works for digital; may catch
    #    line-based tables in scanned pages too via geometric detection)
    try:
        result["tables"] = _extract_page_tables(file_path, page, page_num)
        result["has_tables"] = len(result["tables"]) > 0
    except Exception:
        result["tables"] = []
        result["has_tables"] = False

    result["has_text"] = len(result.get("text", "").strip()) > 10

    return result


# ── Text extraction (digital pages) ───────────────────────────────────────────

def _extract_layout(page) -> str:
    try:
        data = page.get_text("dict")
        blocks = sorted(
            data.get("blocks", []),
            key=lambda b: (round(b.get("bbox", [0, 0])[1] / 15), b.get("bbox", [0, 0])[0])
        )
        all_sizes = [
            span["size"]
            for b in blocks
            for line in b.get("lines", [])
            for span in line.get("spans", [])
            if span.get("size")
        ]
        median_sz = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 12
        heading_thr = median_sz * 1.25

        parts = []
        for block in blocks:
            if block.get("type") != 0:
                continue
            lines_out = []
            for line in block.get("lines", []):
                line_text = ""
                is_heading = False
                for span in line.get("spans", []):
                    t = span.get("text", "").strip()
                    sz = span.get("size", 0)
                    bold = bool(span.get("flags", 0) & 2**4)
                    if t:
                        line_text += t + " "
                        if sz >= heading_thr or bold:
                            is_heading = True
                line_text = line_text.strip()
                if line_text:
                    lines_out.append(f"## {line_text}" if is_heading else line_text)
            if lines_out:
                parts.append("\n".join(lines_out))
        return "\n\n".join(parts) if parts else (page.get_text("text") or "")
    except Exception:
        return page.get_text("text") or ""


# ── OCR (scanned pages) ────────────────────────────────────────────────────────

def _ocr_page(page, page_num: int) -> str:
    """Try enhanced OCR → basic OCR → empty."""
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageEnhance
        import numpy as np
        import fitz

        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")

        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        img = img.filter(ImageFilter.MedianFilter(size=3))

        arr = np.array(img, dtype=np.float32)
        thr = arr.mean() * 0.85
        img = Image.fromarray(
            __import__("numpy").where(arr > thr, 255, 0).astype(__import__("numpy").uint8),
            mode="L"
        )
        raw = pytesseract.image_to_string(img, config=r"--oem 3 --psm 3", lang="eng")
        return _clean_text(raw)
    except Exception:
        pass

    # Basic fallback
    try:
        import pytesseract
        from PIL import Image
        import fitz

        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")
    except Exception:
        return ""


# ── Table extraction ───────────────────────────────────────────────────────────

def _extract_page_tables(file_path: str, page, page_num: int) -> list:
    """Return list of tables as dicts with headers + rows."""
    tables = []

    # Strategy 1: PyMuPDF
    try:
        found = page.find_tables()
        if found and found.tables:
            for tbl in found.tables:
                rows = tbl.extract()
                if not rows or len(rows) < 2:
                    continue
                n_cols = max(len(r) for r in rows)
                if n_cols < 2:
                    continue
                padded = [r + [""] * (n_cols - len(r)) for r in rows]
                headers = [str(c or "").strip() for c in padded[0]]
                data_rows = [[str(c or "").strip() for c in row] for row in padded[1:]]
                tables.append({"headers": headers, "rows": data_rows, "source": "pymupdf"})
            if tables:
                return tables
    except Exception:
        pass

    # Strategy 2: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if page_num < len(pdf.pages):
                p = pdf.pages[page_num]
                for settings in [
                    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
                    {"vertical_strategy": "text", "horizontal_strategy": "text"},
                ]:
                    extracted = p.extract_tables(table_settings=settings)
                    if extracted:
                        for tbl in extracted:
                            if not tbl or len(tbl) < 2:
                                continue
                            n_cols = max(len(r) for r in tbl if r)
                            if n_cols < 2:
                                continue
                            clean = [[str(c or "").replace("\n", " ").strip() for c in row] for row in tbl]
                            headers = clean[0]
                            data_rows = clean[1:]
                            tables.append({"headers": headers, "rows": data_rows, "source": "pdfplumber"})
                        if tables:
                            break
    except Exception:
        pass

    return tables


# ── Confidence scoring ─────────────────────────────────────────────────────────

def _compute_confidence(text: str) -> str:
    """Return 'high', 'medium', or 'low' based on text quality."""
    if not text or len(text.strip()) < 20:
        return "low"
    alnum = sum(c.isalnum() for c in text)
    ratio = alnum / len(text)
    if ratio >= 0.55:
        return "high"
    elif ratio >= 0.35:
        return "medium"
    return "low"


# ── Text cleanup ───────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            cleaned.append("")
            continue
        if len(s) > 2 and sum(c.isalnum() for c in s) < 2:
            continue
        cleaned.append(re.sub(r" {3,}", "  ", s))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()


# ── Load cached reconstruction ─────────────────────────────────────────────────

def load_reconstruction(recon_dir: str) -> Optional[dict]:
    """Load cached pages.json if it exists."""
    meta_path = os.path.join(recon_dir, "pages.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_page_image_b64(recon_dir: str, page_num: int) -> Optional[str]:
    """Return base64-encoded PNG for a page (1-indexed)."""
    img_path = os.path.join(recon_dir, f"page_{page_num}.png")
    if not os.path.exists(img_path):
        return None
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")
