from typing import List, Dict


def _format_cases(cases: List[Dict]) -> str:
    lines = []
    for case in cases:
        case_id = case.get("case_id", "")
        abstract = case.get("abstract", "")
        snippet = abstract[:600].replace("\n", " ").strip()
        lines.append(f"- 案例 {case_id}: {snippet}")
    return "\n".join(lines)


def _format_trade_specific_inputs(trade_specific_inputs: Dict[str, str]) -> str:
    lines = []
    for key, value in trade_specific_inputs.items():
        text = str(value).strip()
        if not text:
            continue
        lines.append(f"- {key}：{text}")
    if not lines:
        return "- 无"
    return "\n".join(lines)


def build_prompt(
    user_text: str,
    temp_c: float,
    wind_speed: float,
    cases: List[Dict],
    humidity: float = 0.0,
) -> str:
    cases_block = _format_cases(cases)

    prompt = f"""
你是建筑安全事故分析助手。请基于检索到的历史案例进行研判，并输出结构化 JSON。

强制规则：
- 你输出的所有自然语言字段必须使用简体中文。
- 必须至少引用 1 个来自检索结果的案例 ID。
- 不得编造事实；如果证据不足，请明确写出"证据不足"，但仍需给出引用案例。
- 只能输出有效 JSON，不要输出 Markdown 或解释文本。

上下文：检索到的历史案例
{cases_block}

环境：
- 温度 (C): {temp_c}
- 风速 (m/s): {wind_speed}
- 湿度 (%): {humidity}

任务：
1) 预测事故严重度等级（1-4）。
2) 抽取核心危险源（中文短语）。
3) 抽取管理缺陷（中文短语）。
4) 提出通用改进建议（中文、可执行）。
5) 基于核心危险源，给出有针对性的应急/预防措施（如高处坠落、触电、机械伤害等不同类型应给出不同措施）。
6) 给出引用案例 citations（仅填写上面案例的 case_id）。

返回 JSON 键：
severity_level (int 1-4), core_hazards (list[str]), management_gaps (list[str]),
improvement_actions (list[str]), targeted_actions (list[str], 针对具体危险源类型的措施),
citations (list[int]), rationale (string, 中文)

事故描述：
{user_text}
""".strip()

    return prompt


TRADE_TYPES = [
    "高处作业", "电气作业", "焊接热作", "土方开挖",
    "运输机械", "起重吊装", "拆除作业", "综合施工",
]


def build_pre_assessment_prompt(
    work_plan: str,
    trade_type: str,
    work_height: float,
    shift: str,
    new_worker_pct: float,
    trade_specific_inputs: Dict[str, str],
    temp_c: float,
    wind_speed: float,
    humidity: float,
    cases: List[Dict],
) -> str:
    cases_block = _format_cases(cases)
    trade_specific_block = _format_trade_specific_inputs(trade_specific_inputs)

    prompt = f"""
你是施工安全风险评估专家。请在施工作业开始前，基于作业计划和检索到的历史事故案例，
评估潜在风险并给出预防措施。输出结构化 JSON。

强制规则：
- 你输出的所有自然语言字段必须使用简体中文。
- 必须至少引用 1 个来自检索结果的案例 ID 作为风险依据。
- 不得编造事实；如证据不足请明确写出。
- 必须结合“工种专项信息”进行风险判断与措施生成。
- 只能输出有效 JSON，不要输出 Markdown 或解释文本。

上下文：检索到的历史类似事故案例
{cases_block}

作业条件：
- 工种类型：{trade_type}
- 作业高度：{work_height} m
- 作业时段：{shift}
- 新工人占比：{new_worker_pct:.0f}%
- 温度 (C)：{temp_c}
- 风速 (m/s)：{wind_speed}
- 湿度 (%)：{humidity}

工种专项信息：
{trade_specific_block}

任务：
1) 评估风险等级（1-4，1=低风险，4=极高风险）。
2) 列出主要潜在危险源（中文短语）。
3) 给出针对性预防措施（中文、可执行、与工种和危险源匹配）。
4) 列出必需的个人防护装备 PPE（中文）。
5) 给出引用案例 citations（仅填写上面案例的 case_id）。
6) 给出评估理由 rationale（中文，解释为什么给出该风险等级）。

返回 JSON 键：
risk_level (int 1-4), potential_hazards (list[str]), preventive_measures (list[str]),
required_ppe (list[str]), citations (list[int]), rationale (string, 中文)

作业计划描述：
{work_plan}
""".strip()

    return prompt
