from rag.prompting import build_pre_assessment_prompt


def test_pre_assessment_prompt_contains_trade_specific_inputs() -> None:
    prompt = build_pre_assessment_prompt(
        work_plan="外墙吊篮清洗作业，需跨层移动。",
        trade_type="高处作业",
        work_height=18.0,
        shift="白天",
        new_worker_pct=30,
        trade_specific_inputs={
            "作业平台类型": "吊篮",
            "临边防护状态": "部分缺失",
            "安全带挂点类型": "临时锚点",
        },
        temp_c=34.0,
        wind_speed=8.0,
        humidity=78.0,
        cases=[{"case_id": 1001, "abstract": "吊篮作业中发生失稳险情。"}],
    )

    assert "工种专项信息" in prompt
    assert "作业平台类型：吊篮" in prompt
    assert "临边防护状态：部分缺失" in prompt
    assert "必须结合“工种专项信息”进行风险判断与措施生成" in prompt
