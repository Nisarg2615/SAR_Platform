"""
Agent 4 — Compliance Engine
LangGraph node: runs all 8 AML rules, collects issues, populates state.compliance.
"""

from __future__ import annotations

from datetime import datetime
from agents.shared.schemas import SARCase, ComplianceResult
from agents.agent4_compliance.rules import ALL_RULES


async def agent4_check_compliance(state: SARCase) -> SARCase:
    """
    Agent 4 — Compliance Check.

    Reads:   state.normalized, state.risk_assessment, state.narrative
    Writes:  state.compliance (ComplianceResult)
    Appends: state.audit_trail
    Never raises — all errors go to state.error_log.
    """
    try:
        issues: list[str] = []

        for rule_fn in ALL_RULES:
            try:
                result = rule_fn(state)
                if result is not None:
                    issues.append(result)
            except Exception as rule_err:
                # Individual rule failure should not stop the others
                issues.append(f"[Rule error — {rule_fn.__name__}]: {rule_err}")

        # Derive boolean compliance flags from the issues list
        bsa_issue = any("BSA CTR" in i or "Structuring" in i for i in issues)
        geo_issue = any("geography" in i.lower() for i in issues)
        all_fields_complete = (
            state.normalized is not None
            and state.risk_assessment is not None
            and state.narrative is not None
        )

        directive = state.orchestrator_decision.directives.get("agent4_compliance") if state.orchestrator_decision else None
        if directive:
            from agents.llm.client import llm_call
            llm_res, provider = await llm_call(
                "You are an AML Compliance AI. Review the case and output a 1 sentence compliance summary.",
                f"Issues found: {len(issues)}",
                directive.provider.value,
                directive.model,
                fallback_chain=[p.value for p in directive.fallback_chain]
            )
            if llm_res:
                issues.append(f"[{provider} AI Analysis]: {llm_res}")

        state.compliance = ComplianceResult(
            case_id=state.case_id,
            bsa_compliant=not bsa_issue,
            all_fields_complete=all_fields_complete,
            fincen_format_valid=not geo_issue,
            compliance_issues=issues,   # always a list, may be empty
            validated_timestamp=datetime.now(),
        )

        state.audit_trail.append({
            "agent": "Agent 4 - Compliance Engine",
            "action": (
                f"Ran {len(ALL_RULES)} AML rules — "
                f"{'PASS' if not issues else f'{len(issues)} issue(s) found'}"
            ),
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        state.error_log.append({
            "agent": "Agent 4 - Compliance Engine",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

    return state
