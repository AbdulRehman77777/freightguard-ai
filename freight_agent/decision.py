"""Conservative, deterministic document decision logic."""

from __future__ import annotations

from .schemas import DecisionStatus, ValidationIssue


def decide(issues: list[ValidationIssue]) -> DecisionStatus:
    return (
        DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW
        if issues
        else DecisionStatus.APPROVED
    )


def summarize(issues: list[ValidationIssue]) -> str:
    if not issues:
        return "Document passed structural and business validation and is approved."
    codes = {issue.code for issue in issues}
    if codes == {"RATE_MISMATCH", "OVERWEIGHT_LOAD"}:
        rate_issue = next(issue for issue in issues if issue.code == "RATE_MISMATCH")
        delta = abs(float(rate_issue.actual_value) - float(rate_issue.expected_value))
        return f"Document requires human review due to a ${delta:,.2f} payment discrepancy and an overweight load."
    descriptions = {
        "RATE_MISMATCH": "a payment discrepancy",
        "OVERWEIGHT_LOAD": "an overweight load",
        "INCOMPLETE_DATA": "incomplete or invalid required data",
        "EXTRACTION_FAILED": "an extraction failure",
        "PROCESSING_ERROR": "a processing failure",
    }
    reasons = [descriptions.get(issue.code, issue.code.lower().replace("_", " ")) for issue in issues]
    return "Document requires human review due to " + ", ".join(dict.fromkeys(reasons)) + "."
