import logging
from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel

from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.compliance.deterministic_checker import deterministic_checker
from app.services.compliance.ai_checker import ai_checker
from app.services.compliance.scoring_service import scoring_service

logger = logging.getLogger("brandshield.compliance.engine")


class NoApprovedRulesError(Exception):
    """Raised when an audit is requested for a workspace without any approved rules."""
    pass


class ComplianceAuditResult(BaseModel):
    compliance_score: int
    status: str
    summary: str
    findings: List[FindingCreate]


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
        existing_signatures = {
            (f.excerpt.strip().lower(), f.category.strip().lower())
            for f in deterministic_findings
        }
        existing_excerpts = {f.excerpt.strip().lower() for f in deterministic_findings}

        for ai_f in ai_findings:
            sig = (ai_f.excerpt.strip().lower(), ai_f.category.strip().lower())
            exc = ai_f.excerpt.strip().lower()
            # If excerpt already covered by deterministic finding, avoid duplicate card
            if sig in existing_signatures or exc in existing_excerpts:
                continue
            all_findings.append(ai_f)
            existing_signatures.add(sig)
            existing_excerpts.add(exc)

        # Sort merged findings by position in content
        def sort_key(f: FindingCreate):
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

        logger.info(
            f"Audit finished: total_merged_findings={len(all_findings)}, "
            f"score={score}/100, status={status_label}"
        )

        return ComplianceAuditResult(
            compliance_score=score,
            status=status_label,
            summary=summary,
            findings=all_findings,
        )


compliance_engine = ComplianceEngine()
