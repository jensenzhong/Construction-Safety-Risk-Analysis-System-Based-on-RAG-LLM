from __future__ import annotations

import math
from typing import Dict, Iterable, List


_TRADE_KEYWORDS = {
    "高处作业": {
        "base_risk": 2.3,
        "hazards": ["高处坠落", "临边坠落", "坠物打击"],
        "measures": ["作业前确认生命绳、挂点和防坠器状态", "临边、洞口和作业平台按要求设置防护"],
        "ppe": ["安全帽", "全身式安全带", "防滑鞋", "防割手套"],
    },
    "电气作业": {
        "base_risk": 2.0,
        "hazards": ["触电", "电弧灼伤", "误送电"],
        "measures": ["执行停送电和挂牌上锁", "使用绝缘工具并进行验电确认"],
        "ppe": ["安全帽", "绝缘手套", "绝缘鞋", "护目镜"],
    },
    "焊接热作": {
        "base_risk": 1.9,
        "hazards": ["火灾", "爆炸", "灼伤"],
        "measures": ["清除周边可燃物并配置灭火器", "落实动火审批和监护"],
        "ppe": ["安全帽", "焊工面罩", "阻燃手套", "防护鞋"],
    },
    "土方开挖": {
        "base_risk": 2.1,
        "hazards": ["塌方", "坍塌埋压", "机械碰撞"],
        "measures": ["检查放坡、支护和临边防护", "挖机回转半径内设置警戒区"],
        "ppe": ["安全帽", "反光背心", "防砸鞋", "防护手套"],
    },
    "运输机械": {
        "base_risk": 1.7,
        "hazards": ["车辆伤害", "盲区碰撞", "倒车事故"],
        "measures": ["设置交通引导和倒车指挥", "检查制动、报警和照明装置"],
        "ppe": ["安全帽", "反光背心", "防砸鞋"],
    },
    "起重吊装": {
        "base_risk": 2.2,
        "hazards": ["吊物打击", "起重伤害", "吊装失稳"],
        "measures": ["核对吊点、索具、重量和回转范围", "设置警戒区并安排专职指挥"],
        "ppe": ["安全帽", "反光背心", "防砸鞋", "防护手套"],
    },
    "拆除作业": {
        "base_risk": 2.3,
        "hazards": ["结构坍塌", "高处坠落", "坠物打击"],
        "measures": ["按方案分区分层拆除，严禁立体交叉作业", "拆除前切断相关能源和管线"],
        "ppe": ["安全帽", "护目镜", "防尘口罩", "防砸鞋"],
    },
    "综合施工": {
        "base_risk": 1.6,
        "hazards": ["交叉作业伤害", "机械碰撞", "临边坠落"],
        "measures": ["落实班前交底和作业面隔离", "统一现场交通和人员流线"],
        "ppe": ["安全帽", "反光背心", "防砸鞋", "防护手套"],
    },
}


def _pick_trade_profile(trade_type: str) -> Dict[str, object]:
    text = str(trade_type or "").strip()
    for keyword, profile in _TRADE_KEYWORDS.items():
        if keyword in text:
            return profile
    return _TRADE_KEYWORDS["综合施工"]


