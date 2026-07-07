import logging
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class ChunkingService:
    @staticmethod
    def chunk_page_text(extracted_text: str, page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Semantic chunker that respects layout block boundaries (\n\n).
        It merges blocks until MAX_CHUNK_LENGTH is reached, ensuring it never 
        splits a table or paragraph indiscriminately down the middle.
        """
        chunks = []
        # \n\n represents explicit PyMuPDF block boundaries from our OCR pipeline
        layout_blocks = [block.strip() for block in extracted_text.split("\n\n") if block.strip()]
        
        current_chunk = []
        current_length = 0
        
        for block in layout_blocks:
            block_len = len(block)
            
            # If a single block (e.g., massive table) exceeds MAX_CHUNK_LENGTH, we keep it whole
            # to preserve table/semantic integrity.
            if current_length + block_len > settings.CHUNK_SIZE and current_chunk:
                chunks.append({
                    "text_content": "\n\n".join(current_chunk),
                    "chunk_metadata": {"source": "layout_merge", "block_count": len(current_chunk)}
                })
                # Overlap strategy: take the last block of the previous chunk if it's small enough
                last_block = current_chunk[-1] if len(current_chunk[-1]) < settings.CHUNK_OVERLAP else ""
                current_chunk = [last_block, block] if last_block else [block]
                current_length = len("\n\n".join(current_chunk))
            else:
                current_chunk.append(block)
                current_length += block_len
                
        # Append remainder
        if current_chunk:
            chunks.append({
                "text_content": "\n\n".join(current_chunk),
                "chunk_metadata": {"source": "layout_merge", "is_tail": True, "block_count": len(current_chunk)}
            })
            
        return chunks
