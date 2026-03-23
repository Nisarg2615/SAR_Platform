"""
Agent 3 — Narrative Generation
LangGraph node: calls MiniMax LLM, parses output, populates state.narrative.
"""

from __future__ import annotations

from datetime import datetime
from agents.shared.schemas import SARCase, SARNarrative
from agents.agent3_narrative.minimax_client import generate_narrative


# ---------------------------------------------------------------------------
# Section parser helpers
# ---------------------------------------------------------------------------
def _extract_section(text: str, label: str, next_label: str | None = None) -> str:
    """Extract a labelled section from the LLM output."""
    marker = f"[{label}]"
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    if next_label:
        end = text.find(f"[{next_label}]", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()
    return text[start:].strip()


def _parse_narrative_sections(raw: str) -> dict[str, str]:
    """
    Parse the four-section LLM output into a dict.
    Falls back to placing everything in narrative_body if parsing fails.
    """
    labels = [
        "SUBJECT INFORMATION",
        "SUSPICIOUS ACTIVITY DESCRIPTION",
        "NARRATIVE BODY",
        "LAW ENFORCEMENT NOTE",
    ]
    sections: dict[str, str] = {}

    for i, label in enumerate(labels):
        next_label = labels[i + 1] if i + 1 < len(labels) else None
        sections[label] = _extract_section(raw, label, next_label)

    # If parsing failed, treat the entire text as the narrative body
    if not any(sections.values()):
        sections["NARRATIVE BODY"] = raw.strip()

    return sections


# ---------------------------------------------------------------------------
# LangGraph agent node
# ---------------------------------------------------------------------------
async def agent3_generate_narrative(state: SARCase) -> SARCase:
    """
    Agent 3 — LLM Narrative Generation.

    Reads:   state.normalized, state.risk_assessment
    Writes:  state.narrative (SARNarrative)
    Appends: state.audit_trail
    Never raises — all errors go to state.error_log.
    """
    try:
        # Call LLM (or fallback template)
        raw_text = await generate_narrative(state)

        # Parse into labelled sections
        sections = _parse_narrative_sections(raw_text)

        subject_info = sections.get("SUBJECT INFORMATION", "")
        suspicious_desc = sections.get("SUSPICIOUS ACTIVITY DESCRIPTION", "")
        narrative_body = sections.get("NARRATIVE BODY", "")
        law_note = sections.get("LAW ENFORCEMENT NOTE", "")

        # Ensure narrative_body is at least 100 chars (gate requirement)
        if len(narrative_body) < 100:
            # Promote full raw text if section extraction was too sparse
            narrative_body = raw_text

        # Build evidence refs from risk signals
        evidence_refs: list[str] = []
        if state.risk_assessment:
            evidence_refs = [
                f"{s.signal_type}: {s.description}"
                for s in state.risk_assessment.signals
            ]

        # Compose subject_information (merge subject_info + law_note for schema fit)
        combined_subject = subject_info or f"Case {state.case_id}"
        combined_activity = suspicious_desc + (f"\n\n{law_note}" if law_note else "")

        state.narrative = SARNarrative(
            case_id=state.case_id,
            summary=narrative_body[:100] + "...",
            subject_info=combined_subject,
            suspicious_activity=combined_activity or narrative_body[:200],
            law_enforcement_note=law_note or "No specific law enforcement note.",
            narrative_body=narrative_body,
            generation_timestamp=datetime.now(),
        )

        state.audit_trail.append({
            "agent": "Agent 3 - Narrative Generation",
            "action": f"Generated SAR narrative ({len(narrative_body)} chars) "
                      f"using MiniMax-Text-2.5",
            "confidence": 0.90,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        state.error_log.append({
            "agent": "Agent 3 - Narrative Generation",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

    return state
