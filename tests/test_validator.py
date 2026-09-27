from copy import deepcopy

import pytest

from freight_agent.schemas import ExtractionFreightDocument
from freight_agent.validator import validate_document, validate_rate, validate_weight


def codes(issues):
    return [issue.code for issue in issues]


def test_correct_total(valid_extraction):
    assert validate_rate(valid_extraction) == []


def test_incorrect_total_and_provided_discrepancy(valid_data):
    valid_data.update(total_pay=2800.0, weight_lbs=46800)
    issues = validate_document(ExtractionFreightDocument.model_validate(valid_data))
    assert codes(issues) == ["RATE_MISMATCH", "OVERWEIGHT_LOAD"]
    assert "Difference: $250.00" in issues[0].message


def test_zero_fuel_surcharge(valid_data):
    valid_data.update(fuel_surcharge=0, total_pay=2200)
    assert validate_rate(ExtractionFreightDocument.model_validate(valid_data)) == []


def test_decimal_precision_is_compared_at_cents(valid_data):
    valid_data.update(total_linehaul_rate=0.1, fuel_surcharge=0.2, total_pay=0.3)
    assert validate_rate(ExtractionFreightDocument.model_validate(valid_data)) == []


def test_missing_financial_operand_reports_incomplete_only(valid_data):
    valid_data["fuel_surcharge"] = None
    issues = validate_document(ExtractionFreightDocument.model_validate(valid_data))
    assert "RATE_MISMATCH" not in codes(issues)
    assert "INCOMPLETE_DATA" in codes(issues)


@pytest.mark.parametrize("weight,expected", [(44999, False), (45000, False), (45001, True), (46800, True)])
def test_weight_boundaries(valid_data, weight, expected):
    valid_data["weight_lbs"] = weight
    assert bool(validate_weight(ExtractionFreightDocument.model_validate(valid_data))) is expected


@pytest.mark.parametrize("path", [
    ("carrier_name",), ("load_number",), ("pickup_location", "city"),
    ("pickup_location", "zip"), ("delivery_location", "state"),
])
def test_individual_missing_fields(valid_data, path):
    data = deepcopy(valid_data)
    target = data
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = None
    issues = validate_document(ExtractionFreightDocument.model_validate(data))
    assert codes(issues)[-1] == "INCOMPLETE_DATA"
    assert ".".join(path) in issues[-1].message


def test_ambiguous_location_and_multiple_missing_fields(valid_data):
    valid_data["pickup_location"] = None
    valid_data["load_number"] = None
    issue = validate_document(ExtractionFreightDocument.model_validate(valid_data))[-1]
    assert issue.code == "INCOMPLETE_DATA"
    assert "pickup_location" in issue.message and "load_number" in issue.message
