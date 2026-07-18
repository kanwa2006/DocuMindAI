import logging
from typing import Dict, Any, List
from pydantic import BaseModel
import sys

logger = logging.getLogger(__name__)

# PHASE 1 & 2: GLOBAL MODEL LOADING
# Models are loaded once at worker boot to prevent VRAM fragmentation and latency
_paddle_ocr_instance = None
_docling_converter_instance = None

def get_paddle_ocr():
    global _paddle_ocr_instance
    if _paddle_ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR (Real Engine)...")
            # C-3: PaddleOCR 3.x removed use_gpu/use_angle_cls — device
            # selection follows the installed paddlepaddle build (CPU build →
            # CPU), and rotated-text handling is use_textline_orientation.
            # Instantiating with the removed 2.x kwargs raised TypeError,
            # which the old `except ImportError` never caught.
            _paddle_ocr_instance = PaddleOCR(use_textline_orientation=True, lang='en')
        except Exception as exc:
            logger.error(f"PaddleOCR unavailable ({exc}). Falling back to mock.")
            _paddle_ocr_instance = "MOCK"
    return _paddle_ocr_instance

def get_docling_converter():
    global _docling_converter_instance
    if _docling_converter_instance is None:
        try:
            from docling.document_converter import DocumentConverter
            logger.info("Initializing Docling Converter (Real Engine)...")
            _docling_converter_instance = DocumentConverter()
        except Exception as exc:
            logger.error(f"Docling unavailable ({exc}). Falling back to mock.")
            _docling_converter_instance = "MOCK"
    return _docling_converter_instance


class OCREngineResult(BaseModel):
    engine_name: str
    text: str
    confidence: float
    tables: List[Dict[str, Any]] = []
    formulas: List[Dict[str, Any]] = []
    bounding_boxes: List[Dict[str, Any]] = []

class BaseOCREngine:
    async def extract(self, file_path: str, mime_type: str) -> OCREngineResult:
        raise NotImplementedError

class DoclingEngine(BaseOCREngine):
    """
    PHASE 3: DOCLING INTEGRATION
    Optimized for research papers, tabular data, formulas, and semantic trees.
    """
    async def extract(self, file_path: str, mime_type: str) -> OCREngineResult:
        logger.info(f"Running REAL DoclingEngine on {file_path}")
        converter = get_docling_converter()
        
        if converter == "MOCK":
            return OCREngineResult(engine_name="Docling", text="Mock Text", confidence=0.0)

        # Actual extraction
        doc_result = converter.convert(file_path)
        
        # Parse output semantic hierarchy
        full_text = doc_result.document.export_to_markdown()
        tables = []
        for table in doc_result.document.tables:
            tables.append({"type": "table", "markdown": table.export_to_markdown()})
            
        formulas = []
        # Docling captures formulas as math blocks
        
        return OCREngineResult(
            engine_name="Docling",
            text=full_text,
            confidence=0.92, # Docling is deterministic parsing, high confidence
            tables=tables,
            formulas=formulas
        )

