import time
import re
from typing import List, Optional

STRICT_WITH_DOC = (
    "STRICT RULES - PDF IS UPLOADED:\n"
    "1. Answer ONLY from the document content provided below. Do NOT use outside knowledge.\n"
    "2. Give COMPLETE, DETAILED answers using relevant document content.\n"
    "3. CITE PAGE NUMBERS whenever possible (e.g., 'As stated on Page 3...' or '(Page 5)').\n"
    "   Each chunk below is labelled with its source and page — use that information.\n"
    "4. If a TABLE is present in the context, describe or reproduce its key data clearly.\n"
    "5. If information is NOT in the document, say exactly: 'Not found in the uploaded document.'\n"
    "6. Do not hallucinate or add outside knowledge.\n"
    "7. For summary/revision questions:\n"
    "   - Start with a short 2-3 line overview.\n"
    "   - Section-wise headings with concise bullet points.\n"
    "   - Include: key definition, architecture/flow (if present), features, and exam focus.\n"
    "   - End with 'Likely Viva/Exam Focus' as 4-6 bullets.\n"
    "8. Do not repeat identical content blocks.\n"
)

STRICT_NO_DOC = (
    "RULES - NO PDF UPLOADED:\n"
    "1. Answer from general knowledge helpfully.\n"
    "2. Clearly state that this is general AI knowledge, not from an uploaded document.\n"
)

class GeminiKeyRotator:
    def __init__(self, keys: list):
        self.keys = [k.strip() for k in keys if k and k.strip()]
        self.current_index = 0
        self.reset_time = {}

    def get_current_key(self) -> Optional[str]:
        if not self.keys:
            return None
        now = time.time()
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]
            if key in self.reset_time and now < self.reset_time[key]:
                self.current_index = (self.current_index + 1) % len(self.keys)
                continue
            return key
        return None

    def mark_failed(self, key: str, cooldown: int = 30):
        self.reset_time[key] = time.time() + cooldown
        self.current_index = (self.current_index + 1) % len(self.keys)

_rotator = None

def _get_rotator():
    global _rotator
    if _rotator is None:
        from backend.config import GEMINI_API_KEYS
        _rotator = GeminiKeyRotator(GEMINI_API_KEYS)
    return _rotator

def classify_query(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["summarize", "summary", "overview", "what is this document", "what is this about"]):
        return "summary"
    if any(w in q for w in ["predict", "exam", "important question", "study guide", "revision"]):
        return "predict"
    if any(w in q for w in ["difference between", "compare", "versus", "vs", "contrast"]):
        return "compare"
    if any(w in q for w in ["explain", "what is", "what are", "describe", "define"]):
        return "explain"
    return "general"

def choose_model(question: str, query_type: str, context: str, is_followup: bool) -> str:
    """
    Safe routing:
    - Default = gemini-1.5-flash
    - Use gemini-2.5-pro ONLY for truly heavy tasks
    """
    q = question.lower()
    context_len = len(context)

    pro_keywords = [
        "predict exam", "important questions", "exam questions",
        "compare", "difference between", "contrast",
        "analyze", "analysis", "derive", "critically analyze",
        "advantages and disadvantages", "evaluate"
    ]

    is_heavy_question = any(k in q for k in pro_keywords)
    is_large_context = context_len > 18000

    from backend.config import GEMINI_MODEL
    # Prefer configured model to avoid hardcoded unavailable/quota-heavy routes.
    selected = GEMINI_MODEL
    return selected

def build_prompt(
    question: str,
    context: str,
    has_docs: bool = True,
    query_type: str = "general",
    conversation_context: str = ""
) -> str:
    # Keep enough context for high-quality long-form summaries.
    if context and len(context) > 28000:
        context = context[:28000]
    rules = STRICT_WITH_DOC if has_docs else STRICT_NO_DOC
    intent_rules = ""
    if has_docs and query_type in ["summary", "predict"]:
        intent_rules = (
            "EXAM PREP MODE:\n"
            "- Cover all major topics present in the provided document context.\n"
            "- Use numbered sections and concise bullets.\n"
            "- Include definition, key points, architecture/flow, and exam focus.\n"
            "- Do not skip topics that appear in the provided context.\n"
            "- If a requested part is missing in context, explicitly state 'Not mentioned in the PDF content provided.'\n\n"
        )
    return (
        f"You are DocuMind AI.\n"
        f"{rules}\n\n"
        f"{intent_rules}"
        f"{conversation_context}\n"
        f"Document Content:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer clearly and helpfully:"
    )

