"""Deterministic freight business rules."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import ValidationError

from .schemas import (
    ExtractionFreightDocument,
    FreightDocument,
    Severity,
    ValidationIssue,
)

MONEY_QUANTUM = Decimal("0.01")
MAX_WEIGHT_LBS = 45_000


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def find_incomplete_fields(extracted: ExtractionFreightDocument) -> list[str]:
    try:
        FreightDocument.model_validate(extracted.model_dump())
        return []
    except ValidationError as exc:
        names: list[str] = []
        for error in exc.errors():
            name = ".".join(str(part) for part in error["loc"])
            if name not in names:
                names.append(name)
        return names


def validate_incomplete(extracted: ExtractionFreightDocument) -> list[ValidationIssue]:
    fields = find_incomplete_fields(extracted)
    if not fields:
        return []
    return [ValidationIssue(
        code="INCOMPLETE_DATA",
        severity=Severity.ERROR,
        message=f"Required information is missing, invalid, or ambiguous: {', '.join(fields)}.",
        field=", ".join(fields),
    )]


def validate_rate(extracted: ExtractionFreightDocument) -> list[ValidationIssue]:
    values = (extracted.total_linehaul_rate, extracted.fuel_surcharge, extracted.total_pay)
    if any(value is None for value in values):
        return []
    linehaul, fuel, stated = (_money(value) for value in values if value is not None)
    calculated = linehaul + fuel
    if calculated == stated:
        return []
    difference = abs(stated - calculated)
    return [ValidationIssue(
        code="RATE_MISMATCH",
        severity=Severity.ERROR,
        message=(f"Calculated payment is ${calculated:,.2f}, but the document states "
                 f"${stated:,.2f}. Difference: ${difference:,.2f}."),
        field="total_pay",
        expected_value=float(calculated),
        actual_value=float(stated),
    )]


def validate_weight(extracted: ExtractionFreightDocument) -> list[ValidationIssue]:
    if extracted.weight_lbs is None or extracted.weight_lbs <= MAX_WEIGHT_LBS:
        return []
    overage = extracted.weight_lbs - MAX_WEIGHT_LBS
    return [ValidationIssue(
        code="OVERWEIGHT_LOAD",
        severity=Severity.WARNING,
        message=(f"Load weight of {extracted.weight_lbs:,} lbs exceeds the "
                 f"{MAX_WEIGHT_LBS:,} lbs threshold by {overage:,} lbs."),
        field="weight_lbs",
        expected_value=MAX_WEIGHT_LBS,
        actual_value=extracted.weight_lbs,
    )]


def validate_document(extracted: ExtractionFreightDocument) -> list[ValidationIssue]:
    """Collect every detectable issue in stable rule order."""
    return [
        *validate_rate(extracted),
        *validate_weight(extracted),
        *validate_incomplete(extracted),
    ]
