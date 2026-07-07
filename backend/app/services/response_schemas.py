"""
Response structure schemas injected into system prompts.

These are plain-language instructions appended to the workspace system prompt in
query.py via ``get_response_schema(workspace_type)``. They do NOT change WHAT the
model answers from the grounded context — only HOW the answer is structured.

KEYS ARE THE CANONICAL WORKSPACE SLUGS used everywhere else in the app
(``config.WORKSPACE_RETRIEVAL_CONFIG`` and the frontend routes):

    general, hr, legal, finance, research, study, exam

Prior to this revision the dict was keyed ``student``/``teacher`` instead of
``study``/``exam``. Because ``get_response_schema`` is only ever called with the
canonical slug, the Study and Exam workspaces silently fell back to the GENERAL
schema and never received their structured-output instructions. ``_ALIASES``
now maps the legacy names onto the canonical slugs so any older caller keeps
working, and the keys themselves are canonical.
"""

# ---------------------------------------------------------------------------
# Shared completeness rule.
#
# Appended to the "analysis" workspaces. It reconciles the concise-by-default
# behaviour (good for pointed questions) with the product mandate that
# "summarize / give notes / explain all topics" requests must be COMPLETE — the
# model must never silently drop a topic the user asked about to hit a length
# target.
# ---------------------------------------------------------------------------
_COMPLETENESS_CLAUSE = """
COMPLETENESS RULE (overrides any brevity guidance above):
- Simple, pointed question → answer directly and concisely; do not pad.
- Request to summarize, give notes, explain all/every topic, or produce a
  detailed/comprehensive write-up → prioritise COMPLETENESS over shortness:
  cover every topic and sub-topic present in the evidence, preserve the source's
  conceptual order, and keep important formulas, definitions and examples. Do not
  truncate to hit a length target; continue until every in-scope topic is covered.
- Only assert facts supported by the provided context/evidence. If something is
  not in the evidence, say so explicitly rather than inventing it.
"""


_GENERAL = """
RESPONSE FORMAT RULES (follow exactly):
1. Open with a 1-2 sentence direct answer to the question.
2. For anything with 3+ distinct points, use ### sub-headers; use "- " bullets
   for enumerations of 3+ items.
3. **Bold** key terms, figures, names and dates.
4. Attribute non-trivial claims to their source inline: (filename, p.N).
5. Simple question → 2-4 sentences is enough.
6. Request to summarise / explain a document / give notes → switch to the
   structured long-form layout and cover ALL topics (see COMPLETENESS RULE):
   ## Overview · ## Main Topics · ## Key Details · ## Examples (if any) ·
   ## Key Takeaways.
"""


_HR = """
RESPONSE FORMAT RULES (follow exactly):
1. Multiple candidates → lead with a ranking table:
   | Rank | Candidate | Match /100 | Top Skills | Experience | Verdict |
   then a one-line "Why this ranking:" explaining the ordering.
2. Single candidate → a scorecard with fixed sections:
   **Match Score:** N/100 (state briefly how it was derived)
   **JD Alignment:** which JD requirements are met / partially met / missing
   **Strengths:** bullets, each tied to specific resume evidence
   **Gaps / Risks:** bullets, each tied to specific resume evidence
   **Recommendation:** Shortlist / Review / Reject + one-line rationale
3. Cite the resume section every finding comes from
   (e.g. "Experience → Acme Corp, 2021-23").
4. Comparisons → side-by-side table, one column per candidate.
5. Never surface candidate PII (phone, email, address) in the response.
"""


_LEGAL = """
RESPONSE FORMAT RULES (follow exactly):
1. Open with: "Overall risk: [Low / Medium / High / Critical]" + a one-line reason.
2. Clause-by-clause analysis, one block per clause:
   **Clause:** [type / heading]   **Risk:** [Low/Medium/High/Critical]   **Confidence:** [High/Medium/Low]
   **Says:** what the clause states, in plain English
   **Concern:** why it is risky (omit if none)
   **Action:** what to do
   **Source:** filename, page N — quote the exact operative wording.
3. Add an **Obligations & Deadlines** section: bullet every duty, the responsible
   party, and any date / notice period found (e.g. "Tenant: 60 days' written notice — p.4").
4. Quote operative legal wording verbatim; never paraphrase it.
5. Comparing documents or clauses → use a | clause | doc A | doc B | table.
6. End with: "⚠ Verify all findings with a qualified legal professional."
"""


