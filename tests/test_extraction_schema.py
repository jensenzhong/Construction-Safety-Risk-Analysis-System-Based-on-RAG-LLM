import json

import pytest

from rag.extraction_schema import parse_and_validate_response


def test_extraction_schema_valid_payload() -> None:
    response = json.dumps(
        {
            "severity_level": 3,
            "core_hazards": ["fall from height", "slippery surface"],
            "management_gaps": ["insufficient ladder stabilization"],
            "improvement_actions": ["assign ladder spotter", "use anti-slip feet"],
            "confidence": 0.87,
            "reasoning_summary": "Worker fell after ladder base slipped.",
        }
    )

    parsed = parse_and_validate_response(response, require_citations=False)

    assert parsed["severity_level"] == 3
    assert isinstance(parsed["core_hazards"], list)
    assert isinstance(parsed["management_gaps"], list)
    assert isinstance(parsed["improvement_actions"], list)
    assert 0 <= parsed["confidence"] <= 1


def test_extraction_schema_rejects_invalid_severity() -> None:
    response = json.dumps(
        {
            "severity_level": 9,
            "core_hazards": ["electric arc"],
            "management_gaps": ["no lockout"],
            "improvement_actions": ["enforce LOTO"],
        }
    )

    with pytest.raises(ValueError, match="severity_level"):
        parse_and_validate_response(response, require_citations=False)


def test_extraction_schema_accepts_legacy_severity_field() -> None:
    response = json.dumps(
        {
            "severity": 2,
            "core_hazards": ["cut hazard"],
            "management_gaps": ["unguarded blade"],
            "improvement_actions": ["install guard"],
        }
    )

    parsed = parse_and_validate_response(response, require_citations=False)
    assert parsed["severity_level"] == 2
