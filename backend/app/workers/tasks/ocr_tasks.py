"""GPU-queue OCR task — currently a declared-but-unimplemented capability.

**This task is not the OCR pipeline.** The real, verified path is
`document_tasks.process_document`, which downloads via `storage_service` using
the document's actual `storage_path` and routes through `ocr_orchestrator`
(PaddleOCR/Docling). That path is confirmed working end-to-end: image-only PDF →
grounded answer with a page citation.

This module exists to reserve `ocr_gpu_queue` for a dedicated GPU worker (see
`celery_app.task_routes`). It has never been dispatched — zero call sites.

It previously *looked* implemented while being incapable of working:

- the file path was fabricated — `f"/tmp/docs/{doc.id}.pdf"`, annotated "Pass a
  mock file path and mime type for prototype" — so it never opened the user's
  document at all;
- the persistence step was commented out, targeting `doc.extracted_text` and
  `doc.ocr_metadata`, **neither of which exists on the Document model**. Even
  uncommented it would have raised;
- it then called `db.commit()` on those no-op changes and logged
  "OCR Extraction successful", so a dispatch would have reported success while
  discarding every result.

That is precisely the silent-degradation pattern CLAUDE.md forbids: a feature
that reports success and produces nothing. Rather than leave a plausible-looking
stub, or duplicate the working pipeline just to make this reachable, the task now
fails loudly and says where the real implementation lives. Wiring stays intact so
the three-way rule holds and a future GPU worker can take the queue over.

P0-7 is fixed here too — the module no longer imports the async session — so the
worker-session guard protects it if it is ever implemented.
"""
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class OcrGpuTaskNotImplemented(NotImplementedError):
    """Raised because GPU-queue OCR is reserved, not built.

    Deliberately loud. The previous behaviour — log success, persist nothing —
    is the failure mode this project treats as unacceptable.
    """


@celery_app.task(name="app.workers.tasks.ocr_tasks.extract_document_ocr", bind=True)
def extract_document_ocr(self, document_id: str):
    """Reserved for a dedicated GPU OCR worker. Not implemented.

    Does NOT retry: retrying an unimplemented capability only burns the queue.
    If you are here because you dispatched this, use
    `document_tasks.process_document` instead — it is the real OCR path.
    """
    uuid.UUID(document_id)  # validate the argument shape before refusing
    logger.error(
        "extract_document_ocr was dispatched for %s but GPU-queue OCR is not "
        "implemented. The working OCR path is document_tasks.process_document.",
        document_id,
    )
    raise OcrGpuTaskNotImplemented(
        "GPU-queue OCR is reserved but unimplemented. Use "
        "document_tasks.process_document, which downloads via storage_service "
        "and routes through ocr_orchestrator."
    )
