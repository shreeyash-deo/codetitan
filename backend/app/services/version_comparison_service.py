import difflib
import re
from typing import List, Tuple, Set
from app.models.version import ContentVersion
from app.schemas.finding import FindingOut
from app.schemas.version import (
    ContentVersionSummaryOut,
    DiffHunk,
    FindingDelta,
    VersionComparisonOut,
)


class VersionComparisonService:
    @staticmethod
    def _finding_signature(f) -> Tuple[str, str, str]:
        rule_or_cat = (getattr(f, "guideline_reference", None) or getattr(f, "category", None) or "").strip().lower()
        cat = (getattr(f, "category", "") or "").strip().lower()
        excerpt = (getattr(f, "excerpt", "") or "").strip().lower()
        return (rule_or_cat, cat, excerpt)

    @classmethod
    def compare_versions(
        cls,
        source: ContentVersion,
        target: ContentVersion,
    ) -> VersionComparisonOut:
        # 1. Compute text diff at sentence / line granularity
        src_text = source.content or ""
        tgt_text = target.content or ""

        def tokenize_sentences(text: str) -> List[str]:
            if not text:
                return []
            lines = text.splitlines(keepends=True)
            tokens: List[str] = []
            for line in lines:
                parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', line) if p.strip()]
                if parts:
                    tokens.extend(parts)
                elif line.strip():
                    tokens.append(line.strip())
            return tokens

        src_tokens = tokenize_sentences(src_text)
        tgt_tokens = tokenize_sentences(tgt_text)

        # Fallback to lines if tokenization produced empty (e.g. whitespace-only)
        if not src_tokens and src_text:
            src_tokens = src_text.splitlines(keepends=True)
        if not tgt_tokens and tgt_text:
            tgt_tokens = tgt_text.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, src_tokens, tgt_tokens)
        hunks: List[DiffHunk] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                hunks.append(
                    DiffHunk(
                        change_type="unchanged",
                        content=" ".join(src_tokens[i1:i2]),
                        old_start=i1 + 1,
                        old_lines=i2 - i1,
                        new_start=j1 + 1,
                        new_lines=j2 - j1,
                    )
                )
            elif tag == "delete":
                hunks.append(
                    DiffHunk(
                        change_type="removed",
                        content=" ".join(src_tokens[i1:i2]),
                        old_start=i1 + 1,
                        old_lines=i2 - i1,
                        new_start=j1 + 1,
                        new_lines=0,
                    )
                )
            elif tag == "insert":
                hunks.append(
                    DiffHunk(
                        change_type="added",
                        content=" ".join(tgt_tokens[j1:j2]),
                        old_start=i1 + 1,
                        old_lines=0,
                        new_start=j1 + 1,
                        new_lines=j2 - j1,
                    )
                )
            elif tag == "replace":
                hunks.append(
                    DiffHunk(
                        change_type="removed",
                        content=" ".join(src_tokens[i1:i2]),
                        old_start=i1 + 1,
                        old_lines=i2 - i1,
                        new_start=j1 + 1,
                        new_lines=0,
                    )
                )
                hunks.append(
                    DiffHunk(
                        change_type="added",
                        content=" ".join(tgt_tokens[j1:j2]),
                        old_start=i2 + 1,
                        old_lines=0,
                        new_start=j1 + 1,
                        new_lines=j2 - j1,
                    )
                )

        raw_diff_lines = list(
            difflib.unified_diff(
                src_tokens,
                tgt_tokens,
                fromfile=f"v{source.version_number}",
                tofile=f"v{target.version_number}",
                lineterm="",
            )
        )
        raw_diff = "\n".join(raw_diff_lines)

        # 2. Finding deltas using stable signature
        src_findings = list(source.findings or [])
        tgt_findings = list(target.findings or [])

        src_signatures = {cls._finding_signature(f): f for f in src_findings}
        tgt_signatures = {cls._finding_signature(f): f for f in tgt_findings}

        resolved_signatures: Set[Tuple[str, str, str]] = set(src_signatures.keys()) - set(tgt_signatures.keys())
        new_signatures: Set[Tuple[str, str, str]] = set(tgt_signatures.keys()) - set(src_signatures.keys())
        persistent_signatures: Set[Tuple[str, str, str]] = set(src_signatures.keys()) & set(tgt_signatures.keys())

        resolved_findings = [
            FindingOut.model_validate(src_signatures[sig]) for sig in resolved_signatures
        ]
        new_findings = [
            FindingOut.model_validate(tgt_signatures[sig]) for sig in new_signatures
        ]
        persistent_findings = [
            FindingOut.model_validate(tgt_signatures[sig]) for sig in persistent_signatures
        ]

        score_before = source.compliance_score
        score_after = target.compliance_score
        score_delta = score_after - score_before

        return VersionComparisonOut(
            review_id=source.review_id,
            source_version=ContentVersionSummaryOut.model_validate(source),
            target_version=ContentVersionSummaryOut.model_validate(target),
            score_before=score_before,
            score_after=score_after,
            score_delta=score_delta,
            audit_status_before=source.audit_status,
            audit_status_after=target.audit_status,
            text_diff=hunks,
            raw_diff=raw_diff,
            findings_delta=FindingDelta(
                resolved=resolved_findings,
                new=new_findings,
                persistent=persistent_findings,
            ),
            source_content=src_text,
            target_content=tgt_text,
        )
