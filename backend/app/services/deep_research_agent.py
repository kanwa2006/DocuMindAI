"""
Deep Research Agent — Phase 19
Hybrid RAG + web intelligence using Tavily for knowledge-gap filling.
Yields ResearchEvent objects so callers can stream progress to the UI.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchEvent:
    step: Any  # int or "final"
    status: str  # "running" | "done" | "skipped" | "complete" | "error"
    message: str = ""
    answer: str = ""
    doc_citations: List[Any] = field(default_factory=list)
    web_sources: List[Dict[str, Any]] = field(default_factory=list)
    doc_trust: Optional[Any] = None
    has_web_augmentation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "status": self.status,
            "message": self.message,
            "answer": self.answer,
            "doc_citations": self.doc_citations,
            "web_sources": self.web_sources,
            "doc_trust": self.doc_trust.to_dict() if self.doc_trust else None,
            "has_web_augmentation": self.has_web_augmentation,
        }


class DeepResearchAgent:
    """
    Performs a 4-step hybrid research pipeline:
      1. RAG over uploaded documents (with Veritas trust score)
      2. Identify knowledge gaps via LLM
      3. Agentic web search (Tavily) for gaps if trust score < 85
      4. Synthesise document + web findings into a structured answer

    Yields ResearchEvent at each step for SSE streaming.
    """

    def __init__(self) -> None:
        self._tavily_client: Optional[Any] = None

    def _get_tavily(self) -> Any:
        if self._tavily_client is None:
            try:
                from tavily import TavilyClient
                from app.core.config import settings
                self._tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            except Exception as exc:
                logger.warning("Tavily unavailable: %s", exc)
                return None
        return self._tavily_client

    async def research(
        self,
        query: str,
        document_ids: List[str],
        session_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> AsyncGenerator[ResearchEvent, None]:
        from app.services.llm_service import llm_service
        from app.services.veritas_engine import veritas_engine

        # Step 1: RAG from uploaded documents
        yield ResearchEvent(
            step=1, status="running",
            message="Analyzing your uploaded documents..."
        )
        try:
            from app.services.retrieval_service import retrieval_service
            doc_answer, doc_citations = await retrieval_service.query(query, document_ids)
            doc_trust = await veritas_engine.compute_trust_score(
                answer=doc_answer,
                primary_chunks=doc_citations,
                query=query,
                document_ids=document_ids,
                db=db,
            )
        except Exception as exc:
            logger.warning("RAG pipeline error in DeepResearch step 1: %s", exc)
            doc_answer = ""
            doc_citations = []
            from app.services.veritas_engine import VeritasTrustReport
            doc_trust = VeritasTrustReport(final_score=0, grade="UNKNOWN",
                                           warnings=["Document retrieval failed"])

        yield ResearchEvent(
            step=1, status="done",
            message=f"Found relevant content in {len(doc_citations)} passages"
        )

        # Step 2: Identify knowledge gaps
        yield ResearchEvent(
            step=2, status="running",
            message="Identifying what your documents don't cover..."
        )
        gaps: List[str] = []
        if doc_trust.final_score < 85 and doc_answer:
            gap_prompt = (
                f"User asked: {query}\n"
                f"Document answer: {doc_answer}\n"
                "Identify 2-3 specific aspects not answered clearly. "
                "Return ONLY a JSON array of search queries, max 3 items."
            )
            try:
                import json
                raw = await llm_service.generate(
                    "You are a research gap analyst. Output only valid JSON arrays.",
                    gap_prompt,
                )
                raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                gaps = json.loads(raw)[:3]
            except Exception as exc:
                logger.warning("Gap identification failed: %s", exc)

        if not gaps:
            yield ResearchEvent(
                step=2, status="skipped",
                message="Documents provided complete coverage — skipping web search"
            )
        else:
            yield ResearchEvent(
                step=2, status="done",
                message=f"Identified {len(gaps)} knowledge gap(s)"
            )

        # Step 3: Web search for gaps
        web_results: List[Dict[str, Any]] = []
        if gaps:
            yield ResearchEvent(step=3, status="running", message="Searching current sources...")
            tavily = self._get_tavily()
            if tavily:
                for search_query in gaps:
                    try:
                        results = tavily.search(
                            search_query,
                            search_depth="basic",
                            max_results=3,
                            include_domains=[
                                "gov.in", "rbi.org.in", "sebi.gov.in",
                                "economictimes.com", "livemint.com",
                                "barandbench.com", "livelaw.in",
                                "pubmed.ncbi.nlm.nih.gov", "arxiv.org",
                            ],
                        )
                        web_results.extend(results.get("results", []))
                    except Exception as exc:
                        logger.warning("Tavily search failed for '%s': %s", search_query, exc)
            yield ResearchEvent(
                step=3, status="done",
                message=f"Found {len(web_results)} current source(s)"
            )

        # Step 4: Synthesise
        yield ResearchEvent(step=4, status="running", message="Synthesizing findings...")
        web_text = "\n".join(
            f"- {r.get('title','')} ({r.get('url','')}): {r.get('content','')[:300]}"
            for r in web_results
        )
        synthesis_prompt = (
            f"User question: {query}\n\n"
            f"FROM UPLOADED DOCUMENTS (Trust Score: {doc_trust.final_score}/100):\n{doc_answer}\n\n"
            f"FROM CURRENT WEB SOURCES:\n{web_text or 'No web sources found.'}\n\n"
            "Create a structured synthesis:\n"
            "1. ANSWER FROM YOUR DOCUMENTS (with page citations)\n"
            "2. CURRENT CONTEXT (what web sources add, with URLs)\n"
            "3. KEY INSIGHTS (2-3 bullets)\n"
            "4. GAPS & LIMITATIONS\n"
            "Mark web content with [Web Source] tag."
        )
        try:
            final_answer = await llm_service.generate(
                "You are a research synthesis expert.", synthesis_prompt
            )
        except Exception as exc:
            logger.warning("Synthesis failed: %s", exc)
            final_answer = doc_answer or "Research synthesis could not be completed."

        yield ResearchEvent(step=4, status="done", message="Research complete")
        yield ResearchEvent(
            step="final",
            status="complete",
            answer=final_answer,
            doc_citations=doc_citations,
            web_sources=web_results,
            doc_trust=doc_trust,
            has_web_augmentation=bool(web_results),
        )


deep_research_agent = DeepResearchAgent()
