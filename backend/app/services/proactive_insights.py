import json
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.proactive_insight import ProactiveInsight
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

WORKSPACE_INSIGHT_PROMPTS: dict = {
    "legal": (
        "You are a legal analysis AI. Analyze the following document chunks and identify proactive insights "
        "that a lawyer or client should know immediately. Focus on: penalty clauses, termination conditions, "
        "unusual or non-standard clauses, missing essential clauses, key dates and deadlines, and liability risks. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for anything that could cause financial loss or legal liability. "
        "Return ONLY the JSON array, no other text."
    ),
    "finance": (
        "You are a financial analysis AI. Analyze the following document chunks and identify proactive insights "
        "for a financial analyst or accountant. Focus on: key ratios, year-on-year changes greater than 20%, "
        "red flags or anomalies, tax compliance issues, unusual transactions, and liquidity concerns. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for material misstatements or compliance violations. "
        "Return ONLY the JSON array, no other text."
    ),
    "hr": (
        "You are an HR analysis AI. Analyze the following document chunks (resumes/job descriptions) and identify "
        "proactive insights for a recruiter. Focus on: exceptional candidates, disqualifying factors, skills gaps, "
        "red flags in work history, standout achievements, and JD-resume mismatches. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for disqualifying factors or exceptional top-fit candidates. "
        "Return ONLY the JSON array, no other text."
    ),
    "research": (
        "You are a research analysis AI. Analyze the following document chunks (research papers) and identify "
        "proactive insights for a researcher. Focus on: key claims and hypotheses, methodology limitations, "
        "key statistics and findings, contradictions with existing literature, research gaps, and citation quality. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for fundamental methodology flaws or extraordinary claims. "
        "Return ONLY the JSON array, no other text."
    ),
    "exam": (
        "You are an educational content analysis AI. Analyze the following document chunks (syllabus/textbook) "
        "and identify proactive insights for a teacher. Focus on: difficult concepts students often struggle with, "
        "high-priority exam topics, prerequisite knowledge required, common misconceptions, and assessment opportunities. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for prerequisite gaps or frequently failed exam topics. "
        "Return ONLY the JSON array, no other text."
    ),
    "study": (
        "You are a study assistant AI. Analyze the following document chunks and identify proactive insights "
        "for a student. Focus on: the top 5 most important concepts, key terms and definitions, "
        "likely exam questions, tricky or counter-intuitive points, and connections between topics. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for high-probability exam topics. "
        "Return ONLY the JSON array, no other text."
    ),
    "general": (
        "You are a document analysis AI. Analyze the following document chunks and identify proactive insights "
        "that the reader should know before asking questions. Focus on: the main purpose of the document, "
        "action items or next steps, critical facts or figures, items requiring urgent attention, "
        "and any surprising or non-obvious information. "
        "Return a JSON array of up to 8 objects. Each object must have exactly these keys: "
        "insight_type (string), severity (one of: critical, important, informational), "
        "finding (string, max 500 chars), page_reference (integer or null). "
        "severity=critical for urgent action items or critical facts. "
        "Return ONLY the JSON array, no other text."
    ),
}


@dataclass
class InsightItem:
    insight_type: str
    severity: str
    finding: str
    page_reference: Optional[int]


class ProactiveInsightsService:
    async def generate_insights(
        self,
        document_id: str,
        workspace: str,
        top_chunks: List[dict],
        session_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        db: Session = None,
    ) -> List[InsightItem]:
        prompt_template = WORKSPACE_INSIGHT_PROMPTS.get(workspace, WORKSPACE_INSIGHT_PROMPTS["general"])

        # Select top 10 most information-dense chunks (longest text = highest density)
        sorted_chunks = sorted(top_chunks, key=lambda c: len(c.get("text_content", "")), reverse=True)
        selected = sorted_chunks[:10]

        chunks_text = "\n\n".join(
            f"[Page {c.get('page_number', '?')}] {c.get('text_content', '')}"
            for c in selected
        )

        user_prompt = (
            f"Document chunks to analyze:\n\n{chunks_text}\n\n"
            "Generate proactive insights as a JSON array."
        )

        raw = await llm_service.provider.generate(system_prompt=prompt_template, user_prompt=user_prompt)

        items = self._parse_insights(raw)

        if db is not None:
            self._persist(items, document_id, workspace, session_id, owner_id, db)

        return items

    def _parse_insights(self, raw: str) -> List[InsightItem]:
        try:
            # Strip markdown fences if present
            text = raw.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(text)
            if not isinstance(data, list):
                return []

            items = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                severity = str(entry.get("severity", "informational")).lower()
                if severity not in ("critical", "important", "informational"):
                    severity = "informational"
                finding = str(entry.get("finding", ""))[:500]
                if not finding:
                    continue
                page_ref = entry.get("page_reference")
                if page_ref is not None:
                    try:
                        page_ref = int(page_ref)
                    except (ValueError, TypeError):
                        page_ref = None
                items.append(InsightItem(
                    insight_type=str(entry.get("insight_type", "general")),
                    severity=severity,
                    finding=finding,
                    page_reference=page_ref,
                ))
            return items[:8]
        except Exception as exc:
            logger.warning(f"[ProactiveInsights] Failed to parse LLM response: {exc}")
            return []

    def _persist(
        self,
        items: List[InsightItem],
        document_id: str,
        workspace: str,
        session_id: Optional[str],
        owner_id: Optional[str],
        db: Session,
    ) -> None:
        doc_uuid = uuid.UUID(str(document_id))
        sess_uuid = uuid.UUID(str(session_id)) if session_id else None

        for item in items:
            row = ProactiveInsight(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                session_id=sess_uuid,
                workspace=workspace,
                insight_type=item.insight_type,
                severity=item.severity,
                finding=item.finding,
                page_reference=item.page_reference,
                was_clicked=False,
            )
            db.add(row)

            if item.severity == "critical" and owner_id:
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(str(owner_id)),
                    type="insight",
                    title=f"Critical insight found ({workspace})",
                    body=item.finding[:200],
                    action_url=f"/dashboard?doc={document_id}",
                    is_read=False,
                )
                db.add(notif)

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"[ProactiveInsights] DB persist failed: {exc}")


proactive_insights_service = ProactiveInsightsService()
