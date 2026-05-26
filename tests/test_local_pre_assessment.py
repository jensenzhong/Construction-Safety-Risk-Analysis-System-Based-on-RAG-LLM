from rag.local_pre_assessment import build_local_pre_assessment


def test_local_pre_assessment_returns_valid_payload() -> None:
    payload = build_local_pre_assessment(
        work_plan="在18层外立面进行吊篮安装和调试，夜间继续施工。",
        trade_type="高处作业",
        work_height=18.0,
        shift="夜间",
        new_worker_pct=35,
        trade_specific_inputs={
            "作业平台类型": "吊篮",
            "挂点状态": "临时挂点",
        },
        temp_c=36.0,
        wind_speed=9.0,
        humidity=88.0,
        cases=[
            {"case_id": 101, "abstract": "高处作业坠落事故"},
            {"case_id": 205, "abstract": "吊篮失稳事故"},
        ],
    )

    assert payload["risk_level"] >= 3
    assert payload["citations"] == [101, 205]
    assert payload["potential_hazards"]
    assert payload["preventive_measures"]
    assert payload["required_ppe"]
    assert "建议按" in payload["rationale"]
