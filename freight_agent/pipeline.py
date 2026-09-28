"""Application workflow orchestration."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from .decision import decide, summarize
from .exceptions import ConfigurationError, DocumentExtractionError
from .extractor import GroqExtractionService
from .schemas import (
    DecisionStatus,
    ExtractionFreightDocument,
    FreightDocument,
    ProcessingResult,
    Severity,
    ValidationIssue,
)
from .validator import validate_document


class ExtractionService(Protocol):
    def extract(self, raw_text: str) -> ExtractionFreightDocument: ...


class FreightProcessingPipeline:
    def __init__(self, extractor: ExtractionService | None = None) -> None:
        self._extractor = extractor

    def process(self, raw_text: str) -> ProcessingResult:
        if not raw_text or not raw_text.strip():
            return _failure("PROCESSING_ERROR", "Document text is empty.")
        try:
            extractor = self._extractor or GroqExtractionService()
            extracted = extractor.extract(raw_text)
        except (ConfigurationError, DocumentExtractionError) as exc:
            return _failure("EXTRACTION_FAILED", str(exc))
        except Exception:
            return _failure("PROCESSING_ERROR", "An unexpected processing error occurred.")

        issues = validate_document(extracted)
        strict_document: FreightDocument | None = None
        try:
            strict_document = FreightDocument.model_validate(extracted.model_dump())
        except ValidationError:
            pass
        partial = None if strict_document else extracted.model_dump()
        return ProcessingResult(
            status=decide(issues),
            document=strict_document,
            partial_document=partial,
            issues=issues,
            summary=summarize(issues),
        )


def _failure(code: str, message: str) -> ProcessingResult:
    issue = ValidationIssue(code=code, severity=Severity.ERROR, message=message)
    return ProcessingResult(
        status=DecisionStatus.FLAGGED_FOR_HUMAN_REVIEW,
        issues=[issue],
        summary=summarize([issue]),
    )


def process_document(raw_text: str, extractor: ExtractionService | None = None) -> ProcessingResult:
    return FreightProcessingPipeline(extractor).process(raw_text)
