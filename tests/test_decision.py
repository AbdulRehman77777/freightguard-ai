import pytest

from freight_agent.decision import decide
from freight_agent.schemas import DecisionStatus, Severity, ValidationIssue


def issue(severity):
    return ValidationIssue(code="TEST", severity=severity, message="test")


def test_no_issues_approved():
    assert decide([]) == DecisionStatus.APPROVED


@pytest.mark.parametrize("issues", [
    [issue(Severity.ERROR)],
    [issue(Severity.WARNING)],
    [issue(Severity.ERROR), issue(Severity.WARNING)],
])
def test_any_issue_flagged(issues):
    assert decide(issues) == DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW
