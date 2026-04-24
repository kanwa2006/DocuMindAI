"""
Enhanced PDF extraction v2.1:
- Multi-strategy table extraction (PyMuPDF find_tables → pdfplumber fallback)
- Layout-aware heading / section detection via font-size analysis
- Confidence-based OCR with fallback chain per page
- Per-page error isolation (one bad page doesn't kill the whole document)
"""
import os
import io
import re


def process_pdf(file_path: str, images_dir: str) -> tuple:
    os.makedirs(images_dir, exist_ok=True)
    all_text_parts = []
    image_paths = []

    try:
        import fitz
        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                page_text = page.get_text("text") or ""

                if len(page_text.strip()) < 80:
                    # Scanned page — run enhanced OCR with fallback chain
                    ocr_text = _ocr_with_fallback(page, page_num, images_dir, image_paths)
                    content = ocr_text if len(ocr_text.strip()) > len(page_text.strip()) else page_text
                    if not content.strip():
                        content = "[Image content — OCR returned no text]"
                else:
                    # Digital page — extract layout + tables
                    layout_text = _extract_layout_with_headings(page)
                    table_text  = _extract_tables_robust(file_path, page, page_num)
                    content     = f"{layout_text}\n\n{table_text}".strip() if table_text else layout_text

                all_text_parts.append(f"[Page {page_num + 1}]\n{content}")

            except Exception as page_err:
                print(f"[OCR] Skipping page {page_num + 1} due to error: {page_err}")
                all_text_parts.append(f"[Page {page_num + 1}]\n[Page extraction failed]")

        doc.close()

    except ImportError:
        return _pdfplumber_fallback(file_path, images_dir)
    except Exception as e:
        print(f"[OCR Error] {e}")
        return _pdfplumber_fallback(file_path, images_dir)

    return "\n\n".join(all_text_parts), image_paths


# ── Layout extraction with heading detection ───────────────────────────────────

def _extract_layout_with_headings(page) -> str:
    """
    Extract text preserving reading order.
    Detects headings by font size relative to the page median.
    Marks detected headings with ## prefix for downstream chunking.
    """
    try:
        data = page.get_text("dict")
        blocks = data.get("blocks", [])

        # Collect all font sizes to compute median
        all_sizes = []
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("size"):
                        all_sizes.append(span["size"])

        median_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 12
        heading_threshold = median_size * 1.25  # 25% larger than median = heading

        # Sort blocks top→bottom, left→right
        blocks_sorted = sorted(blocks, key=lambda b: (round(b.get("bbox", [0,0])[1] / 15), b.get("bbox", [0,0])[0]))

        parts = []
        for block in blocks_sorted:
            if block.get("type") != 0:  # 0 = text block
                continue
            block_lines = []
            for line in block.get("lines", []):
                line_text = ""
                is_heading = False
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    flags = span.get("flags", 0)
                    bold = bool(flags & 2**4)  # bit 4 = bold
                    if text:
                        line_text += text + " "
                        if size >= heading_threshold or bold:
                            is_heading = True
                line_text = line_text.strip()
                if line_text:
                    block_lines.append(f"## {line_text}" if is_heading else line_text)

            if block_lines:
                parts.append("\n".join(block_lines))

        return "\n\n".join(parts) if parts else (page.get_text("text") or "")

    except Exception:
        return page.get_text("text") or ""


# ── Table extraction — multi-strategy with validation ─────────────────────────

def _extract_tables_robust(file_path: str, page, page_num: int) -> str:
    """
    Multi-strategy table extraction:
    1. PyMuPDF find_tables() — works on digital PDFs with line-based tables
    2. pdfplumber fallback — works on PDFs where PyMuPDF misses tables
    Validates that extracted table has ≥2 rows and ≥2 columns before accepting.
    """
    # Strategy 1: PyMuPDF built-in table finder
    try:
        tables = page.find_tables()
        if tables and tables.tables:
            parts = []
            for t_idx, table in enumerate(tables.tables):
                rows = table.extract()
                if not rows or len(rows) < 2:
                    continue
                n_cols = max(len(r) for r in rows)
                if n_cols < 2:
                    continue
                md = _rows_to_markdown(rows, t_idx)
                if md:
                    parts.append(md)
            if parts:
                return "\n\n".join(parts)
    except Exception as e:
        print(f"[Table PyMuPDF] page {page_num + 1}: {e}")

    # Strategy 2: pdfplumber fallback
    return _extract_tables_pdfplumber(file_path, page_num)


