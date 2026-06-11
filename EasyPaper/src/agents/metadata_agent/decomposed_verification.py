"""
Verification/result-handling helpers for decomposed paragraph generation.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from .progress import Phase


def handle_local_review_result(
    *,
    local_review: Dict[str, Any],
    verify_stats: Dict[str, int],
    paragraph_index: int,
    attempt: int,
) -> Tuple[str, str]:
    local_status = local_review.get("status", "passed")
    if local_status == "retry_required":
        verify_stats["retried"] += 1
        print(
            f"[MetaDataAgent] Paragraph {paragraph_index} attempt {attempt + 1} "
            f"requested local retry: {local_review.get('issues', [])}"
        )
        return local_status, local_review.get("feedback", "")
    if local_status == "escalate":
        verify_stats["skipped"] += 1
        print(
            f"[MetaDataAgent] Paragraph {paragraph_index} attempt {attempt + 1} "
            "escalated unresolved local issues to outer review"
        )
        return local_status, ""
    if local_status == "fixed_locally":
        print(
            f"[MetaDataAgent] Paragraph {paragraph_index} attempt {attempt + 1} "
            "fixed issues locally before outer verification"
        )
    return local_status, ""


async def verify_claim_and_emit(
    *,
    verifier,
    latex: str,
    para,
    evidence_dag,
    valid_keys_set,
    emitter,
    section_type: str,
    paragraph_index: int,
    max_attempts: int,
    attempt: int,
) -> Any:
    result = await verifier.verify(
        generated_text=latex,
        paragraph_plan=para,
        evidence_dag=evidence_dag,
        valid_citation_keys=valid_keys_set,
        section_type=section_type,
    )

    if emitter is not None:
        fb = (result.feedback_for_retry or "")[:500]
        await emitter.claim_verify_result(
            section_type=section_type,
            paragraph_index=paragraph_index,
            claim_id=para.claim_id,
            passed=result.passed,
            attempt=attempt + 1,
            max_attempts=max_attempts,
            feedback_summary=fb,
            phase=Phase.BODY_SECTIONS,
        )
    return result


def record_claim_verification_failure(
    *,
    verify_stats: Dict[str, int],
    paragraph_index: int,
    attempt: int,
    verification_result,
) -> str:
    verify_stats["retried"] += 1
    print(
        f"[MetaDataAgent] Paragraph {paragraph_index} attempt {attempt + 1} "
        f"failed verification: {len(verification_result.citation_issues)} citation issues, "
        f"{len(verification_result.missing_evidence_refs)} missing refs, "
        f"{len(verification_result.coverage_gaps)} coverage gaps"
    )
    return verification_result.feedback_for_retry
