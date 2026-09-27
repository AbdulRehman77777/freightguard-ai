import json
from pathlib import Path

from freight_agent.exceptions import DocumentExtractionError
from freight_agent.pipeline import process_document
from freight_agent.schemas import DecisionStatus, ExtractionFreightDocument


class StubExtractor:
    def __init__(self, result): self.result = result
    def extract(self, raw_text): return self.result


class FailingExtractor:
    def extract(self, raw_text): raise DocumentExtractionError("API unavailable")


def test_sample_end_to_end(valid_data):
    valid_data.update(total_pay=2800.0, weight_lbs=46800)
    result = process_document("sample", StubExtractor(ExtractionFreightDocument.model_validate(valid_data)))
    assert result.status == DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW
    assert [issue.code for issue in result.issues] == ["RATE_MISMATCH", "OVERWEIGHT_LOAD"]
    assert result.document is not None
    expected = json.loads((Path(__file__).parents[1] / "samples" / "expected_output.json").read_text())
    assert result.model_dump(mode="json", exclude_none=True) == expected


def test_corrected_document_is_approved(valid_extraction):
    result = process_document("sample", StubExtractor(valid_extraction))
    assert result.status == DecisionStatus.APPROVED
    assert result.issues == []


def test_incomplete_document_preserves_partial_data(valid_data):
    valid_data["load_number"] = None
    result = process_document("sample", StubExtractor(ExtractionFreightDocument.model_validate(valid_data)))
    assert result.document is None
    assert result.partial_document["carrier_name"] == valid_data["carrier_name"]
    assert result.issues[0].code == "INCOMPLETE_DATA"


def test_extraction_failure_never_approved():
    result = process_document("sample", FailingExtractor())
    assert result.status == DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW
    assert result.issues[0].code == "EXTRACTION_FAILED"


def test_empty_input_never_approved():
    result = process_document("   ", StubExtractor(None))
    assert result.status == DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW
    assert result.issues[0].code == "PROCESSING_ERROR"
