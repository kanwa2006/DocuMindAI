"""
Response structure schemas injected into system prompts.
These are plain-language instructions that enforce consistent output.
They do NOT change what the AI answers — only HOW it structures the answer.
"""

RESPONSE_SCHEMAS = {

    "general": """
RESPONSE FORMAT RULES (follow exactly):
1. Start with a 1-2 sentence direct answer.
2. Use ### headers for each major point (if 3+ points exist).
3. Use bullet lists (- item) for enumerations of 3+ items.
4. Use **bold** for key terms, numbers, and dates.
5. End with a 1-sentence summary if response > 200 words.
6. Maximum response length: match the complexity of the question.
   Simple Q → 2-4 sentences. Complex Q → up to 500 words.
""",

    "legal": """
RESPONSE FORMAT RULES (follow exactly):
1. Start with a Risk Summary sentence: "Overall risk: [Low/Medium/High/Critical]"
2. For clause analysis: use this exact structure per clause:
   **Clause Type:** [name]
   **Risk Level:** [Low / Medium / High / Critical]
   **Finding:** [what the clause says, in plain English]
   **Concern:** [why this is risky, if applicable]
   **Recommendation:** [what to do]
   **Source:** [filename, page N]
3. For list of issues: numbered list with **bold** issue name.
4. Never paraphrase legal language — quote the exact clause text when relevant.
5. Always end with: "⚠ Verify all findings with a qualified legal professional."
6. Use tables (| col | col |) when comparing multiple clauses or documents.
""",

    "finance": """
RESPONSE FORMAT RULES (follow exactly):
1. All monetary values: use Indian format (₹X,XX,XXX or ₹X crore/lakh).
2. All ratios: show formula, then value. Example:
   **Current Ratio** = Current Assets / Current Liabilities = ₹X,XXX / ₹X,XXX = **2.4x**
3. For extraction: use a table with columns: | Line Item | Value | Page |
4. For comparisons: use a table with years as columns.
5. Trend indicators: use ↑ (improving) ↓ (declining) → (stable) per metric.
6. Never compute ratios yourself — state extracted values only if Python calculation
   is unavailable for this query. Mark computed values with [Computed].
7. End every financial analysis with: "⚠ Verify all figures with source documents."
8. For multi-value responses: use numbered sections with ### headers.
""",

    "teacher": """
RESPONSE FORMAT RULES (follow exactly):
1. For question generation: number all questions (1., 2., 3.)
2. MCQs: show question, then options labeled (A) (B) (C) (D)
3. Short answer questions: show [X marks] after each question
4. Long answer questions: show [X marks] and hint in italics
5. Use --- dividers between sections (A, B, C)
6. Answer key format: Q1: (B) | Q2: See page 12 | Q3: [sample answer]
7. For explanation responses: use ### headers for each concept
8. Use > blockquote for direct textbook quotes with page reference
""",

    "hr": """
RESPONSE FORMAT RULES (follow exactly):
1. Candidate rankings: use table format:
   | Rank | Name | Score | Top Skills | Experience |
2. Individual analysis: use fixed sections:
   **Match Score:** X/100
   **Strengths:** bullet list
   **Gaps:** bullet list
   **Recommendation:** [Shortlist / Review / Reject]
3. Comparison: use side-by-side table format
4. Never include candidate PII (phone/email) in responses
5. Always cite which resume section the finding comes from
""",

    "student": """
RESPONSE FORMAT RULES (follow exactly):
1. For explanations: use the ELI5 approach — explain like teaching a smart 16-year-old
2. Always end explanations with: **In one line:** [summary in 10-15 words]
3. For formulas: display on their own line with = alignment
4. For step-by-step solutions: number every step
5. For concept comparisons: use | Concept A | Concept B | comparison table
6. Quiz questions: always show (A) (B) (C) (D) with exactly one correct answer
7. Do NOT give the quiz answer until asked
8. Use emojis sparingly for memory hooks: 🧠 for key concepts, 📌 for important facts
""",

    "research": """
RESPONSE FORMAT RULES (follow exactly):
1. For synthesis: use ### Paper title or [Author, Year] headers per paper
2. Evidence strength: label each finding: [Strong evidence] / [Moderate] / [Limited]
3. For gaps: numbered list with **Gap:** prefix
4. For conflicts: show both sides — "Paper A finds X. Contradicting this, Paper B finds Y."
5. Citations format: (Author, Year, p.X) inline
6. For summaries: use Abstract / Methods / Findings / Limitations sections
7. Always state the number of papers reviewed: "Based on analysis of N papers:"
"""
}


def get_response_schema(workspace: str) -> str:
    return RESPONSE_SCHEMAS.get(workspace, RESPONSE_SCHEMAS["general"])
