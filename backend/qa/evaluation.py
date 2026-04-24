"""
Basic RAG evaluation metrics — no RAGAS package required.

Computes lightweight approximations of:
- Context Relevance: how much of the retrieved context matches the question
- Answer Faithfulness: how much the answer is grounded in the context
- Answer Completeness: length and structure quality score

These are stored per-session and returned via GET /qa/evaluate/{session_id}.
For a full RAGAS integration, replace these with:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
"""
import re
import math


def _tokenize(text: str) -> set:
    return set(re.findall(r'\b\w+\b', (text or "").lower()))


def context_relevance(question: str, chunks: list) -> float:
    """
    Measures how relevant the retrieved chunks are to the question.
    Method: token overlap (Jaccard similarity) between question and context.
    Score: 0.0 (irrelevant) → 1.0 (highly relevant)
    """
    if not chunks:
        return 0.0
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 0.0
    scores = []
    for chunk in chunks:
        c_tokens = _tokenize(chunk.get("chunk", ""))
        if not c_tokens:
            continue
        intersection = len(q_tokens & c_tokens)
        union = len(q_tokens | c_tokens)
        scores.append(intersection / union if union > 0 else 0.0)
    return round(sum(scores) / len(scores), 3) if scores else 0.0


def answer_faithfulness(answer: str, chunks: list) -> float:
    """
    Measures how grounded the answer is in the retrieved context.
    Method: what fraction of answer bigrams appear in the context.
    Score: 0.0 (hallucinated) → 1.0 (fully grounded)
    """
    if not answer or not chunks:
        return 0.0
    context = " ".join(c.get("chunk", "") for c in chunks).lower()
    words = re.findall(r'\b\w+\b', answer.lower())
    if len(words) < 2:
        return 0.0
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    if not bigrams:
        return 0.0
    grounded = sum(1 for bg in bigrams if bg in context)
    return round(grounded / len(bigrams), 3)


def answer_completeness(answer: str, question: str) -> float:
    """
    Rough heuristic for answer completeness:
    - Longer answers get higher scores (up to a cap)
    - Answers with structure (bullets, headings) score higher
    - Penalty for very short answers
    Score: 0.0 → 1.0
    """
    if not answer:
        return 0.0
    length_score = min(len(answer) / 800, 1.0)  # cap at 800 chars
    structure_bonus = 0.0
    if re.search(r'^\s*[-•*]\s', answer, re.MULTILINE):
        structure_bonus += 0.15
    if re.search(r'^#{1,3}\s', answer, re.MULTILINE):
        structure_bonus += 0.1
    if re.search(r'page\s+\d+', answer, re.IGNORECASE):
        structure_bonus += 0.1  # bonus for page citations
    return round(min(length_score + structure_bonus, 1.0), 3)


def evaluate_qa_pair(question: str, answer: str, chunks: list) -> dict:
    """
    Run all three metrics on a single Q&A pair.
    Returns a dict with scores and an overall quality grade.
    """
    cr  = context_relevance(question, chunks)
    af  = answer_faithfulness(answer, chunks)
    ac  = answer_completeness(answer, question)
    overall = round((cr * 0.35 + af * 0.45 + ac * 0.20), 3)

    if overall >= 0.75:
        grade = "Excellent"
    elif overall >= 0.55:
        grade = "Good"
    elif overall >= 0.35:
        grade = "Fair"
    else:
        grade = "Poor"

    return {
        "context_relevance":    cr,
        "answer_faithfulness":  af,
        "answer_completeness":  ac,
        "overall_score":        overall,
        "grade":                grade,
        "note": (
            "Scores are lightweight heuristic approximations. "
            "For full RAGAS evaluation, integrate the ragas Python package "
            "with a labeled evaluation dataset."
        )
    }
