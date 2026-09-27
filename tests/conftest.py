from __future__ import annotations

import pytest

from freight_agent.schemas import ExtractionFreightDocument


@pytest.fixture
def valid_data() -> dict:
    return {
        "carrier_name": "Apex Logistics Solutions LLC",
        "load_number": "LD-994821",
        "pickup_location": {"city": "Dallas", "state": "TX", "zip": "75201"},
        "delivery_location": {"city": "Atlanta", "state": "GA", "zip": "30303"},
        "total_linehaul_rate": 2200.0,
        "fuel_surcharge": 350.0,
        "total_pay": 2550.0,
        "weight_lbs": 44000,
    }


@pytest.fixture
def valid_extraction(valid_data: dict) -> ExtractionFreightDocument:
    return ExtractionFreightDocument.model_validate(valid_data)
