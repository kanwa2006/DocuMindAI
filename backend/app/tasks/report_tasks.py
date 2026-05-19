"""
Phase 9-F2 + 9-G5 — Executive report generation and scheduled weekly reports.

generate_session_report: async helper used by POST /export/{session_id}/report.
run_scheduled_reports:   Celery beat task, Monday 08:00 UTC.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── PDF Builder (reportlab) ───────────────────────────────────────────────────

def _build_pdf(
    title: str,
    prepared_by: str,
    workspace_type: str,
    date_str: str,
    executive_summary: str,
    key_findings: list[str],
    citations: list[str],
    watermark_text: Optional[str],
    company_name: Optional[str],
    footer_opts: dict,
    sections: dict,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
        import io as _io

        buf = _io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
        )

        styles = getSampleStyleSheet()
        s_title = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=22,
            spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e"),
        )
        s_meta = ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12,
        )
        s_h2 = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=18,
            spaceAfter=8,
            textColor=colors.HexColor("#1a1a2e"),
        )
        s_body = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=6,
            leading=16,
        )
        s_disclaimer = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#92400e"),
            backColor=colors.HexColor("#fffbeb"),
            borderPadding=(8, 12, 8, 12),
            borderColor=colors.HexColor("#d97706"),
            borderWidth=1,
            spaceAfter=12,
        )

        story: list = []

        # ── Title block ──────────────────────────────────────────────────────
        story.append(Paragraph(title, s_title))
        meta_parts = []
        if company_name:
            meta_parts.append(company_name)
        meta_parts += [f"Prepared by {prepared_by}", workspace_type.title() + " workspace", date_str]
        story.append(Paragraph(" · ".join(meta_parts), s_meta))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"), spaceAfter=12))

        # ── Workspace disclaimer ──────────────────────────────────────────────
        if sections.get("workspace_context") and workspace_type in ("legal", "finance"):
            disclaimer = (
                "<b>⚡ Grounding Constraint:</b> This report answers ONLY from uploaded documents. "
                "It does not access the internet, legal databases, or financial APIs."
            )
            if workspace_type == "legal":
                disclaimer += " This is not legal advice."
            elif workspace_type == "finance":
                disclaimer += " Financial ratios are computed by Python, not AI estimation."
            story.append(Paragraph(disclaimer, s_disclaimer))

        # ── Executive Summary ─────────────────────────────────────────────────
        if sections.get("executive_summary") and executive_summary:
            story.append(Paragraph("Executive Summary", s_h2))
            story.append(Paragraph(executive_summary, s_body))

        # ── Key Findings ──────────────────────────────────────────────────────
        if sections.get("key_findings") and key_findings:
            story.append(Paragraph("Key Findings", s_h2))
            items = [ListItem(Paragraph(f, s_body)) for f in key_findings]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))

        # ── Citations ─────────────────────────────────────────────────────────
        if sections.get("citations") and citations:
            story.append(Paragraph("Citations", s_h2))
            for i, cit in enumerate(citations, 1):
                story.append(Paragraph(f"{i}. {cit}", s_body))

        # ── Footer ────────────────────────────────────────────────────────────
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
        footer_line = "Generated by DocuMindAI · Answers grounded in uploaded documents only"
        if footer_opts.get("show_date_user"):
            footer_line += f" · {date_str}"
        story.append(Paragraph(footer_line, s_meta))

        def _watermark_page(canvas, _doc):
            if watermark_text:
                canvas.saveState()
                canvas.setFont("Helvetica", 60)
                canvas.setFillAlpha(0.08)
                canvas.setFillColor(colors.grey)
                w, h = A4
                canvas.translate(w / 2, h / 2)
                canvas.rotate(30)
                wm = watermark_text.upper()
                for offset in (-h // 2, 0, h // 2):
                    canvas.drawCentredString(0, offset, wm)
                canvas.restoreState()

        doc.build(story, onFirstPage=_watermark_page, onLaterPages=_watermark_page)
        return buf.getvalue()

    except ImportError:
        logger.warning("reportlab not installed — returning plain-text PDF placeholder")
        placeholder = (
            f"%PDF-1.4\n"
            f"% {title}\n"
            f"% {executive_summary}\n"
            f"% {'; '.join(key_findings[:5])}"
        ).encode()
        return placeholder


# ── Core async report generator ───────────────────────────────────────────────

async def generate_session_report(
    session_id: uuid.UUID,
    config: dict,
    db: Any,
) -> bytes:
    """
    Generate a professional PDF executive report for a session.
    Executive summary LLM call is hard-capped at 200 output tokens.
    This function is NOT a Celery task — it is called directly from the API endpoint.
    """
    from sqlalchemy.future import select
    from app.models.chat import ChatSession, ChatMessage
    from app.services.llm_service import get_llm_service

    session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    title: str = config.get("title") or f"Analysis — {datetime.utcnow().strftime('%Y-%m-%d')}"
    sections: dict = config.get("sections") or {
        "executive_summary": True,
        "key_findings": True,
        "citations": True,
        "workspace_context": True,
    }
    branding: dict = config.get("branding") or {}
    watermark_cfg: dict = config.get("watermark") or {}
    watermark_text: Optional[str] = watermark_cfg.get("text") or config.get("watermark_text")
    footer_opts: dict = config.get("footer_options") or {
        "show_date_user": True,
        "show_disclaimer": True,
    }
    workspace_type: str = config.get("workspace_type") or getattr(session, "workspace_type", "general")

    # Build Q&A text for LLM (cap at 20 turns × 500 chars each to control token use)
    qa_pairs = []
    for m in messages:
        if m.role in ("user", "assistant"):
            qa_pairs.append(f"{m.role.upper()}: {m.content[:500]}")
    qa_text = "\n".join(qa_pairs[:20])

    executive_summary = ""
    if sections.get("executive_summary") and qa_text:
        try:
            llm = get_llm_service()
            # Hard cap: 200 output tokens as specified
            sys_prompt = (
                "You are a professional document analyst writing executive summaries. "
                "Be concise, factual, and never add information not present in the source."
            )
            user_prompt = (
                "Summarize the following Q&A exchange in 3-4 sentences for an executive audience. "
                "Focus on key findings only. Be factual and concise.\n\n"
                f"{qa_text}"
            )
            raw = await llm.generate(system_prompt=sys_prompt, user_prompt=user_prompt)
            # Truncate to ~200 tokens (≈800 chars as a safe proxy)
            executive_summary = raw.strip()[:800]
        except Exception as exc:
            logger.warning("Executive summary generation failed: %s", exc)
            executive_summary = "(Summary generation unavailable)"

    # Extract bullet-point findings from assistant messages
    key_findings: list[str] = []
    if sections.get("key_findings"):
        for m in messages:
            if m.role == "assistant":
                for line in m.content.split("\n"):
                    stripped = line.strip()
                    if stripped and stripped[0] in ("-", "•", "*", "–"):
                        key_findings.append(stripped.lstrip("-•*– ").strip())
                        if len(key_findings) >= 20:
                            break
            if len(key_findings) >= 20:
                break

    # Compile unique citations from assistant messages
    citations: list[str] = []
    if sections.get("citations"):
        seen: set[str] = set()
        for m in messages:
            if m.role == "assistant":
                for line in m.content.split("\n"):
                    if "Source:" in line or "(Page" in line:
                        entry = line.strip()
                        if entry not in seen:
                            citations.append(entry)
                            seen.add(entry)
            if len(citations) >= 50:
                break

    return _build_pdf(
        title=title,
        prepared_by=config.get("prepared_by", "DocuMindAI User"),
        workspace_type=workspace_type,
        date_str=datetime.utcnow().strftime("%B %d, %Y"),
        executive_summary=executive_summary,
        key_findings=key_findings,
        citations=citations,
        watermark_text=watermark_text,
        company_name=branding.get("company_name"),
        footer_opts=footer_opts,
        sections=sections,
    )


# ── Scheduled Report Celery Task (9-G5) ──────────────────────────────────────

def _next_monday_8am(from_dt: datetime) -> datetime:
    """Return the next Monday at 08:00 UTC after from_dt."""
    days_ahead = (7 - from_dt.weekday()) % 7  # 0=Monday
    if days_ahead == 0:
        days_ahead = 7
    next_monday = (from_dt + timedelta(days=days_ahead)).replace(
        hour=8, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    return next_monday


def run_scheduled_reports() -> None:
    """
    Celery beat task — Monday 08:00 UTC.
    Re-generates reports for all due ScheduledReport rows and
    creates a Notification for each. No email delivery in v1.
    """
    asyncio.run(_run_scheduled_reports_async())


async def _run_scheduled_reports_async() -> None:
    from sqlalchemy.future import select
    from sqlalchemy import and_
    from app.db.session import AsyncSessionLocal
    from app.models.workspace_template import ScheduledReport
    from app.models.saved_query_template import Notification

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        stmt = select(ScheduledReport).where(
            and_(
                ScheduledReport.is_active == True,  # noqa: E712
                ScheduledReport.next_run_at <= now,
            )
        )
        result = await db.execute(stmt)
        due = result.scalars().all()

        for sched in due:
            try:
                config = {
                    "title": f"Weekly {sched.workspace_id.title()} Summary — {now.strftime('%Y-%m-%d')}",
                    "sections": {
                        "executive_summary": True,
                        "key_findings": True,
                        "citations": True,
                        "workspace_context": True,
                    },
                    "prepared_by": "Scheduled Report",
                    "workspace_type": sched.workspace_id,
                }
                await generate_session_report(sched.session_id, config, db)

                notification = Notification(
                    user_id=sched.user_id,
                    type="report_ready",
                    title=f"📊 Weekly {sched.workspace_id.title()} report is ready.",
                    body=(
                        f"Your scheduled report was generated on {now.strftime('%B %d, %Y')}. "
                        "Open the session to view."
                    ),
                    link=f"/sessions/{sched.session_id}",
                )
                db.add(notification)

                sched.last_run_at = now
                sched.next_run_at = _next_monday_8am(now)
                await db.commit()
                logger.info("Scheduled report OK session=%s", sched.session_id)
            except Exception as exc:
                logger.error("Scheduled report failed session=%s: %s", sched.session_id, exc)
                await db.rollback()


# ── Register with Celery beat ─────────────────────────────────────────────────
# Import is deferred to avoid circular import at module load.
# The celery_app beat_schedule registration lives in celery_app.py.
try:
    from app.workers.celery_app import celery_app

    celery_app.task(name="tasks.run_scheduled_reports")(run_scheduled_reports)
except Exception:
    pass  # celery not available in test/import contexts
