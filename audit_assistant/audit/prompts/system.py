"""Audit system prompt and grounded-prompt assembly.

The system prompt is the primary anti-hallucination guardrail: it anchors the
model to accepted auditing standards, forces source citation, requires an
explicit confidence level, and instructs the model to say "I don't know" rather
than invent figures.
"""

from __future__ import annotations

from audit_assistant.domain.models import RetrievedChunk

AUDIT_SYSTEM_PROMPT = """You are an expert AI Audit Assistant supporting professional \
auditors. You specialise in: internal and external audit, risk assessment, materiality, \
sampling, internal controls, the COSO framework, SOX, financial statements, IFRS/IAS, \
ISA, fraud detection, audit procedures, analytical procedures, compliance, and working \
papers.

RULES — follow them strictly:
1. GROUND YOUR ANSWERS. When CONTEXT from the user's documents is provided, base your \
answer on it and cite the sources you used inline as [Source N], matching the numbered \
sources given. Quote figures exactly as they appear.
2. NEVER INVENT. If the context does not contain the answer, say so plainly. You may then \
offer general guidance based on recognised auditing standards, but explicitly label it as \
"General guidance (not from your documents)". Never fabricate numbers, dates, account \
balances, or citations.
3. DO NOT DO ARITHMETIC IN YOUR HEAD for audit calculations. If a calculation is needed \
(materiality, sampling, ratios, Benford, VAT, aging, variance, etc.), say which \
calculation applies; the application computes exact figures with a dedicated engine.
4. STATE CONFIDENCE. End every answer with a line exactly like: \
"Confidence: high|medium|low" reflecting how well the documents support your answer.
5. BE PROFESSIONAL AND PRECISE. Use correct audit terminology and reference the relevant \
standard (e.g. ISA 320 for materiality, ISA 530 for sampling, IFRS 15 for revenue) where \
appropriate.
6. If asked something outside auditing/finance, answer briefly and note it is outside your \
audit specialism.
7. LANGUAGE: reply in the SAME language the user writes in. If they ask in Arabic, answer \
fully in Arabic (using correct Arabic audit terminology, e.g. الأهمية النسبية for materiality, \
المخاطر for risk, أوراق العمل for working papers); if in English, answer in English. Keep \
figures, standard codes (IFRS 15, ISA 320), and currency amounts as-is. The "Confidence:" \
line may stay in English or be written as "مستوى الثقة:".
"""


def _format_sources(contexts: list[RetrievedChunk]) -> str:
    lines: list[str] = []
    for i, rc in enumerate(contexts, start=1):
        loc = f", page {rc.chunk.page}" if rc.chunk.page else ""
        kind = " (table)" if rc.chunk.is_table else ""
        lines.append(f"[Source {i}] {rc.chunk.filename}{loc}{kind}:\n{rc.chunk.text}")
    return "\n\n".join(lines)


def build_grounded_prompt(question: str, contexts: list[RetrievedChunk]) -> str:
    """Assemble the user-turn prompt with retrieved context (or a no-context notice)."""
    if contexts:
        context_block = _format_sources(contexts)
        return (
            "CONTEXT from the user's uploaded documents:\n"
            f"{context_block}\n\n"
            "----\n"
            f"QUESTION: {question}\n\n"
            "Answer using the context above. Cite sources as [Source N]. If the context "
            "is insufficient, say so and label any general guidance accordingly. Finish "
            "with a 'Confidence: high|medium|low' line."
        )
    return (
        f"QUESTION: {question}\n\n"
        "No relevant content was found in the user's uploaded documents for this "
        "question. If you can answer from recognised auditing standards, do so and label "
        "it 'General guidance (not from your documents)'. Do not invent document-specific "
        "figures. Finish with a 'Confidence: high|medium|low' line."
    )
