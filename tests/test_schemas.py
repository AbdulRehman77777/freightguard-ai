import math

import pytest
from pydantic import ValidationError

from freight_agent.schemas import ExtractionFreightDocument, FreightDocument, Location


def test_valid_freight_document(valid_data):
    assert FreightDocument.model_validate(valid_data).pickup_location.zip == "75201"


@pytest.mark.parametrize("field,value", [("carrier_name", None), ("load_number", "")])
def test_missing_or_blank_identity_rejected(valid_data, field, value):
    valid_data[field] = value
    with pytest.raises(ValidationError):
        FreightDocument.model_validate(valid_data)


@pytest.mark.parametrize("location", [
    {"city": "", "state": "TX", "zip": "75201"},
    {"city": "Dallas", "state": "Texas", "zip": "75201"},
    {"city": "Dallas", "state": "TX", "zip": "7520"},
])
def test_invalid_location_rejected(location):
    with pytest.raises(ValidationError):
        Location.model_validate(location)


@pytest.mark.parametrize("field,value", [
    ("total_pay", -1), ("fuel_surcharge", math.inf), ("weight_lbs", -1),
])
def test_invalid_numeric_values_rejected(valid_data, field, value):
    valid_data[field] = value
    with pytest.raises(ValidationError):
        FreightDocument.model_validate(valid_data)


def test_unexpected_fields_rejected(valid_data):
    valid_data["secret"] = "unexpected"
    with pytest.raises(ValidationError):
        FreightDocument.model_validate(valid_data)


def test_final_schema_rejects_type_coercion(valid_data):
    valid_data["weight_lbs"] = "44000"
    with pytest.raises(ValidationError):
        FreightDocument.model_validate(valid_data)


def test_extraction_schema_requires_every_key_and_forbids_extras(valid_data):
    valid_data.pop("load_number")
    valid_data["unexpected"] = None
    with pytest.raises(ValidationError) as exc_info:
        ExtractionFreightDocument.model_validate(valid_data)
    error_types = {error["type"] for error in exc_info.value.errors()}
    assert {"missing", "extra_forbidden"} <= error_types


def test_extraction_model_allows_nulls():
    extracted = ExtractionFreightDocument(
        carrier_name=None,
        load_number=None,
        pickup_location=None,
        delivery_location=None,
        total_linehaul_rate=None,
        fuel_surcharge=None,
        total_pay=None,
        weight_lbs=None,
    )
    assert extracted.load_number is None
    assert extracted.pickup_location is None