def _expected_topics_from_context(context: str) -> List[str]:
    """Extract likely major topics from context for expansion checking.
    Generic approach: look for repeated heading-like patterns."""
    c = (context or "").lower()
    if not c:
        return []
    # Try to find section headings or repeated key terms
    # This is a best-effort heuristic; the LLM expansion handles the rest.
    topics = []
    # Look for numbered/titled sections in the context
    import re
    headings = re.findall(r'(?:^|\n)\s*(?:\d+[.)]\s*|#{1,3}\s*)([A-Z][A-Za-z\s&/-]{3,40})', context)
    for h in headings:
        h_clean = h.strip()
        if h_clean and h_clean not in topics and len(h_clean) > 3:
            topics.append(h_clean)
        if len(topics) >= 8:
            break
    return topics

def _needs_expansion(answer: str, query_type: str, expected_topics: List[str]) -> bool:
    if query_type not in ["summary", "predict"]:
        return False
    ans = (answer or "").lower()
    # Too short for a requested full exam-style summary.
    if len(answer or "") < 3200:
        return True
    # If many expected topics exist but several are missing in answer, expand.
    if expected_topics:
        missing = 0
        for t in expected_topics:
            t0 = t.lower().split("/")[0]
            if t0 not in ans:
                missing += 1
        if missing >= 2:
            return True
    return False

def _looks_truncated(answer: str) -> bool:
    a = (answer or "").strip()
    if not a:
        return True
    # Common abrupt endings from interrupted model output.
    bad_endings = (" is a", " are", " and", " with", " of", " to", ":", "-", "•")
    if a.endswith(bad_endings):
        return True
    # Missing sentence closure on a short response.
    if len(a) < 1800 and a[-1] not in ".!?":
        return True
    return False

def _strip_duplicate_lead(base: str, continuation: str) -> str:
    """Drop repeated leading text when a continuation echoes prior content."""
    b = (base or "").strip()
    c = (continuation or "").strip()
    if not b or not c:
        return c
    probe = b[-180:]
    idx = c.lower().find(probe.lower())
    if idx != -1:
        c = c[idx + len(probe):].lstrip()
    return c

def _build_doc_grounded_fallback(chunks: List[dict], question: str) -> str:
    texts = []
    for c in chunks:
        txt = (c.get("chunk") or c.get("text") or "").strip()
        if txt:
            texts.append(txt)
    if not texts:
        return (
            "AI generation is temporarily unavailable (provider quota/high demand), and no document content "
            "could be extracted for fallback. Please retry shortly."
        )

    def clean_line(line: str) -> str:
        line = re.sub(r"\s+", " ", line).strip(" -•\t")
        return line

    def candidate_lines(text: str):
        # Keep medium informative lines; remove very short/noisy OCR fragments.
        raw = re.split(r"[\n\r]+", text)
        out = []
        for ln in raw:
            ln = clean_line(ln)
            if 25 <= len(ln) <= 300:
                out.append(ln)
        return out

    # Extract unique informative lines from all chunks
    seen_points = set()
    all_points = []
    for txt in texts:
        for ln in candidate_lines(txt):
            k = ln.lower()
            if k not in seen_points:
                seen_points.add(k)
                all_points.append(ln)
            if len(all_points) >= 30:
                break
        if len(all_points) >= 30:
            break

    if not all_points:
        return (
            "AI generation is temporarily unavailable. The uploaded PDF was indexed "
            "but the answer service is under high load. Please retry in a few moments."
        )

    # Group into sections of 5-6 points
    sections = []
    idx = 1
    for i in range(0, len(all_points), 6):
        group = all_points[i:i+6]
        bullet_text = "\n".join([f"- {p}" for p in group])
        sections.append(f"{idx}. Key Points (Part {idx})\n{bullet_text}")
        idx += 1

    return (
        "AI generation is temporarily unavailable (provider quota/high demand). "
        "Using strict PDF-grounded fallback notes.\n\n"
        "Overview:\n"
        "Below are the key points extracted directly from your uploaded document.\n\n"
        + "\n\n".join(sections)
        + f"\n\nOriginal question: {question}"
        + "\n\nPlease retry your question in a moment for a full AI-generated answer."
    )