class PaddleOCREngine(BaseOCREngine):
    """
    PHASE 2: PADDLEOCR INTEGRATION
    Optimized for handwritten notes, scattered text, rotated documents, and multi-lingual.
    """
    async def extract(self, file_path: str, mime_type: str) -> OCREngineResult:
        logger.info(f"Running REAL PaddleOCREngine on {file_path}")
        ocr = get_paddle_ocr()
        
        if ocr == "MOCK":
             return OCREngineResult(engine_name="PaddleOCR", text="Mock Text", confidence=0.0)

        # Actual extraction. C-3: PaddleOCR 3.x returns OCRResult dicts
        # (rec_texts/rec_scores/rec_polys) instead of the 2.x nested
        # [box, (text, conf)] lists; normalize both formats to
        # (box, text, conf) triples before the coordinate math below.
        if hasattr(ocr, "predict"):
            result = ocr.predict(file_path)
        else:
            result = ocr.ocr(file_path, cls=True)

        lines_norm = []  # [(box, text, conf)]
        for res in result or []:
            if res is None:
                continue
            texts = None
            if isinstance(res, dict) or hasattr(res, "get"):
                texts = res.get("rec_texts")
            if texts is not None:  # 3.x format
                scores = res.get("rec_scores") or [0.0] * len(texts)
                polys = res.get("rec_polys")
                if polys is None:
                    polys = res.get("dt_polys")
                for i, txt in enumerate(texts):
                    conf = float(scores[i]) if i < len(scores) else 0.0
                    if polys is not None and i < len(polys):
                        box = [[float(p[0]), float(p[1])] for p in polys[i]]
                    else:
                        box = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
                    lines_norm.append((box, txt, conf))
            else:  # 2.x format
                for line in res:
                    lines_norm.append((line[0], line[1][0], float(line[1][1])))

        full_text = ""
        bboxes = []
        total_confidence = 0.0
        word_count = 0

        # PHASE 2: COORDINATE NORMALIZATION
        # To make bounding boxes zoom-safe on the frontend, we must convert absolute pixel coords
        # to normalized percentages (0.0 to 1.0) based on the image's bounding box logic.
        # Note: We assume a standard page dimension for the PDF if not provided by Paddle
        # Since we don't have the original PDF dimensions directly from PaddleOCR.ocr,
        # we dynamically estimate page width/height from the max extents of the bounding boxes,
        # or fall back to an assumed A4 standard aspect ratio.
        max_x = 1; max_y = 1
        for box, _txt, _conf in lines_norm:
            for pt in box:
                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])

        # Add a 5% margin to max dimensions to avoid edge cutoff
        page_w = max_x * 1.05
        page_h = max_y * 1.05

        for box, txt, conf in lines_norm:
            # box: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            # Calculate bounding box (top-left width height)
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            min_x = min(x_coords)
            min_y = min(y_coords)
            w = max(x_coords) - min_x
            h = max(y_coords) - min_y

            # Normalize
            norm_x = min_x / page_w
            norm_y = min_y / page_h
            norm_w = w / page_w
            norm_h = h / page_h

            full_text += txt + "\n"
            total_confidence += conf
            word_count += 1
            bboxes.append({
                "text": txt,
                "bbox_norm": [norm_x, norm_y, norm_w, norm_h],
                "bbox_abs": box,
                "confidence": conf
            })

        avg_confidence = total_confidence / max(1, word_count)
        
        return OCREngineResult(
            engine_name="PaddleOCR",
            text=full_text,
            confidence=avg_confidence,
            bounding_boxes=bboxes
        )

class OCRValidationGateway:
    """
    PHASE 7: OCR VALIDATION GATEWAY
    Ensures minimum fidelity thresholds are met before persisting OCR output.
    """
    @staticmethod
    def validate(result: OCREngineResult, min_confidence: float = 0.80) -> bool:
        if result.confidence < min_confidence:
            logger.warning(f"OCR Validation Failed: Confidence {result.confidence} below threshold {min_confidence}")
            return False
        return True

class OCROrchestrator:
    """
    PHASE 1: OCR ROUTING LAYER
    Dynamically routes documents to the best-suited OCR engine based on heuristics or mime-types.
    """
    def __init__(self):
        self.engines = {
            "docling": DoclingEngine(),
            "paddle": PaddleOCREngine()
        }
        self.validator = OCRValidationGateway()

    async def extract_document(self, file_path: str, mime_type: str, hint: str = "auto") -> OCREngineResult:
        primary_engine_name = "docling"
        fallback_engine_name = "paddle"
        
        if "handwritten" in hint.lower() or mime_type in ["image/jpeg", "image/png"]:
            primary_engine_name = "paddle"
            fallback_engine_name = "docling"

        primary_engine = self.engines[primary_engine_name]
        try:
            result = await primary_engine.extract(file_path, mime_type)
            if self.validator.validate(result):
                return result
            else:
                logger.info(f"Primary engine {primary_engine_name} failed validation. Attempting fallback.")
        except Exception as e:
            logger.error(f"Primary engine {primary_engine_name} failed with error: {str(e)}")

        fallback_engine = self.engines[fallback_engine_name]
        logger.info(f"Routing to fallback engine: {fallback_engine_name}")
        fallback_result = await fallback_engine.extract(file_path, mime_type)
        
        if self.validator.validate(fallback_result, min_confidence=0.60):
            return fallback_result
            
        raise ValueError("All OCR engines failed to produce confident extraction.")

ocr_orchestrator = OCROrchestrator()