def _extract_tables_pdfplumber(file_path: str, page_num: int) -> str:
    """pdfplumber table extraction with merged-cell handling."""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if page_num >= len(pdf.pages):
                return ""
            page = pdf.pages[page_num]
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                    "join_tolerance": 3,
                }
            )
            if not tables:
                # Fallback: looser detection for borderless tables
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                    }
                )
            if not tables:
                return ""

            parts = []
            for t_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                n_cols = max(len(r) for r in table if r)
                if n_cols < 2:
                    continue
                rows = [[str(c or "").replace("\n", " ").strip() for c in row]
                        for row in table]
                md = _rows_to_markdown(rows, t_idx)
                if md:
                    parts.append(md)
            return "\n\n".join(parts)

    except Exception as e:
        print(f"[Table pdfplumber] page {page_num + 1}: {e}")
        return ""


def _rows_to_markdown(rows: list, t_idx: int) -> str:
    """Convert a list-of-lists table to a validated Markdown table string."""
    if not rows:
        return ""
    n_cols = max(len(r) for r in rows)
    if n_cols < 2:
        return ""

    # Pad short rows
    padded = [r + [""] * (n_cols - len(r)) for r in rows]
    lines  = []
    for i, row in enumerate(padded):
        lines.append("| " + " | ".join(cell for cell in row) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * n_cols) + " |")

    non_empty = sum(1 for r in padded[1:] for c in r if c.strip())
    if non_empty == 0:
        return ""  # skip empty tables

    return f"[TABLE {t_idx + 1}]\n" + "\n".join(lines)


# ── OCR with fallback chain + basic confidence ─────────────────────────────────

def _ocr_with_fallback(page, page_num: int, images_dir: str, image_paths: list) -> str:
    """
    Fallback chain:
    1. Enhanced OCR (300 DPI + preprocessing)  — best quality
    2. Basic OCR (200 DPI, no preprocessing)    — if numpy/Pillow preprocessing fails
    3. PyMuPDF raw text                          — last resort
    Also checks OCR confidence and warns if low.
    """
    # Try enhanced first
    result = _ocr_page_enhanced(page, page_num, images_dir, image_paths)
    if result and _ocr_confidence_ok(result):
        return result

    # Try basic
    result_basic = _ocr_page_basic(page, page_num, images_dir, image_paths)
    if result_basic and len(result_basic.strip()) > len((result or "").strip()):
        return result_basic

    # Use whatever we got from enhanced, even if low confidence
    return result or result_basic or ""


def _ocr_confidence_ok(text: str, min_ratio: float = 0.3) -> bool:
    """
    Basic confidence check: alphanumeric ratio.
    If < 30% of characters are alphanumeric, OCR likely produced garbage.
    """
    if not text or len(text) < 20:
        return False
    alnum = sum(c.isalnum() for c in text)
    return (alnum / len(text)) >= min_ratio


def _ocr_page_enhanced(page, page_num: int, images_dir: str, image_paths: list) -> str:
    """300 DPI + contrast + sharpness + median filter + binarization → Tesseract psm 3."""
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
        img = Image.fromarray(np.where(arr > thr, 255, 0).astype(np.uint8), mode="L")

        img_path = os.path.join(images_dir, f"page_{page_num + 1}_ocr.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)

        raw = pytesseract.image_to_string(img, config=r"--oem 3 --psm 3", lang="eng")
        return _clean_ocr_output(raw)

    except ImportError:
        return ""
    except Exception as e:
        print(f"[OCR Enhanced] page {page_num + 1}: {e}")
        return ""


def _ocr_page_basic(page, page_num: int, images_dir: str, image_paths: list) -> str:
    """200 DPI basic OCR — no numpy required."""
    try:
        import pytesseract
        from PIL import Image
        import fitz

        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        img_path = os.path.join(images_dir, f"page_{page_num + 1}_basic.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)

        return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")
    except Exception as e:
        print(f"[OCR Basic] page {page_num + 1}: {e}")
        return ""


def _clean_ocr_output(text: str) -> str:
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


def _pdfplumber_fallback(file_path: str, images_dir: str) -> tuple:
    parts = []
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                parts.append(f"[Page {i + 1}]\n{page.extract_text() or ''}")
    except Exception as e:
        print(f"[pdfplumber fallback error]: {e}")
        return "Could not extract text from this PDF.", []
    return "\n\n".join(parts), []