def call_gemini(prompt: str, model_name: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("Run: pip install google-genai")

    rotator = _get_rotator()
    if not rotator.keys:
        raise ValueError("No Gemini API keys found in .env")

    from backend.config import (
        GEMINI_CONTINUATION_ROUNDS,
        GEMINI_MAX_OUTPUT_TOKENS,
        GEMINI_TEMPERATURE,
        GEMINI_TOP_P,
    )

    max_attempts = min(len(rotator.keys), 6)

    for attempt in range(max_attempts):
        key = rotator.get_current_key()
        if not key:
            time.sleep(1)
            continue

        try:
            print(f"[Gemini] Model={model_name} | Attempt {attempt + 1}/{max_attempts} using key ...{key[-6:]}")
            client = genai.Client(api_key=key)

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    top_p=GEMINI_TOP_P,
                )
            )

            if response and getattr(response, "text", None):
                full_text = response.text.strip()
                rounds = max(0, GEMINI_CONTINUATION_ROUNDS)
                for _ in range(rounds):
                    if not _looks_truncated(full_text):
                        break
                    continuation_prompt = (
                        "Continue from exactly where the last answer stopped.\n"
                        "Do not repeat earlier sections.\n"
                        "Return only the remaining part.\n\n"
                        f"Previous answer:\n{full_text}\n\n"
                        "Continue now:"
                    )
                    cont_response = client.models.generate_content(
                        model=model_name,
                        contents=continuation_prompt,
                        config=types.GenerateContentConfig(
                            temperature=GEMINI_TEMPERATURE,
                            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                            top_p=GEMINI_TOP_P,
                        )
                    )
                    cont_text = (getattr(cont_response, "text", "") or "").strip()
                    if not cont_text:
                        break
                    cont_text = _strip_duplicate_lead(full_text, cont_text)
                    if not cont_text:
                        break
                    full_text = f"{full_text}\n\n{cont_text}".strip()
                return full_text

            raise Exception("Empty response from Gemini")

        except Exception as e:
            err = str(e).lower()
            print(f"[Gemini Error] {e}")

            if "429" in err or "quota" in err or "resource_exhausted" in err:
                rotator.mark_failed(key, 60)
                continue
            elif "503" in err or "unavailable" in err:
                rotator.mark_failed(key, 20)
                continue
            elif "403" in err or "invalid" in err or "api_key" in err:
                rotator.mark_failed(key, 3600)
                continue
            else:
                time.sleep(1)
                continue

    raise Exception(f"Gemini service unavailable for model {model_name}")

def answer_question(chunks: List[dict], question: str,
                    conversation_context: str = "", is_followup: bool = False) -> dict:

    has_docs = len(chunks) > 0

    if not chunks:
        from backend.config import GEMINI_MODEL
        model_name = GEMINI_MODEL
        prompt = build_prompt(
            question,
            "No document uploaded.",
            has_docs=False,
            query_type=classify_query(question),
            conversation_context=conversation_context
        )
        answer = call_gemini(prompt, model_name)
        return {
            "answer": answer,
            "sources": [],
            "model_used": model_name
        }

    context_parts = []
    sources = set()

    for c in chunks:
        chunk_text = c.get("chunk") or c.get("text", "")
        source = c.get("source", "unknown")
        page = c.get("page", None)
        if chunk_text:
            label = f"[From: {source}, Page {page}]" if page else f"[From: {source}]"
            context_parts.append(f"{label}\n{chunk_text}")
            sources.add(source)

    context = "\n\n---\n\n".join(context_parts)

    query_type = classify_query(question)
    primary_model = choose_model(question, query_type, context, is_followup)

    print(f"[Model Router] Selected model: {primary_model}")

    prompt = build_prompt(
        question,
        context,
        has_docs=True,
        query_type=query_type,
        conversation_context=conversation_context
    )

    try:
        answer = call_gemini(prompt, primary_model)
        expected_topics = _expected_topics_from_context(context)
        if _needs_expansion(answer, query_type, expected_topics):
            expand_prompt = (
                f"{prompt}\n\n"
                f"Your previous answer was too brief/incomplete. Expand it fully now.\n"
                f"Expected topics to cover if present: {', '.join(expected_topics) if expected_topics else 'all major topics in context'}.\n"
                "Requirements:\n"
                "- Provide complete topic-wise notes for exam preparation.\n"
                "- Include all major sections from the provided document context.\n"
                "- Add likely viva questions for each section.\n"
                "- Keep strict PDF grounding only.\n"
            )
            answer = call_gemini(expand_prompt, primary_model)
        # Hard guard: if still incomplete/truncated after expansion,
        # force deterministic PDF-grounded exam notes.
        if _needs_expansion(answer, query_type, expected_topics) or _looks_truncated(answer):
            answer = _build_doc_grounded_fallback(chunks, question)
            final_model = "document_fallback"
        else:
            final_model = primary_model
    except Exception as e:
        print(f"[Fallback Triggered] Primary model failed: {e}")
        from backend.config import GEMINI_MODEL
        fallback_candidates = []
        for m in [GEMINI_MODEL, "gemini-2.5-flash"]:
            if m and m != primary_model and m not in fallback_candidates:
                fallback_candidates.append(m)
        answer = None
        final_model = None
        for fallback_model in fallback_candidates:
            try:
                answer = call_gemini(prompt, fallback_model)
                final_model = fallback_model
                break
            except Exception as fallback_error:
                continue
        if answer is None or _looks_truncated(answer):
            answer = _build_doc_grounded_fallback(chunks, question)
            final_model = "document_fallback"

    return {
        "answer": answer,
        "sources": list(sources),
        "query_type": query_type,
        "model_used": final_model
    }