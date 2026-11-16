import logging
import re
from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel

from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.compliance.deterministic_checker import deterministic_checker
from app.services.compliance.ai_checker import ai_checker
from app.services.compliance.scoring_service import scoring_service

logger = logging.getLogger("brandshield.compliance.engine")


def _find_occurrence_spans(content: str, excerpt: str) -> List[Tuple[int, int]]:
    """Find all matching spans of excerpt in content."""
    if not excerpt or excerpt == "[Missing Regulatory Disclaimer]":
        return [(len(content), len(content))]
    pat = re.compile(re.escape(excerpt), re.IGNORECASE)
    spans = [m.span() for m in pat.finditer(content)]
    if not spans:
        pos = 0
        exc_l = excerpt.lower()
        cont_l = content.lower()
        while True:
            idx = cont_l.find(exc_l, pos)
            if idx == -1:
                break
            spans.append((idx, idx + len(excerpt)))
            pos = idx + len(excerpt)
    return spans or [(0, len(excerpt))]


def _assign_finding_spans(findings: List[FindingCreate], content: str) -> List[Tuple[Tuple[int, int], FindingCreate]]:
    """
    Assign each finding to its actual span in content, ensuring multiple occurrences
    of the same phrase receive distinct sequential spans.
    """
    assigned: List[Tuple[Tuple[int, int], FindingCreate]] = []
    used_spans: set = set()

    for f in findings:
        existing_span = getattr(f, "_span", None)
        if existing_span and isinstance(existing_span, tuple) and existing_span not in used_spans:
            used_spans.add(existing_span)
            assigned.append((existing_span, f))
            continue

        candidate_spans = _find_occurrence_spans(content, f.excerpt)
        chosen = None
        for span in candidate_spans:
            if span not in used_spans:
                chosen = span
                break
        if not chosen:
            chosen = candidate_spans[0] if candidate_spans else (0, len(f.excerpt))

        used_spans.add(chosen)
        object.__setattr__(f, "_span", chosen)
        assigned.append((chosen, f))

    return assigned


def _spans_overlap(s1: Tuple[int, int], s2: Tuple[int, int]) -> bool:
    """Check if two text spans overlap or represent the same text occurrence."""
    start1, end1 = s1
    start2, end2 = s2
    return max(start1, start2) < min(end1, end2) or (start1 == start2 and end1 == end2)


def is_valid_natural_replacement(ai_suggestion: Optional[str], excerpt: str, original_content: str) -> bool:
    """
    Validate that an AI suggestion is non-empty, grounded in context, and suitable as
    a natural drop-in replacement rather than an instruction, generic text, or violation.
    """
    if not ai_suggestion or not isinstance(ai_suggestion, str):
        return False

    sugg = ai_suggestion.strip()
    if not sugg or len(sugg) < 2 or len(sugg) > 250:
        return False

    sugg_l = sugg.lower()
    exc_l = excerpt.lower().strip()

    # Reject instructional or meta text instead of a drop-in replacement
    meta_prefixes = (
        "revise ", "replace ", "remove ", "change ", "delete ", "please ",
        "you should", "author should", "consider ", "it is recommended",
        "none", "n/a", "no correction", "suggested revision",
    )
    if any(sugg_l.startswith(prefix) for prefix in meta_prefixes):
        return False

    # Reject if suggestion merely repeats the non-compliant excerpt
    if sugg_l == exc_l or (len(exc_l) > 6 and exc_l in sugg_l):
        return False

    # Reject if suggestion re-introduces prohibited guarantee/zero-risk promises
    prohibited_markers = (
        "100% guaranteed", "guarantee returns", "guaranteed returns", "guaranteed profits",
        "100% risk-free", "zero risk", "zero investment risk", "without any risk",
        "overnight wealth", "make you rich", "revenue overnight",
    )
    if any(pm in sugg_l for pm in prohibited_markers):
        return False

    # Reject generic placeholders
    generic_placeholders = (
        "approved terminology", "compliant terminology", "compliant alternative",
    )
    if any(gp in sugg_l for gp in generic_placeholders):
        return False

    return True


class NoApprovedRulesError(Exception):
    """Raised when an audit is requested for a workspace without any approved rules."""
    pass


class ComplianceAuditResult(BaseModel):
    compliance_score: int
    status: str
    summary: str
    findings: List[FindingCreate]
    audit_status: str = "verified"


