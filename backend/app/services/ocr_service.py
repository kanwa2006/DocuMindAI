import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class OCRService:
    @staticmethod
    def is_text_native(page: fitz.Page) -> bool:
        """
        Heuristic to detect if a page is text-native vs scanned.
        Returns False if there is very little text (likely an image-only scan).
        """
        text = page.get_text("text")
        return len(text.strip()) > 50

    @staticmethod
    def extract_layout_metadata(page: fitz.Page) -> Dict[str, Any]:
        """
        Extracts block-level metadata, crucial for semantic chunking later.
        """
        blocks = page.get_text("dict").get("blocks", [])
        text_blocks = [b for b in blocks if b.get("type") == 0]
        
        return {
            "blocks_count": len(text_blocks),
            "width": page.rect.width,
            "height": page.rect.height
        }

    @staticmethod
    def extract_document_stream(file_path: str):
        """
        Extracts document pages using layout-aware mechanisms, yielding page by page to save memory.
        """
        logger.info(f"[Tracing] Starting PyMuPDF streaming extraction for {file_path}")
        
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                is_native = OCRService.is_text_native(page)
                
                if not is_native:
                    logger.warning(f"[Tracing] Page {page_num+1} appears scanned. Using fallback.")
                    # Fallback architecture hook (Tesseract/EasyOCR would be injected here)
                    extracted_text = page.get_text("text") # Fallback to raw text for now
                    layout_meta = {"is_native": False, "requires_fallback": True}
                else:
                    # Layout-aware extraction preserving reading order
                    blocks = page.get_text("blocks")
                    # PyMuPDF blocks format: (x0, y0, x1, y1, "text", block_no, block_type)
                    # Sort roughly top-to-bottom, left-to-right
                    sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
                    
                    # Extract only text blocks (type == 0)
                    clean_text = "\n\n".join([b[4].strip() for b in sorted_blocks if b[6] == 0])
                    
                    layout_meta = OCRService.extract_layout_metadata(page)
                    layout_meta["is_native"] = True
                    extracted_text = clean_text

                yield {
                    "page_number": page_num + 1,  # 1-indexed for citation systems
                    "extracted_text": extracted_text,
                    "layout_metadata": layout_meta
                }
                
            doc.close()
            logger.info(f"[Tracing] Completed streaming extraction.")
            
        except Exception as e:
            logger.error(f"[Tracing] Extraction failed for {file_path}: {str(e)}")
            raise e
