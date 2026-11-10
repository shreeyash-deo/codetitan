from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel

from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.compliance.deterministic_checker import deterministic_checker
from app.services.compliance.ai_checker import ai_checker
from app.services.compliance.scoring_service import scoring_service


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
        1. Validates approved rules exist.
        2. Executes Python deterministic checks.
        3. Executes AI contextual checks.
        4. Merges and deduplicates findings.
        5. Computes official compliance score and status.
        """
        # Boundary condition: Zero approved rules
        if not approved_rules:
            raise NoApprovedRulesError(
                "No approved brand rules found in this workspace. "
                "Brand-specific compliance analysis cannot be completed until at least one rule is approved."
            )

        # 1. Run Python Deterministic Checks
        deterministic_findings = deterministic_checker.evaluate(
            content=content,
            content_type=content_type,
            approved_rules=approved_rules,
        )

        # 2. Run AI Contextual Checks
        ai_summary, ai_findings = ai_checker.evaluate(
            content=content,
            content_type=content_type,
            approved_rules=approved_rules,
        )

        # 3. Merge & Deduplicate findings
        all_findings: List[FindingCreate] = list(deterministic_findings)
        existing_signatures = {
            (f.excerpt.strip().lower(), f.category.strip().lower())
            for f in deterministic_findings
        }

        for ai_f in ai_findings:
            sig = (ai_f.excerpt.strip().lower(), ai_f.category.strip().lower())
            if sig not in existing_signatures:
                all_findings.append(ai_f)
                existing_signatures.add(sig)

        # 4. Calculate Compliance Score
        score, status_label = scoring_service.calculate_score(all_findings)

        # Formulate executive summary if AI summary was generic
        summary = ai_summary
        if not summary:
            if not all_findings:
                summary = "Content conforms to all approved brand guidelines. No compliance violations detected."
            else:
                summary = f"Audit detected {len(all_findings)} compliance violation(s). Score: {score}/100."

        return ComplianceAuditResult(
            compliance_score=score,
            status=status_label,
            summary=summary,
            findings=all_findings,
        )


compliance_engine = ComplianceEngine()