_FINANCE = """
RESPONSE FORMAT RULES (follow exactly):
1. Money in Indian format (₹X,XX,XXX or ₹X crore / ₹X lakh).
2. Extracted figures → table: | Line Item | Value | Page |. Mark any value you had
   to derive (not read directly) with [Computed]; otherwise treat figures as extracted.
3. Ratios → show the formula, the inputs, then the result:
   **Current Ratio** = Current Assets / Current Liabilities = ₹X / ₹Y = **2.4x**
4. Year-on-year → a table with years as columns, plus ↑ / ↓ / → per metric and a
   one-line read of the trend.
5. Call out anomalies in an **Anomalies / Flags** section (unusual swings, missing
   periods, figures that don't reconcile) with the page reference.
6. End with: "⚠ Verify all figures against the source documents."
"""


_RESEARCH = """
RESPONSE FORMAT RULES (follow exactly):
1. State the basis up front: "Based on analysis of N paper(s):".
2. Per-paper synthesis → ### [Author, Year] (or paper title) headers.
3. Label every finding's evidence strength: [Strong] / [Moderate] / [Limited].
4. **Methodology:** extract design, sample / data, and method for each paper where available.
5. **Contradictions:** show both sides — "Paper A finds X; contradicting this, Paper B finds Y."
6. **Gaps:** numbered list, each prefixed **Gap:** — what remains unstudied.
7. Inline citations as (Author, Year, p.N). For a single-paper summary use
   Abstract / Methods / Findings / Limitations sections.
"""


_STUDY = """
RESPONSE FORMAT RULES (follow exactly):
1. Notes requests → topic-wise structure: ## <Topic> then ### <Sub-topic>, covering
   EVERY topic in the material (see COMPLETENESS RULE — do not skip topics). Under
   each: key points as bullets, **bold** terms, and any formula / definition on its
   own line.
2. **Flashcards** section grouped by topic when notes / revision is requested
   (5-10 per topic): "- Q: … / A: …".
3. **Quick Quiz** section — MCQs with (A) (B) (C) (D), exactly one correct. Do NOT
   reveal answers until the user asks.
4. Explanations → ELI5 for a smart 16-year-old; end each with "**In one line:** …".
5. **Revision Checkpoints** — a short checklist of "you should now be able to …".
6. Preserve the source's conceptual order; cite page numbers for specific facts.
"""


_EXAM = """
RESPONSE FORMAT RULES (follow exactly):
1. Generate the paper as structured sections (Section A / B / C) separated by ---
   dividers, with a header line stating total marks and duration.
2. Number every question (1., 2., 3.). MCQs show options (A) (B) (C) (D).
3. Show mark allocation after each question: [X marks].
4. Tag each question with its Bloom level (Remember / Understand / Apply / Analyse /
   Evaluate / Create) and keep a sensible spread across levels.
5. Produce a separate **Answer Key** section: "Q1: (B) | Q2: model answer / page ref | …".
6. Keep formatting clean and export-friendly (no stray markup) so it converts to
   DOCX intact.
"""


RESPONSE_SCHEMAS = {
    "general":  _GENERAL + _COMPLETENESS_CLAUSE,
    "hr":       _HR + _COMPLETENESS_CLAUSE,
    "legal":    _LEGAL + _COMPLETENESS_CLAUSE,
    "finance":  _FINANCE + _COMPLETENESS_CLAUSE,
    "research": _RESEARCH + _COMPLETENESS_CLAUSE,
    "study":    _STUDY + _COMPLETENESS_CLAUSE,
    "exam":     _EXAM,
}

# Legacy → canonical slug aliases (back-compat for any older caller).
_ALIASES = {
    "student": "study",
    "teacher": "exam",
}


def get_response_schema(workspace: str) -> str:
    """Return the structured-output instruction block for a workspace slug.

    Falls back to the GENERAL schema for unknown slugs. Legacy names
    (``student``/``teacher``) are resolved to their canonical slugs.
    """
    key = (workspace or "general").lower().strip()
    key = _ALIASES.get(key, key)
    return RESPONSE_SCHEMAS.get(key, RESPONSE_SCHEMAS["general"])
