from typing import List, Tuple, Any

SEVERITY_DEDUCTIONS = {
    "critical": 25,
    "major": 12,
    "minor": 5,
    "suggestion": 0,
}


class ScoringService:
    @staticmethod
    def calculate_score(findings: List[Any]) -> Tuple[int, str]:
        """
        Calculate compliance score starting from 100 and deducting points per unique violation.
        Deductions:
          - critical: -25 points
          - major: -12 points
          - minor: -5 points
          - suggestion: 0 points

        Avoids counting duplicate findings more than once.
        Clamps result strictly between 0 and 100.
        Statuses:
          - 85–100: compliant
          - 60–84: needs_changes
          - 0–59: critical_issues
        """
        score = 100
        seen_keys = set()

        for f in findings:
            # Finding object or Pydantic model / dict
            excerpt = getattr(f, "excerpt", None) or (f.get("excerpt") if isinstance(f, dict) else "")
            category = getattr(f, "category", None) or (f.get("category") if isinstance(f, dict) else "")
            severity = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "minor")
            status = getattr(f, "status", None) or (f.get("status") if isinstance(f, dict) else "open")

            # Only count active/open or un-remediated violations
            if status in ("rejected", "applied"):
                continue

            # Deduplicate by (excerpt, category)
            dedup_key = (excerpt.strip().lower(), category.strip().lower())
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            sev_clean = severity.strip().lower()
            deduction = SEVERITY_DEDUCTIONS.get(sev_clean, 5)
            score -= deduction

        # Clamp between 0 and 100
        clamped_score = max(0, min(100, score))

        # Determine status
        if clamped_score >= 85:
            status_label = "compliant"
        elif clamped_score >= 60:
            status_label = "needs_changes"
        else:
            status_label = "critical_issues"

        return clamped_score, status_label


scoring_service = ScoringService()
