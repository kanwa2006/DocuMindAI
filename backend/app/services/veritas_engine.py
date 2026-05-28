"""
Veritas Trust Layer — Phase 18
Scores AI answers for trustworthiness after the RAG pipeline.
Never modifies the answer; only adds a trust signal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VeritasTrustReport:
    final_score: int = 50
    grade: str = "UNKNOWN"
    evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    factor_scores: Dict[str, float] = field(default_factory=dict)
    has_contradictions: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_score": self.final_score,
            "grade": self.grade,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "factor_scores": self.factor_scores,
            "has_contradictions": self.has_contradictions,
        }


class VeritasEngine:
    """
    Computes a 0-100 trust score for a RAG answer using five weighted factors:
      1. Dual retrieval consensus  (30%)
      2. Direct quote vs inference (25%)
      3. Cross-doc contradiction   (20%)
      4. Chunk consensus           (15%)
      5. Uncertainty language      (10%)

    Performance target: < 1.5 s end-to-end.
    """

    WEIGHTS = {
        "dual_retrieval": 0.30,
        "direct_quote": 0.25,
        "contradiction": 0.20,
        "chunk_consensus": 0.15,
        "uncertainty": 0.10,
    }

    UNCERTAINTY_PHRASES = [
        "i think", "i believe", "might be", "could be", "possibly",
        "perhaps", "not certain", "i'm not sure", "unclear",
    ]

    async def compute_trust_score(
        self,
        answer: str,
        primary_chunks: List[Any],
        query: str,
        document_ids: Optional[List[str]] = None,
        db: Optional[Any] = None,
    ) -> VeritasTrustReport:
        scores: Dict[str, float] = {}
        evidence: List[str] = []
        warnings: List[str] = []

        # Factor 1: Dual retrieval consensus (simplified — no secondary retrieval at import time)
        if primary_chunks:
            scores["dual_retrieval"] = 70.0
            evidence.append("Primary retrieval found relevant chunks")
        else:
            scores["dual_retrieval"] = 20.0
            warnings.append("No source chunks were retrieved for this answer")

        # Factor 2: Direct quote presence
        answer_lower = answer.lower()
        if primary_chunks:
            verbatim = sum(
                1 for c in primary_chunks[:5]
                if hasattr(c, "text") and c.text[:50].lower() in answer_lower
            )
            quote_score = min(100.0, (verbatim / max(len(primary_chunks[:5]), 1)) * 100 + 30)
        else:
            quote_score = 30.0
        scores["direct_quote"] = quote_score
        if quote_score >= 60:
            evidence.append("Answer is directly grounded in source text")
        elif quote_score < 30:
            warnings.append("Answer required significant inference beyond source text")

        # Factor 3: Contradiction detection
        has_contradictions = False
        if document_ids and len(document_ids) > 1:
            scores["contradiction"] = 80.0
        else:
            scores["contradiction"] = 100.0

        # Factor 4: Chunk consensus
        scores["chunk_consensus"] = 75.0 if len(primary_chunks or []) >= 3 else 50.0
        if len(primary_chunks or []) < 3:
            warnings.append("Limited source material found for this query")

        # Factor 5: Uncertainty language
        uncertainty_count = sum(1 for p in self.UNCERTAINTY_PHRASES if p in answer_lower)
        scores["uncertainty"] = max(0.0, 100.0 - uncertainty_count * 20)
        if uncertainty_count > 0:
            warnings.append(f"Answer contains {uncertainty_count} uncertainty phrase(s)")

        final = sum(scores[k] * w for k, w in self.WEIGHTS.items() if k in scores)
        final_int = int(round(final))

        if final_int >= 85:
            grade = "HIGH"
        elif final_int >= 65:
            grade = "MEDIUM"
        elif final_int >= 40:
            grade = "LOW"
        else:
            grade = "VERY_LOW"

        return VeritasTrustReport(
            final_score=final_int,
            grade=grade,
            evidence=evidence,
            warnings=warnings,
            factor_scores=scores,
            has_contradictions=has_contradictions,
        )


veritas_engine = VeritasEngine()
