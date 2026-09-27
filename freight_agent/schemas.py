"""Pydantic data contracts for extraction, validation, and public output."""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ZIP_PATTERN = re.compile(r"^\d{5}(?:-\d{4})?$")
STATE_PATTERN = re.compile(r"^[A-Z]{2}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractionLocation(StrictModel):
    city: str | None
    state: str | None
    zip: str | None


class ExtractionFreightDocument(StrictModel):
    """Nullable contract used at the LLM boundary; absence is never fabricated."""

    carrier_name: str | None
    load_number: str | None
    pickup_location: ExtractionLocation | None
    delivery_location: ExtractionLocation | None
    total_linehaul_rate: float | None
    fuel_surcharge: float | None
    total_pay: float | None
    weight_lbs: int | None


class Location(StrictModel):
    city: str = Field(min_length=1)
    state: str
    zip: str

    @field_validator("city")
    @classmethod
    def city_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("city must not be blank")
        return value

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        value = value.strip().upper()
        if not STATE_PATTERN.fullmatch(value):
            raise ValueError("state must be a two-letter abbreviation")
        return value

    @field_validator("zip")
    @classmethod
    def valid_zip(cls, value: str) -> str:
        value = value.strip()
        if not ZIP_PATTERN.fullmatch(value):
            raise ValueError("ZIP must use 12345 or 12345-6789 format")
        return value


class FreightDocument(StrictModel):
    carrier_name: str = Field(min_length=1)
    load_number: str = Field(min_length=1)
    pickup_location: Location
    delivery_location: Location
    total_linehaul_rate: float = Field(ge=0)
    fuel_surcharge: float = Field(ge=0)
    total_pay: float = Field(ge=0)
    weight_lbs: int = Field(ge=0)

    @field_validator("carrier_name", "load_number")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("total_linehaul_rate", "fuel_surcharge", "total_pay")
    @classmethod
    def money_is_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("monetary values must be finite")
        return value


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class DecisionStatus(StrEnum):
    APPROVED = "APPROVED"
    FLAGGED_FOR_HUMAN_REVIEW = "FLAGGED_FOR_HUMAN_REVIEW"


class ValidationIssue(StrictModel):
    code: str
    severity: Severity
    message: str
    field: str | None = None
    expected_value: Any | None = None
    actual_value: Any | None = None


class ProcessingResult(StrictModel):
    status: DecisionStatus
    document: FreightDocument | None = None
    partial_document: dict[str, Any] | None = None
    issues: list[ValidationIssue]
    summary: str
