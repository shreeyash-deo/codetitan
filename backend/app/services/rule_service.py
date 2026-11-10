from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.rule import BrandRule
from app.models.approval import Approval
from app.schemas.rule import ExtractedRuleCandidate, BrandRuleUpdate


class RuleService:
    @staticmethod
    def get_by_id(db: Session, rule_id: int) -> Optional[BrandRule]:
        return db.query(BrandRule).filter(BrandRule.id == rule_id).first()

    @staticmethod
    def list_rules(
        db: Session,
        workspace_id: int,
        approval_status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[BrandRule]:
        query = db.query(BrandRule).filter(BrandRule.workspace_id == workspace_id)
        if approval_status:
            query = query.filter(BrandRule.approval_status == approval_status.lower())
        if category:
            query = query.filter(BrandRule.category == category)
        return query.order_by(BrandRule.created_at.desc()).all()

    @staticmethod
    def save_extracted_rules_with_stats(
        db: Session,
        workspace_id: int,
        document_id: int,
        candidates: List[ExtractedRuleCandidate],
    ) -> Tuple[List[BrandRule], int]:
        """
        Persist AI-extracted candidate rules into the database as 'pending'.
        Prevents duplicate rule proliferation by checking existing titles in the workspace.
        Preserves existing approved rules immutably.
        Returns (created_rules, duplicate_count).
        """
        existing_rules = (
            db.query(BrandRule)
            .filter(BrandRule.workspace_id == workspace_id)
            .all()
        )
        existing_titles = {r.title.strip().lower() for r in existing_rules}

        created_rules: List[BrandRule] = []
        duplicate_count = 0
        for candidate in candidates:
            title_clean = candidate.title.strip()
            # Avoid duplicate rules if an identical rule title already exists in this workspace
            if title_clean.lower() in existing_titles:
                duplicate_count += 1
                continue

            rule = BrandRule(
                workspace_id=workspace_id,
                document_id=document_id,
                title=title_clean,
                description=candidate.description.strip(),
                category=candidate.category.strip(),
                source_reference=candidate.source_reference,
                confidence=candidate.confidence,
                approval_status="pending",  # Always begins as pending
            )
            db.add(rule)
            created_rules.append(rule)
            existing_titles.add(title_clean.lower())

        db.commit()
        for r in created_rules:
            db.refresh(r)

        return created_rules, duplicate_count

    @staticmethod
    def save_extracted_rules(
        db: Session,
        workspace_id: int,
        document_id: int,
        candidates: List[ExtractedRuleCandidate],
    ) -> List[BrandRule]:
        created_rules, _ = RuleService.save_extracted_rules_with_stats(
            db, workspace_id, document_id, candidates
        )
        return created_rules

    @staticmethod
    def update_rule(db: Session, rule: BrandRule, rule_in: BrandRuleUpdate) -> BrandRule:
        update_data = rule_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def approve_rule(db: Session, rule: BrandRule, reviewer_id: int) -> BrandRule:
        """Mark rule as approved authoritative brand knowledge."""
        rule.approval_status = "approved"

        # Record human governance approval
        approval = Approval(
            brand_rule_id=rule.id,
            submitted_by=None,
            reviewer_id=reviewer_id,
            status="approved",
            comment="Approved by authorized reviewer as official brand rule.",
        )
        db.add(approval)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def reject_rule(
        db: Session, rule: BrandRule, reviewer_id: int, reason: Optional[str] = None
    ) -> BrandRule:
        """Mark rule as rejected. Rejected rules are excluded from compliance scanning."""
        rule.approval_status = "rejected"

        approval = Approval(
            brand_rule_id=rule.id,
            submitted_by=None,
            reviewer_id=reviewer_id,
            status="rejected",
            comment=reason or "Rejected by reviewer.",
        )
        db.add(approval)
        db.commit()
        db.refresh(rule)
        return rule


rule_service = RuleService()
