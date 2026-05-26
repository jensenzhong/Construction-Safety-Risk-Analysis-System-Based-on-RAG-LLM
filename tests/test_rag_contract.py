import json

import pytest

from rag.extraction_schema import parse_and_validate_response


def test_rag_citations_filtered_to_retrieved_case_ids() -> None:
    response = json.dumps(
        {
            "severity_level": 4,
            "core_hazards": ["electrical arc"],
            "management_gaps": ["missing PPE"],
            "improvement_actions": ["lockout/tagout", "arc-rated PPE"],
            "citations": [101, "102", 999],
            "rationale": "Pattern aligns with historical electrical events.",
        }
    )

    parsed = parse_and_validate_response(
        response,
        require_citations=True,
        allowed_case_ids=[101, 102, 103],
    )

    assert parsed["citations"] == [101, 102]


def test_rag_requires_non_empty_citations_after_filtering() -> None:
    response = json.dumps(
        {
            "severity_level": 2,
            "core_hazards": ["trip"],
            "management_gaps": ["poor housekeeping"],
            "improvement_actions": ["clear walkway"],
            "citations": [888],
            "rationale": "No matching retrieved precedent cited.",
        }
    )

    with pytest.raises(ValueError, match="citations"):
        parse_and_validate_response(
            response,
            require_citations=True,
            allowed_case_ids=[101],
        )