def _dedupe_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    items: List[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def _risk_level(
    trade_type: str,
    work_height: float,
    shift: str,
    new_worker_pct: float,
    temp_c: float,
    wind_speed: float,
    humidity: float,
) -> int:
    score = float(_pick_trade_profile(trade_type)["base_risk"])

    if work_height >= 15:
        score += 0.9
    elif work_height >= 5:
        score += 0.5

    if "夜" in str(shift):
        score += 0.4

    if new_worker_pct >= 50:
        score += 0.6
    elif new_worker_pct >= 25:
        score += 0.3

    if temp_c >= 35 or temp_c <= 0:
        score += 0.5
    elif temp_c >= 30:
        score += 0.3

    if wind_speed >= 10:
        score += 0.8
    elif wind_speed >= 6:
        score += 0.4

    if humidity >= 85:
        score += 0.3

    return max(1, min(4, int(math.ceil(score))))


def build_local_pre_assessment(
    work_plan: str,
    trade_type: str,
    work_height: float,
    shift: str,
    new_worker_pct: float,
    trade_specific_inputs: Dict[str, object],
    temp_c: float,
    wind_speed: float,
    humidity: float,
    cases: List[Dict],
) -> Dict[str, object]:
    profile = _pick_trade_profile(trade_type)
    risk_level = _risk_level(
        trade_type=trade_type,
        work_height=work_height,
        shift=shift,
        new_worker_pct=new_worker_pct,
        temp_c=temp_c,
        wind_speed=wind_speed,
        humidity=humidity,
    )

    hazards = list(profile["hazards"])
    measures = list(profile["measures"])
    ppe = list(profile["ppe"])
    rationale_bits = [f"工种为{trade_type or '综合施工'}"]

    if work_height >= 5:
        hazards.append("高处作业失足")
        measures.append("高处作业区域实行上下分层防护和工具防坠落管理")
        rationale_bits.append(f"作业高度{work_height:.1f}米")

    if "夜" in str(shift):
        hazards.append("夜间视线不足")
        measures.append("夜间补足照明并安排现场监护")
        rationale_bits.append("夜间作业增加了识别和沟通风险")

    if new_worker_pct >= 25:
        hazards.append("人员经验不足")
        measures.append("开工前进行针对性安全交底和师带徒确认")
        rationale_bits.append(f"新工人占比{new_worker_pct:.0f}%")

    if temp_c >= 35:
        hazards.append("高温中暑")
        measures.append("落实高温错峰作业、饮水补给和中暑应急药品")
        rationale_bits.append(f"环境温度{temp_c:.1f}℃偏高")
    elif temp_c <= 0:
        hazards.append("低温滑跌")
        measures.append("低温时重点检查脚手板、通道和作业面防滑")
        rationale_bits.append(f"环境温度{temp_c:.1f}℃偏低")

    if wind_speed >= 10:
        hazards.append("大风导致吊物摆动或人员失稳")
        measures.append("大风条件下暂停高处、吊装和临边危险作业")
        rationale_bits.append(f"风速{wind_speed:.1f}m/s偏高")
    elif wind_speed >= 6:
        hazards.append("风载影响作业稳定")
        measures.append("加强临边防护、吊装控制和作业面清理")
        rationale_bits.append(f"风速{wind_speed:.1f}m/s较高")

    if humidity >= 85:
        hazards.append("潮湿环境导致滑倒或绝缘性能下降")
        measures.append("潮湿天气加强防滑、防漏电和设备绝缘检查")
        rationale_bits.append(f"湿度{humidity:.0f}%偏高")

    for key, value in (trade_specific_inputs or {}).items():
        text = str(value).strip()
        if not text:
            continue
        rationale_bits.append(f"{key}为{text}")

    if work_plan.strip():
        measures.append("按作业计划逐项核对设备、人员和作业许可条件")

    citations: List[int] = []
    for case in cases:
        case_id = case.get("case_id")
        try:
            citations.append(int(case_id))
        except Exception:
            continue

    rationale = "；".join(_dedupe_keep_order(rationale_bits))
    rationale = f"{rationale}，因此建议按{risk_level}级风险进行管控。"

    deduped_citations: List[int] = []
    seen_citations = set()
    for cid in citations:
        if cid in seen_citations:
            continue
        seen_citations.add(cid)
        deduped_citations.append(cid)

    return {
        "risk_level": risk_level,
        "potential_hazards": _dedupe_keep_order(hazards)[:6],
        "preventive_measures": _dedupe_keep_order(measures)[:8],
        "required_ppe": _dedupe_keep_order(ppe)[:6],
        "citations": deduped_citations[:3],
        "rationale": rationale,
    }