class ComplianceEngine:
    @classmethod
    def run_compliance_audit(
        cls,
        content: str,
        content_type: str,
        approved_rules: List[BrandRule],
    ) -> ComplianceAuditResult:
        """
        Orchestrate the hybrid compliance audit:
        1. Validates approved rules exist (raises NoApprovedRulesError if none exist).
        2. Executes Python deterministic checks.
        3. Executes AI contextual checks.
        4. Merges and deduplicates findings without double-counting.
        5. Computes official compliance score and status.
        """
        # Boundary condition: Zero approved rules
        if not approved_rules:
            logger.warning("Audit aborted: No approved brand rules found in workspace.")
            raise NoApprovedRulesError(
                "Brand rules unavailable: No approved brand rules found in this organisation. "
                "Brand-specific compliance analysis cannot be completed until at least one rule is approved."
            )

        logger.info(
            f"Compliance audit started: content_len={len(content)}, "
            f"content_type={content_type}, approved_rules_count={len(approved_rules)}"
        )

        # 1. Run Python Deterministic Checks
        deterministic_findings = deterministic_checker.evaluate(
            content=content,
            content_type=content_type,
            approved_rules=approved_rules,
        )
        logger.info(f"Stage 1 (Deterministic) completed: {len(deterministic_findings)} finding(s).")

        # 2. Run AI Contextual Checks
        ai_summary, ai_findings = ai_checker.evaluate(
            content=content,
            content_type=content_type,
            approved_rules=approved_rules,
        )
        logger.info(f"Stage 2 (AI Semantic) completed: {len(ai_findings)} finding(s).")

        # 3. Merge & Deduplicate findings
        all_findings: List[FindingCreate] = list(deterministic_findings)
        assigned_det = _assign_finding_spans(all_findings, content)

        for ai_f in ai_findings:
            ai_span = getattr(ai_f, "_span", None)
            if not ai_span or not isinstance(ai_span, tuple):
                c_spans = _find_occurrence_spans(content, ai_f.excerpt)
                ai_span = c_spans[0] if c_spans else (0, len(ai_f.excerpt))
                object.__setattr__(ai_f, "_span", ai_span)

            # Check if this AI finding overlaps with an existing deterministic finding at this occurrence
            matching_df = None
            for df_span, df in assigned_det:
                if _spans_overlap(ai_span, df_span):
                    matching_df = df
                    break

            if matching_df is not None:
                # Same violation occurrence! Deduplicate by not creating a duplicate card.
                # Update suggestion ONLY if AI suggestion is high quality and natural:
                if is_valid_natural_replacement(ai_f.suggested_correction, matching_df.excerpt, content):
                    det_sugg = (matching_df.suggested_correction or "").strip().lower()
                    is_generic_det = any(g in det_sugg for g in ("approved terminology", "compliant alternative", "compliant terminology"))
                    if is_generic_det or is_valid_natural_replacement(ai_f.suggested_correction, matching_df.excerpt, content):
                        matching_df.suggested_correction = ai_f.suggested_correction.strip()
                continue

            # Distinct occurrence or semantic-only finding: add to all_findings
            all_findings.append(ai_f)
            assigned_det.append((ai_span, ai_f))

        # Sort merged findings strictly by actual start span in content
        def sort_key(f: FindingCreate):
            span = getattr(f, "_span", None)
            if span and isinstance(span, tuple):
                return span[0]
            if f.excerpt == "[Missing Regulatory Disclaimer]":
                return 999999
            pos = content.find(f.excerpt)
            return pos if pos != -1 else 999999

        all_findings.sort(key=sort_key)

        # 4. Calculate Compliance Score
        score, status_label = scoring_service.calculate_score(all_findings)

        # 5. Formulate executive summary clearly identifying AI status
        summary = ai_summary
        if not summary:
            if not all_findings:
                summary = "Content conforms to all approved brand guidelines. No compliance violations detected."
            else:
                summary = f"Audit detected {len(all_findings)} compliance violation(s). Score: {score}/100."
        elif "unavailable" in summary.lower():
            if all_findings:
                summary = f"Deterministic compliance audit detected {len(all_findings)} violation(s). Score: {score}/100. ({ai_summary})"
            else:
                summary = f"Deterministic audit passed (no rule violations detected). ({ai_summary})"

        # 6. Audit integrity: verify semantic AI executed without degradation
        is_ai_degraded = (
            not ai_summary
            or "unavailable" in ai_summary.lower()
            or "skipped" in ai_summary.lower()
            or "failed" in ai_summary.lower()
            or "error" in ai_summary.lower()
        )
        audit_status = "degraded" if is_ai_degraded else "verified"

        logger.info(
            f"Audit finished: total_merged_findings={len(all_findings)}, "
            f"score={score}/100, status={status_label}, audit_status={audit_status}"
        )

        return ComplianceAuditResult(
            compliance_score=score,
            status=status_label,
            summary=summary,
            findings=all_findings,
            audit_status=audit_status,
        )


compliance_engine = ComplianceEngine()
