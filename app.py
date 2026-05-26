import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from llm.client import chat
from rag.config import DATA_PATH, FAISS_INDEX_PATH, KEEP_COLS, TEXT_COL
from rag.extraction_schema import (
    parse_and_validate_pre_assessment,
)
from rag.index_builder import build_index
from rag.local_pre_assessment import build_local_pre_assessment
from rag.prompting import build_pre_assessment_prompt, TRADE_TYPES
from rag.retrieval import retrieve
from sensors.api import read_sensors


st.set_page_config(
    page_title="工程安全智能决策助手",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Warm sienna palette — single hue, depth via lightness
C = {
    "bg":        "#F9F7F4",
    "bg_warm":   "#F4F0EB",
    "card":      "#FFFFFF",
    "border":    "#E8E2D9",
    "border_d":  "#D6CEC3",
    "ink":       "#1A1613",
    "ink2":      "#3D3530",
    "sub":       "#6B635B",
    "muted":     "#9C9489",
    "faint":     "#C5BEB6",
    "a50":       "#FAF0EB",
    "a100":      "#F2DDD2",
    "a200":      "#E4BCA6",
    "a300":      "#D4A08A",
    "a400":      "#C4704B",
    "a500":      "#A85A38",
    "a600":      "#8B4528",
    "a700":      "#6B341D",
    "s1":        "#D4A08A",
    "s2":        "#C4704B",
    "s3":        "#A85A38",
    "s4":        "#7A3E24",
}

SEVERITY_CFG = {
    1: {"color": C["s1"], "bg": C["a50"],  "label": "轻微"},
    2: {"color": C["s2"], "bg": C["a100"], "label": "一般"},
    3: {"color": C["s3"], "bg": C["a100"], "label": "严重"},
    4: {"color": C["s4"], "bg": C["a100"], "label": "重大"},
}


def rgba(hex_color: str, alpha: float) -> str:
    v = hex_color.lstrip("#")
    return f"rgba({int(v[0:2],16)},{int(v[2:4],16)},{int(v[4:6],16)},{alpha})"


def apply_theme() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

:root {{
    --font-display: 'Source Serif 4', 'Noto Serif SC', Georgia, serif;
    --font-body: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background: {C["bg"]};
    color: {C["ink"]};
    font-family: var(--font-body);
}}
[data-testid="stHeader"] {{
    background: {rgba(C["bg"], 0.85)};
    backdrop-filter: blur(12px);
}}
[data-testid="stSidebar"] {{
    background: {C["bg_warm"]};
    border-right: 1px solid {C["border"]};
}}
h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-display) !important;
    color: {C["ink"]} !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
}}
p, div, span, label, li {{ color: {C["ink"]}; }}

::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {C["border_d"]}; border-radius: 6px; }}

.hero {{ max-width: 720px; margin: 0 auto 8px; padding: 52px 0 36px; text-align: center; }}
.hero-title {{ font-family: var(--font-display); font-size: 2.1rem; font-weight: 700; color: {C["ink"]}; letter-spacing: -0.025em; margin: 0 0 10px; line-height: 1.25; }}
.hero-sub {{ color: {C["sub"]}; font-size: 0.95rem; line-height: 1.6; margin: 0; }}
.hero-divider {{ width: 48px; height: 2px; background: {C["a400"]}; border-radius: 2px; margin: 20px auto 0; }}

.sec-title {{ font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; color: {C["ink"]}; margin: 40px 0 4px; letter-spacing: -0.01em; }}
.sec-desc {{ color: {C["muted"]}; font-size: 0.85rem; margin: 0 0 20px; }}
.sec-rule {{ border: none; height: 1px; background: {C["border"]}; margin: 32px 0; }}

.pill {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border-radius: 999px; font-size: 0.8rem; font-weight: 500; }}
.pill-ok {{ background: {C["a50"]}; color: {C["a500"]}; border: 1px solid {C["a200"]}; }}
.pill-warn {{ background: #FFF8F0; color: {C["a600"]}; border: 1px solid {C["a200"]}; }}

.kpi {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 12px; padding: 22px 24px; transition: box-shadow 0.25s ease, border-color 0.25s ease; }}
.kpi:hover {{ border-color: {C["border_d"]}; box-shadow: 0 2px 12px {rgba(C["ink"], 0.04)}; }}
.kpi-label {{ font-size: 0.75rem; font-weight: 500; color: {C["muted"]}; text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 8px; }}
.kpi-val {{ font-family: var(--font-display); font-size: 1.9rem; font-weight: 700; color: {C["ink"]}; letter-spacing: -0.02em; margin: 0; line-height: 1; }}
.kpi-note {{ color: {C["muted"]}; font-size: 0.78rem; margin-top: 6px; }}
.kpi-bar {{ height: 3px; border-radius: 3px; margin-top: 14px; }}

[data-testid="stMetric"] {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 12px; padding: 18px 22px; }}
[data-testid="stMetricLabel"] {{ color: {C["muted"]} !important; font-size: 0.78rem !important; letter-spacing: 0.04em; }}
[data-testid="stMetricValue"] {{ font-family: var(--font-display) !important; font-weight: 700 !important; color: {C["ink"]} !important; }}

.rcard {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 12px; padding: 28px 32px; margin: 16px 0; }}
.rcard-title {{ font-family: var(--font-display); font-size: 1.05rem; font-weight: 600; color: {C["ink"]}; margin: 0 0 20px; padding-bottom: 14px; border-bottom: 1px solid {C["border"]}; }}
.rfield {{ margin-bottom: 16px; }}
.rfield:last-child {{ margin-bottom: 0; }}
.rfield-label {{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: {C["a500"]}; margin-bottom: 4px; }}
.rfield-val {{ color: {C["ink2"]}; font-size: 0.92rem; line-height: 1.75; }}

.ditem {{ display: flex; align-items: baseline; gap: 12px; padding: 9px 0; border-bottom: 1px solid {C["border"]}; color: {C["ink2"]}; font-size: 0.9rem; line-height: 1.65; }}
.ditem:last-child {{ border-bottom: none; }}
.dnum {{ flex-shrink: 0; width: 22px; height: 22px; border-radius: 6px; background: {C["a50"]}; color: {C["a500"]}; font-size: 0.7rem; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }}

.sim {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; transition: box-shadow 0.25s ease, border-color 0.25s ease; }}
.sim:hover {{ border-color: {C["a200"]}; box-shadow: 0 2px 12px {rgba(C["ink"], 0.04)}; }}
.sim-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.sim-id {{ font-family: var(--font-display); font-weight: 600; font-size: 0.95rem; color: {C["ink"]}; }}
.sim-pct {{ font-family: var(--font-display); font-weight: 700; font-size: 1rem; color: {C["a500"]}; }}
.sim-bar {{ width: 100%; height: 4px; background: {C["border"]}; border-radius: 4px; overflow: hidden; margin-bottom: 12px; }}
.sim-fill {{ height: 100%; border-radius: 4px; background: {C["a400"]}; }}
.sim-body {{ color: {C["sub"]}; font-size: 0.88rem; line-height: 1.7; margin-bottom: 8px; }}
.sim-tags {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.tag {{ padding: 3px 10px; background: {C["bg_warm"]}; border: 1px solid {C["border"]}; border-radius: 6px; font-size: 0.75rem; color: {C["sub"]}; }}

div[data-baseweb="textarea"] textarea {{ background: {C["card"]} !important; color: {C["ink"]} !important; border: 1px solid {C["border"]} !important; border-radius: 10px !important; font-size: 0.92rem !important; line-height: 1.7 !important; padding: 14px 16px !important; }}
div[data-baseweb="textarea"] textarea:focus {{ border-color: {C["a400"]} !important; box-shadow: 0 0 0 3px {rgba(C["a400"], 0.08)} !important; }}

[data-testid="stSlider"] label {{ color: {C["sub"]} !important; font-weight: 500 !important; font-size: 0.88rem !important; }}

.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {{ background: {C["a400"]} !important; color: #FFFFFF !important; font-weight: 600 !important; font-size: 0.92rem !important; border: none !important; border-radius: 10px !important; padding: 10px 32px !important; transition: all 0.2s ease !important; box-shadow: 0 1px 3px {rgba(C["a400"], 0.2)} !important; }}
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {{ background: {C["a500"]} !important; box-shadow: 0 2px 8px {rgba(C["a400"], 0.25)} !important; }}
.stButton > button:not([kind="primary"]), button[data-testid="stBaseButton-secondary"] {{ background: {C["card"]} !important; color: {C["ink2"]} !important; border: 1px solid {C["border"]} !important; border-radius: 10px !important; font-weight: 500 !important; }}
.stButton > button:not([kind="primary"]):hover, button[data-testid="stBaseButton-secondary"]:hover {{ border-color: {C["border_d"]} !important; background: {C["bg_warm"]} !important; }}

[data-testid="stExpander"] {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 10px; }}
[data-testid="stExpander"] summary {{ color: {C["sub"]} !important; }}
[data-testid="stAlert"] {{ border-radius: 10px !important; }}
hr {{ border-color: {C["border"]} !important; }}
[data-testid="stCaption"] {{ color: {C["muted"]} !important; }}

.rpill {{ display: inline-flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }}
.rpill-high {{ background: {rgba(C["s4"], 0.08)}; color: {C["s4"]}; border: 1px solid {rgba(C["s4"], 0.2)}; }}
.rpill-mid {{ background: {rgba(C["s2"], 0.08)}; color: {C["s2"]}; border: 1px solid {rgba(C["s2"], 0.18)}; }}
.rpill-low {{ background: {rgba(C["s1"], 0.12)}; color: {C["a600"]}; border: 1px solid {rgba(C["s1"], 0.3)}; }}

[data-testid="stSlider"][data-testid] {{ opacity: 0.85; }}
div[data-testid="stSlider"] > div > div > div {{ font-size: 0.78rem !important; }}

.upload-info {{ background: {C["bg_warm"]}; border: 1px solid {C["border"]}; border-radius: 10px; padding: 16px 20px; margin: 12px 0; font-size: 0.85rem; color: {C["sub"]}; line-height: 1.7; }}
.upload-info code {{ background: {rgba(C["a400"], 0.08)}; color: {C["a600"]}; padding: 1px 6px; border-radius: 4px; font-size: 0.82rem; }}
.upload-stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 10px 0; }}
.upload-stat {{ background: {C["card"]}; border: 1px solid {C["border"]}; border-radius: 8px; padding: 10px 16px; font-size: 0.82rem; color: {C["sub"]}; }}
.upload-stat strong {{ color: {C["ink"]}; font-weight: 600; }}

.alert-bar {{ padding: 10px 16px; border-radius: 8px; font-size: 0.84rem; font-weight: 500; margin: 8px 0; }}
.alert-bar.danger {{ background: {rgba(C["s4"], 0.08)}; color: {C["s4"]}; border: 1px solid {rgba(C["s4"], 0.18)}; }}
.alert-bar.warn {{ background: {rgba(C["s2"], 0.08)}; color: {C["a600"]}; border: 1px solid {rgba(C["s2"], 0.15)}; }}

.foot {{ text-align: center; padding: 28px 0 12px; margin-top: 40px; border-top: 1px solid {C["border"]}; color: {C["faint"]}; font-size: 0.76rem; }}
</style>
""",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
#  Data helpers
# ═══════════════════════════════════════════════════════════

@st.cache_data
def load_source_df() -> pd.DataFrame:
    if not DATA_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(DATA_PATH)
    if df.empty:
        return df
    df = df.rename(columns=lambda col: str(col).strip())
    if "case_id" not in df.columns:
        df["case_id"] = df.index.astype(int)
    if "event_keyword" not in df.columns:
        df["event_keyword"] = ""
    if "abstract" not in df.columns:
        df["abstract"] = ""
    if "degree_of_inj_x" in df.columns:
        severity = pd.to_numeric(df["degree_of_inj_x"], errors="coerce").fillna(2).clip(1, 4).astype(int)
        df["severity_level"] = severity
    if "date" in df.columns:
        df["parsed_date"] = pd.to_datetime(df["date"], errors="coerce")
    return df




def infer_trade(event_keyword: str, abstract: str) -> str:
    text = f"{event_keyword} {abstract}".lower()
    if any(k in text for k in ["elect", "arc", "busbar", "lockout"]):
        return "电气作业"
    if any(k in text for k in ["ladder", "roof", "scaffold", "fall"]):
        return "高处作业"
    if any(k in text for k in ["weld", "burn", "hot work"]):
        return "焊接热作"
    if any(k in text for k in ["trench", "excavat", "collapse"]):
        return "土方开挖"
    if any(k in text for k in ["forklift", "truck", "vehicle"]):
        return "运输机械"
    return "综合施工"


def infer_hazard(event_keyword: str, abstract: str) -> str:
    text = f"{event_keyword} {abstract}".lower()
    if any(k in text for k in ["fall", "ladder", "scaffold"]):
        return "高处坠落"
    if any(k in text for k in ["elect", "arc", "shock"]):
        return "触电/电弧"
    if any(k in text for k in ["struck", "hit", "falling object"]):
        return "物体打击"
    if any(k in text for k in ["caught", "machine", "roller", "blade"]):
        return "机械卷入"
    if any(k in text for k in ["collapse", "trench"]):
        return "坍塌掩埋"
    if any(k in text for k in ["fire", "explosion", "burn"]):
        return "火灾爆燃"
    return "其他风险"


def top_root_cause(df: pd.DataFrame) -> Optional[str]:
    if "event_keyword" not in df.columns:
        return None
    tokens: List[str] = []
    for raw in df["event_keyword"].dropna().astype(str).head(20000):
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        tokens.extend(parts[:3])
    if not tokens:
        return None
    return pd.Series(tokens).value_counts().index[0]


def climate_impact(temp_c: float, wind_speed: float) -> float:
    temp_score = max(0.0, temp_c - 25.0) / 15.0
    wind_score = wind_speed / 15.0
    return max(0.0, min(1.0, (temp_score + wind_score) / 2.0))


def risk_score(severity_level: int, temp_c: float, wind_speed: float) -> float:
    severity_norm = (severity_level - 1) / 3.0
    score_01 = 0.7 * severity_norm + 0.3 * climate_impact(temp_c, wind_speed)
    return round(max(0.0, min(1.0, score_01)) * 100.0, 1)


def risk_band(score_100: float) -> str:
    if score_100 >= 75:
        return "高风险"
    if score_100 >= 45:
        return "中风险"
    return "低风险"


def rpill_cls(score_100: float) -> str:
    if score_100 >= 75:
        return "rpill-high"
    if score_100 >= 45:
        return "rpill-mid"
    return "rpill-low"


def get_case_ids(cases: List[Dict]) -> List[int]:
    ids: List[int] = []
    for case in cases:
        try:
            ids.append(int(case.get("case_id")))
        except Exception:
            continue
    return ids


TRADE_FORM_CONFIG: Dict[str, List[Dict]] = {
    "高处作业": [
        {"id": "platform_type", "label": "作业平台类型", "type": "select", "options": ["脚手架", "移动平台", "吊篮", "梯子", "屋面临边"], "default": "脚手架"},
        {"id": "edge_protection", "label": "临边防护状态", "type": "select", "options": ["完善", "部分缺失", "未设置"], "default": "完善"},
        {"id": "anchor_point", "label": "安全带挂点类型", "type": "select", "options": ["已验收固定锚点", "临时锚点", "无可靠锚点"], "default": "已验收固定锚点"},
        {"id": "scaffold_acceptance", "label": "脚手架验收状态", "type": "select", "options": ["已验收", "待验收", "不涉及"], "default": "已验收"},
        {"id": "exposure_env", "label": "作业面暴露环境", "type": "select", "options": ["室内", "室外普通风环境", "室外高风环境"], "default": "室外普通风环境"},
    ],
    "电气作业": [
        {"id": "voltage_level", "label": "电压等级", "type": "select", "options": ["低压(<1kV)", "高压(>=1kV)"], "default": "低压(<1kV)"},
        {"id": "live_work", "label": "是否带电作业", "type": "select", "options": ["否", "是"], "default": "否"},
        {"id": "loto_status", "label": "LOTO 执行状态", "type": "select", "options": ["已执行", "部分执行", "未执行"], "default": "已执行"},
        {"id": "insulation_test", "label": "绝缘检测状态", "type": "select", "options": ["合格", "未检测", "不合格"], "default": "合格"},
        {"id": "confined_space", "label": "是否受限空间", "type": "select", "options": ["否", "是"], "default": "否"},
    ],
    "焊接热作": [
        {"id": "permit_status", "label": "动火票状态", "type": "select", "options": ["已审批", "审批中", "未办理"], "default": "已审批"},
        {"id": "combustible_radius", "label": "可燃物清理半径 (m)", "type": "number", "min": 0.0, "max": 30.0, "step": 0.5, "default": 8.0},
        {"id": "fire_watch", "label": "监火人配置", "type": "select", "options": ["已配置", "临时兼任", "未配置"], "default": "已配置"},
        {"id": "gas_detection", "label": "气体检测状态", "type": "select", "options": ["合格", "未检测", "超限"], "default": "合格"},
        {"id": "extinguisher_status", "label": "灭火器材状态", "type": "select", "options": ["齐全可用", "数量不足", "失效"], "default": "齐全可用"},
    ],
    "土方开挖": [
        {"id": "excavation_depth", "label": "开挖深度 (m)", "type": "number", "min": 0.0, "max": 30.0, "step": 0.5, "default": 3.0},
        {"id": "soil_type", "label": "土质类型", "type": "select", "options": ["一般土", "砂土", "软土/回填土", "岩土混合"], "default": "一般土"},
        {"id": "support_status", "label": "支护状态", "type": "select", "options": ["已支护", "局部支护", "未支护"], "default": "已支护"},
        {"id": "pipeline_scan", "label": "地下管线探明状态", "type": "select", "options": ["已探明并标识", "部分探明", "未探明"], "default": "已探明并标识"},
        {"id": "drainage_status", "label": "排水/积水状态", "type": "select", "options": ["良好", "一般", "积水明显"], "default": "良好"},
    ],
    "运输机械": [
        {"id": "vehicle_type", "label": "车辆/设备类型", "type": "select", "options": ["叉车", "自卸车", "混凝土车", "挖机/装载机", "其他"], "default": "叉车"},
        {"id": "reverse_alarm", "label": "倒车报警状态", "type": "select", "options": ["正常", "故障", "无此装置"], "default": "正常"},
        {"id": "separation_status", "label": "人车分流状态", "type": "select", "options": ["完善", "部分分流", "未分流"], "default": "完善"},
        {"id": "speed_control", "label": "限速管控状态", "type": "select", "options": ["已限速并执行", "已限速未执行", "未限速"], "default": "已限速并执行"},
        {"id": "lighting_status", "label": "夜间照明状态", "type": "select", "options": ["充足", "一般", "不足"], "default": "充足"},
    ],
    "起重吊装": [
        {"id": "load_ratio", "label": "额定载荷利用率 (%)", "type": "slider", "min": 10, "max": 120, "step": 5, "default": 60},
        {"id": "rigging_check", "label": "吊索具检查状态", "type": "select", "options": ["合格", "待复检", "不合格"], "default": "合格"},
        {"id": "certified_crew", "label": "司索/指挥持证情况", "type": "select", "options": ["齐全", "部分缺失", "缺失"], "default": "齐全"},
        {"id": "lifting_plan", "label": "吊装方案状态", "type": "select", "options": ["专项方案已审批", "有方案未审批", "无专项方案"], "default": "专项方案已审批"},
        {"id": "overhead_obstacle", "label": "上方障碍物状态", "type": "select", "options": ["无障碍", "有可控障碍", "有高风险障碍"], "default": "无障碍"},
    ],
    "拆除作业": [
        {"id": "demolition_method", "label": "拆除方法", "type": "select", "options": ["机械拆除", "人工拆除", "爆破拆除", "混合拆除"], "default": "机械拆除"},
        {"id": "temporary_support", "label": "临时支撑状态", "type": "select", "options": ["完善", "部分设置", "未设置"], "default": "完善"},
        {"id": "energy_isolation", "label": "断电断气隔离状态", "type": "select", "options": ["已隔离", "部分隔离", "未隔离"], "default": "已隔离"},
        {"id": "warning_zone", "label": "落物警戒区状态", "type": "select", "options": ["已封控", "部分封控", "未封控"], "default": "已封控"},
        {"id": "adjacent_distance", "label": "邻近结构距离 (m)", "type": "number", "min": 0.0, "max": 50.0, "step": 0.5, "default": 5.0},
    ],
    "综合施工": [
        {"id": "cross_operation", "label": "交叉作业强度", "type": "select", "options": ["低", "中", "高"], "default": "中"},
        {"id": "temp_power", "label": "临时用电状态", "type": "select", "options": ["规范", "一般", "混乱"], "default": "规范"},
        {"id": "channel_status", "label": "通道畅通状态", "type": "select", "options": ["畅通", "局部拥堵", "堵塞"], "default": "畅通"},
        {"id": "supervision_presence", "label": "现场监护到岗状态", "type": "select", "options": ["到岗", "间断到岗", "未到岗"], "default": "到岗"},
        {"id": "key_risk_notes", "label": "关键风险补充说明", "type": "textarea", "default": "", "height": 88},
    ],
}


def render_trade_specific_form(trade_type: str) -> Dict[str, str]:
    fields = TRADE_FORM_CONFIG.get(trade_type, [])
    values: Dict[str, str] = {}
    if not fields:
        return values

    st.markdown(
        f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.92rem;color:{C["ink2"]};margin:10px 0 8px;">{trade_type}专项信息</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)

    for idx, field in enumerate(fields):
        col = c1 if idx % 2 == 0 else c2
        field_id = str(field.get("id", f"field_{idx}"))
        label = str(field.get("label", field_id))
        widget_type = str(field.get("type", "text"))
        key = f"trade_{trade_type}_{field_id}"

        with col:
            if widget_type == "select":
                options = [str(item) for item in field.get("options", [])]
                if not options:
                    options = [""]
                default = str(field.get("default", options[0]))
                if default not in options:
                    default = options[0]
                value = st.selectbox(label, options, index=options.index(default), key=key)
            elif widget_type == "number":
                min_val = float(field.get("min", 0.0))
                max_val = float(field.get("max", 100.0))
                step = float(field.get("step", 1.0))
                default = float(field.get("default", min_val))
                value = st.number_input(label, min_value=min_val, max_value=max_val, value=default, step=step, key=key)
            elif widget_type == "slider":
                min_val = int(field.get("min", 0))
                max_val = int(field.get("max", 100))
                step = int(field.get("step", 1))
                default = int(field.get("default", min_val))
                value = st.slider(label, min_val, max_val, default, step, key=key)
            elif widget_type == "textarea":
                default = str(field.get("default", ""))
                height = int(field.get("height", 90))
                value = st.text_area(label, value=default, height=height, key=key)
            else:
                default = str(field.get("default", ""))
                value = st.text_input(label, value=default, key=key)

        values[label] = str(value).strip()

    return values


def format_trade_inputs(trade_type: str, trade_inputs: Dict[str, str]) -> str:
    lines = [f"- {key}: {value}" for key, value in trade_inputs.items() if str(value).strip()]
    if not lines:
        return f"工种专项信息（{trade_type}）：无"
    return f"工种专项信息（{trade_type}）：\n" + "\n".join(lines)


def _compress_categories(series: pd.Series, keep_top_n: int, other_name: str) -> pd.Series:
    top = series.value_counts().head(keep_top_n).index
    return series.where(series.isin(top), other_name)


def sensor_alerts(temp_c: float, wind_speed: float, humidity: float) -> List[str]:
    alerts = []
    if temp_c > 35:
        alerts.append(f"高温预警：当前温度 {temp_c}°C 超过 35°C，高温中暑风险显著升高，建议调整作业时间")
    elif temp_c < 0:
        alerts.append(f"低温预警：当前温度 {temp_c}°C 低于 0°C，路面结冰与材料脆裂风险上升")
    if wind_speed > 10:
        alerts.append(f"强风预警：当前风速 {wind_speed} m/s 超过 10 m/s，应暂停高处作业与起重吊装")
    if humidity > 85:
        alerts.append(f"高湿预警：当前湿度 {humidity}%，湿滑导致的滑倒/触电风险增加")
    return alerts


# ═══════════════════════════════════════════════════════════
#  Sensor Gauges
# ═══════════════════════════════════════════════════════════

TEMP_STEPS = [
    {"range": [-10, 10], "color": C["a50"]},
    {"range": [10, 25],  "color": C["a100"]},
    {"range": [25, 35],  "color": C["a200"]},
    {"range": [35, 45],  "color": C["a300"]},
]
WIND_STEPS = [
    {"range": [0, 5],   "color": C["a50"]},
    {"range": [5, 10],  "color": C["a100"]},
    {"range": [10, 15], "color": C["a200"]},
    {"range": [15, 20], "color": C["a300"]},
]
HUMID_STEPS = [
    {"range": [0, 30],   "color": C["a50"]},
    {"range": [30, 60],  "color": C["a100"]},
    {"range": [60, 80],  "color": C["a200"]},
    {"range": [80, 100], "color": C["a300"]},
]


def render_gauge(value: float, title: str, min_val: float, max_val: float, unit: str, steps: list, height: int = 210) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": f" {unit}", "font": {"size": 26, "family": "Source Serif 4, Georgia, serif", "color": C["ink"]}},
        title={"text": title, "font": {"size": 13, "family": "Noto Sans SC, sans-serif", "color": C["muted"]}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickcolor": C["border_d"], "tickfont": {"size": 10, "color": C["muted"]}, "dtick": (max_val - min_val) / 5},
            "bar": {"color": C["a400"], "thickness": 0.25},
            "bgcolor": C["bg_warm"], "borderwidth": 0, "steps": steps,
            "threshold": {"line": {"color": C["a700"], "width": 3}, "thickness": 0.75, "value": value},
        },
    ))
    fig.update_layout(height=height, margin=dict(l=24, r=24, t=48, b=4), paper_bgcolor="rgba(0,0,0,0)", font={"family": "Noto Sans SC, sans-serif", "color": C["ink2"]})
    return fig


# ═══════════════════════════════════════════════════════════
#  Sankey
# ═══════════════════════════════════════════════════════════

def render_sankey(df: pd.DataFrame) -> None:
    required_cols = {"event_keyword", "abstract", "severity_level"}
    if not required_cols.issubset(set(df.columns)):
        st.info("缺少必要字段，已隐藏关系流图。")
        return
    work = df.copy()
    work["trade_group"] = [infer_trade(k, a) for k, a in zip(work["event_keyword"], work["abstract"])]
    work["hazard_group"] = [infer_hazard(k, a) for k, a in zip(work["event_keyword"], work["abstract"])]
    work["trade_group"] = _compress_categories(work["trade_group"], keep_top_n=5, other_name="其他工种")
    work["hazard_group"] = _compress_categories(work["hazard_group"], keep_top_n=6, other_name="其他风险")
    trade_nodes = sorted(work["trade_group"].unique().tolist())
    hazard_nodes = sorted(work["hazard_group"].unique().tolist())
    severity_nodes = ["严重度1", "严重度2", "严重度3", "严重度4"]
    nodes = trade_nodes + hazard_nodes + severity_nodes
    node_to_index = {name: idx for idx, name in enumerate(nodes)}
    min_link_count = max(3, int(len(work) * 0.005))
    source, target, value, link_colors = [], [], [], []
    trade_hazard = work.groupby(["trade_group", "hazard_group"]).size().reset_index(name="count")
    trade_hazard = trade_hazard[trade_hazard["count"] >= min_link_count]
    for _, row in trade_hazard.iterrows():
        source.append(node_to_index[row["trade_group"]]); target.append(node_to_index[row["hazard_group"]]); value.append(int(row["count"])); link_colors.append(rgba(C["a200"], 0.45))
    hazard_severity = work.groupby(["hazard_group", "severity_level"]).size().reset_index(name="count")
    filtered_hazard = hazard_severity[hazard_severity["count"] >= min_link_count].copy()
    for level in range(1, 5):
        if int(level) in set(filtered_hazard["severity_level"].astype(int)):
            continue
        candidate = hazard_severity[hazard_severity["severity_level"] == level]
        if candidate.empty:
            continue
        filtered_hazard = pd.concat([filtered_hazard, candidate.nlargest(1, "count")], ignore_index=True)
    for _, row in filtered_hazard.iterrows():
        severity_key = f"严重度{int(row['severity_level'])}"
        source.append(node_to_index[row["hazard_group"]]); target.append(node_to_index[severity_key]); value.append(int(row["count"]))
        link_colors.append(rgba(SEVERITY_CFG[int(row["severity_level"])]["color"], 0.35))
    if not source:
        st.info("可视化数据不足，已隐藏关系流图。")
        return
    node_colors = [C["a300"]] * len(trade_nodes) + [C["a200"]] * len(hazard_nodes) + [C["s1"], C["s2"], C["s3"], C["s4"]]
    fig = go.Figure(data=[go.Sankey(arrangement="snap", textfont=dict(size=13, color=C["ink2"], family="Noto Sans SC, Microsoft YaHei, sans-serif"),
        node=dict(label=nodes, color=node_colors, pad=14, thickness=14, line=dict(width=0), hovertemplate="%{label}<extra></extra>"),
        link=dict(source=source, target=target, value=value, color=link_colors, hovertemplate="流量: %{value}<extra></extra>"))])
    fig.update_layout(height=460, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=13, color=C["ink2"], family="Noto Sans SC, Microsoft YaHei, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("图中只保留主要流向，极小流量已合并/过滤以保持可读性。")


# ═══════════════════════════════════════════════════════════
#  Time Trend Charts
# ═══════════════════════════════════════════════════════════

def render_monthly_trend(df: pd.DataFrame) -> None:
    if "parsed_date" not in df.columns:
        return
    work = df.dropna(subset=["parsed_date"]).copy()
    if work.empty:
        return
    work["ym"] = work["parsed_date"].dt.to_period("M").dt.to_timestamp()
    monthly = work.groupby("ym").size().reset_index(name="count")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["ym"], y=monthly["count"], mode="lines+markers",
        line=dict(color=C["a400"], width=2), marker=dict(size=5, color=C["a400"]),
        hovertemplate="%{x|%Y-%m}: %{y} 起<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=40, r=16, t=8, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="", gridcolor=C["border"], tickfont=dict(size=11, color=C["muted"])),
        yaxis=dict(title=dict(text="事故数量", font=dict(size=12, color=C["sub"])), gridcolor=C["border"], tickfont=dict(size=11, color=C["muted"])),
        font=dict(family="Noto Sans SC, sans-serif", color=C["ink2"]))
    st.plotly_chart(fig, use_container_width=True)


def render_trade_month_heatmap(df: pd.DataFrame) -> None:
    if "parsed_date" not in df.columns or "event_keyword" not in df.columns:
        return
    work = df.dropna(subset=["parsed_date"]).copy()
    if work.empty:
        return
    work["month"] = work["parsed_date"].dt.month
    work["trade"] = [infer_trade(k, a) for k, a in zip(work["event_keyword"], work["abstract"])]
    pivot = work.groupby(["trade", "month"]).size().reset_index(name="count")
    matrix = pivot.pivot(index="trade", columns="month", values="count").fillna(0)
    month_labels = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
    all_months = list(range(1, 13))
    for m in all_months:
        if m not in matrix.columns:
            matrix[m] = 0
    matrix = matrix[all_months]
    fig = go.Figure(data=go.Heatmap(
        z=matrix.values, x=month_labels, y=matrix.index.tolist(),
        colorscale=[[0, C["a50"]], [0.3, C["a100"]], [0.6, C["a200"]], [0.85, C["a300"]], [1.0, C["a500"]]],
        hovertemplate="工种: %{y}<br>月份: %{x}<br>事故数: %{z}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=80, r=16, t=8, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11, color=C["muted"])), yaxis=dict(tickfont=dict(size=11, color=C["muted"])),
        font=dict(family="Noto Sans SC, sans-serif", color=C["ink2"]))
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
#  Environment Correlation Chart
# ═══════════════════════════════════════════════════════════

def render_env_correlation(df: pd.DataFrame) -> None:
    cols_needed = {"temp", "wind_speed", "severity_level"}
    if not cols_needed.issubset(set(df.columns)):
        return
    work = df[["temp", "wind_speed", "severity_level"]].dropna().copy()
    if len(work) < 50:
        return
    work["temp_k"] = pd.to_numeric(work["temp"], errors="coerce")
    work = work.dropna(subset=["temp_k"])
    if work.empty:
        return
    work["temp_c"] = work["temp_k"] - 273.15
    work["sev_label"] = work["severity_level"].map({1: "1-轻微", 2: "2-一般", 3: "3-严重", 4: "4-重大"})
    sev_colors = {f"{i}-{SEVERITY_CFG[i]['label']}": SEVERITY_CFG[i]["color"] for i in range(1, 5)}

    tc, wc = st.columns(2)
    with tc:
        fig_t = go.Figure()
        for sev_label, color in sev_colors.items():
            subset = work[work["sev_label"] == sev_label]
            if subset.empty:
                continue
            fig_t.add_trace(go.Box(y=subset["temp_c"], name=sev_label, marker_color=color, line_color=color))
        fig_t.update_layout(height=280, margin=dict(l=40, r=16, t=8, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
            yaxis=dict(title=dict(text="温度 (°C)", font=dict(size=11, color=C["sub"])), gridcolor=C["border"], tickfont=dict(size=10, color=C["muted"])),
            xaxis=dict(tickfont=dict(size=10, color=C["muted"])),
            font=dict(family="Noto Sans SC, sans-serif", color=C["ink2"]))
        st.plotly_chart(fig_t, use_container_width=True)
        st.caption("温度（开尔文转摄氏）按严重度分组")

    with wc:
        fig_w = go.Figure()
        for sev_label, color in sev_colors.items():
            subset = work[work["sev_label"] == sev_label]
            if subset.empty:
                continue
            fig_w.add_trace(go.Box(y=subset["wind_speed"], name=sev_label, marker_color=color, line_color=color))
        fig_w.update_layout(height=280, margin=dict(l=40, r=16, t=8, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
            yaxis=dict(title=dict(text="风速 (m/s)", font=dict(size=11, color=C["sub"])), gridcolor=C["border"], tickfont=dict(size=10, color=C["muted"])),
            xaxis=dict(tickfont=dict(size=10, color=C["muted"])),
            font=dict(family="Noto Sans SC, sans-serif", color=C["ink2"]))
        st.plotly_chart(fig_w, use_container_width=True)
        st.caption("风速按严重度分组")


# ═══════════════════════════════════════════════════════════
#  Layout
# ═══════════════════════════════════════════════════════════

apply_theme()
df = load_source_df()

# ─── Hero ───
st.markdown(
    f"""
<div class="hero">
    <div class="hero-title">工程安全智能决策助手</div>
    <div class="hero-sub">
        基于 RAG 检索增强与 DeepSeek 大模型的施工安全研判系统<br>
        覆盖 53,000+ 历史事故案例，支持事前风险预判与实时预警
    </div>
    <div class="hero-divider"></div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Status ───
_, sc = st.columns([5, 1])
with sc:
    if FAISS_INDEX_PATH.exists():
        st.markdown('<span class="pill pill-ok">● 索引就绪</span>', unsafe_allow_html=True)
        st.markdown('<span class="pill pill-warn">○ 未就绪</span>', unsafe_allow_html=True)

if not FAISS_INDEX_PATH.exists():
    if st.button("初始化索引"):
        with st.spinner("正在构建 FAISS 索引…"):
            try:
                build_index(device="cpu")
                st.success("索引构建完成，请刷新页面。")
            except Exception as exc:
                st.error(f"索引构建失败: {exc}")

with st.expander("数据管理：上传补充数据 / 重建索引"):
    st.markdown(
        '<div class="upload-info">'
        f'上传 CSV 文件以补充事故数据库。文件必须包含 <code>{TEXT_COL}</code>（事故描述）列，'
        '建议同时包含 <code>event_keyword</code>（关键词）和 <code>degree_of_inj_x</code>（严重度 1-4）列。'
        '</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("选择 CSV 文件", type=["csv"], help=f"必须包含 {TEXT_COL} 列")
    if uploaded_file is not None:
        try:
            new_df = pd.read_csv(uploaded_file)
            new_df = new_df.rename(columns=lambda col: str(col).strip())
        except Exception as exc:
            st.error(f"无法读取文件: {exc}")
            new_df = None
        if new_df is not None:
            if TEXT_COL not in new_df.columns:
                st.error(f"上传的文件缺少必须列 **{TEXT_COL}**。当前列：{', '.join(new_df.columns.tolist())}")
            else:
                empty_mask = new_df[TEXT_COL].astype(str).str.strip().isin(["", "nan"])
                valid_count = int((~empty_mask).sum())
                existing_count = len(df) if not df.empty else 0
                matched_cols = [c for c in KEEP_COLS if c in new_df.columns]
                missing_cols = [c for c in KEEP_COLS if c not in new_df.columns and c != "case_id"]
                st.markdown(f'<div class="upload-stats"><div class="upload-stat">上传行数 <strong>{len(new_df):,}</strong></div><div class="upload-stat">有效记录 <strong>{valid_count:,}</strong></div><div class="upload-stat">现有记录 <strong>{existing_count:,}</strong></div><div class="upload-stat">匹配列数 <strong>{len(matched_cols)}/{len(KEEP_COLS)}</strong></div></div>', unsafe_allow_html=True)
                if missing_cols:
                    st.caption(f"以下可选列在上传文件中缺失，将自动补空：{', '.join(missing_cols)}")
                st.dataframe(new_df.head(5), use_container_width=True, height=200)
                if valid_count == 0:
                    st.warning(f"上传文件中没有有效的 {TEXT_COL} 记录，请检查数据。")
                elif st.button("确认导入并重建索引", type="primary"):
                    try:
                        if DATA_PATH.exists():
                            shutil.copy(DATA_PATH, DATA_PATH.with_suffix(".csv.bak"))
                        new_clean = new_df[~empty_mask].copy()
                        if DATA_PATH.exists():
                            existing_df = pd.read_csv(DATA_PATH)
                            existing_df = existing_df.rename(columns=lambda col: str(col).strip())
                            combined = pd.concat([existing_df, new_clean], ignore_index=True)
                        else:
                            combined = new_clean.copy()
                        before_dedup = len(combined)
                        combined = combined.drop_duplicates(subset=[TEXT_COL], keep="first")
                        dedup_removed = before_dedup - len(combined)
                        combined.to_csv(DATA_PATH, index=False)
                        with st.spinner("正在重建 FAISS 索引…"):
                            build_index(device="cpu")
                        st.cache_data.clear()
                        st.success(f"导入完成！新增 {valid_count} 条（去重 {dedup_removed} 条），共 {len(combined):,} 条。索引已重建。")
                        st.info("请刷新页面以更新看板数据。")
                    except Exception as exc:
                        st.error(f"导入失败: {exc}")
    st.markdown(f'<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:{C["muted"]};font-size:0.82rem;margin-bottom:8px;">如果只需重建索引（不导入新数据）：</div>', unsafe_allow_html=True)
    if st.button("仅重建索引"):
        with st.spinner("正在重建 FAISS 索引…"):
            try:
                build_index(device="cpu"); st.cache_data.clear(); st.success("索引重建完成，请刷新页面。")
            except Exception as exc:
                st.error(f"索引重建失败: {exc}")


# ═══════════════════════════════════════════════════════════
#  Dashboard
# ═══════════════════════════════════════════════════════════

def render_dashboard(df: pd.DataFrame) -> None:
    st.markdown('<div class="sec-rule"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-title">宏观风险看板</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-desc">整体事故规模、主要根因、时间趋势与环境关联分析</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("未读取到数据集，无法展示看板。")
        return

    severity_counts = {}
    if "severity_level" in df.columns:
        severity_counts = df["severity_level"].value_counts().to_dict()
    root_cause = top_root_cause(df)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi"><div class="kpi-label">事故总数</div><div class="kpi-val">{len(df):,}</div><div class="kpi-note">数据集全部记录</div><div class="kpi-bar" style="background:{C["a100"]};"><div style="width:100%;height:100%;background:{C["a400"]};border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
    with k2:
        cause_text = root_cause if root_cause else "—"
        st.markdown(f'<div class="kpi"><div class="kpi-label">最频发根因</div><div class="kpi-val" style="font-size:1.3rem;">{cause_text}</div><div class="kpi-note">基于事件关键词统计</div><div class="kpi-bar" style="background:{C["a100"]};"><div style="width:72%;height:100%;background:{C["a300"]};border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
    with k3:
        severe_count = severity_counts.get(3, 0) + severity_counts.get(4, 0)
        pct = severe_count / max(1, len(df)) * 100
        st.markdown(f'<div class="kpi"><div class="kpi-label">严重/重大事故</div><div class="kpi-val">{severe_count:,}</div><div class="kpi-note">严重度 3–4 级 · {pct:.1f}%</div><div class="kpi-bar" style="background:{C["a100"]};"><div style="width:{pct:.1f}%;height:100%;background:{C["a500"]};border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
    with k4:
        if severity_counts:
            avg_sev = df["severity_level"].mean()
            bar_w = (avg_sev - 1) / 3 * 100
            st.markdown(f'<div class="kpi"><div class="kpi-label">平均严重度</div><div class="kpi-val">{avg_sev:.2f}</div><div class="kpi-note">1 轻微 — 4 重大</div><div class="kpi-bar" style="background:{C["a100"]};"><div style="width:{bar_w:.1f}%;height:100%;background:{C["a400"]};border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="kpi"><div class="kpi-label">平均严重度</div><div class="kpi-val">—</div><div class="kpi-note">无数据</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.95rem;color:{C["ink2"]};margin-bottom:4px;">工种 → 危险源 → 严重度</div>', unsafe_allow_html=True)
    render_sankey(df)

    st.markdown(f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.95rem;color:{C["ink2"]};margin:24px 0 4px;">月度事故趋势</div>', unsafe_allow_html=True)
    render_monthly_trend(df)

    st.markdown(f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.95rem;color:{C["ink2"]};margin:16px 0 4px;">工种-月份事故热力图</div>', unsafe_allow_html=True)
    render_trade_month_heatmap(df)

    st.markdown(f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.95rem;color:{C["ink2"]};margin:16px 0 4px;">环境参数与事故严重度关联</div>', unsafe_allow_html=True)
    render_env_correlation(df)



# ═══════════════════════════════════════════════════════════
#  AI Analysis
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="sec-rule"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="sec-title">事前预判与预警</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sec-desc">仅保留事前风险评估，结合环境传感数据进行实时预警</div>', unsafe_allow_html=True)

# ─── Sensor Panel ───
if "temp_c" not in st.session_state:
    st.session_state["temp_c"] = 25.0
if "wind_speed" not in st.session_state:
    st.session_state["wind_speed"] = 3.0
if "humidity" not in st.session_state:
    st.session_state["humidity"] = 55.0
if "sensor_source" not in st.session_state:
    st.session_state["sensor_source"] = "手动输入"

sensor_header_l, sensor_header_r = st.columns([4, 1.5])
with sensor_header_l:
    st.markdown(f'<div style="font-family:var(--font-display);font-weight:600;font-size:0.95rem;color:{C["ink2"]};margin:8px 0 4px;">环境参数监测</div>', unsafe_allow_html=True)
with sensor_header_r:
    if st.button("从传感器刷新", key="sensor_refresh"):
        reading = read_sensors()
        st.session_state["temp_c"] = reading.temp_c
        st.session_state["wind_speed"] = reading.wind_speed
        st.session_state["humidity"] = reading.humidity_pct
        st.session_state["sensor_source"] = f"传感器 ({reading.source})"
        st.rerun()

source_label = st.session_state["sensor_source"]
is_sensor = "传感器" in source_label
pill_cls = "pill-ok" if is_sensor else "pill-warn"
pill_dot = "●" if is_sensor else "○"
st.markdown(f'<span class="pill {pill_cls}">{pill_dot} {source_label}</span>', unsafe_allow_html=True)

g1, g2, g3 = st.columns(3)
with g1:
    st.plotly_chart(render_gauge(st.session_state["temp_c"], "环境温度", -10, 45, "°C", TEMP_STEPS), use_container_width=True, key="gauge_temp")
    new_temp = st.slider("调节温度 (°C)", -10.0, 45.0, st.session_state["temp_c"], 0.5, key="slider_temp")
    if new_temp != st.session_state["temp_c"]:
        st.session_state["temp_c"] = new_temp; st.session_state["sensor_source"] = "手动输入"; st.rerun()
with g2:
    st.plotly_chart(render_gauge(st.session_state["wind_speed"], "环境风速", 0, 20, "m/s", WIND_STEPS), use_container_width=True, key="gauge_wind")
    new_wind = st.slider("调节风速 (m/s)", 0.0, 20.0, st.session_state["wind_speed"], 0.5, key="slider_wind")
    if new_wind != st.session_state["wind_speed"]:
        st.session_state["wind_speed"] = new_wind; st.session_state["sensor_source"] = "手动输入"; st.rerun()
with g3:
    st.plotly_chart(render_gauge(st.session_state["humidity"], "环境湿度", 0, 100, "%", HUMID_STEPS), use_container_width=True, key="gauge_humid")
    new_humid = st.slider("调节湿度 (%)", 0.0, 100.0, st.session_state["humidity"], 1.0, key="slider_humid")
    if new_humid != st.session_state["humidity"]:
        st.session_state["humidity"] = new_humid; st.session_state["sensor_source"] = "手动输入"; st.rerun()

temp_c = st.session_state["temp_c"]
wind_speed = st.session_state["wind_speed"]
humidity = st.session_state["humidity"]

# ── Sensor Alerts (Change 2) ──
alerts = sensor_alerts(temp_c, wind_speed, humidity)
for alert_text in alerts:
    is_danger = "暂停" in alert_text or "高温" in alert_text
    cls = "danger" if is_danger else "warn"
    st.markdown(f'<div class="alert-bar {cls}">{alert_text}</div>', unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─── Pre-assessment Input Area ───
st.markdown(f'<div style="color:{C["sub"]};font-size:0.88rem;margin-bottom:10px;">填写即将进行的施工作业信息，系统将预判风险等级并给出预防建议。</div>', unsafe_allow_html=True)
fc1, fc2 = st.columns(2)
with fc1:
    trade_type = st.selectbox("工种类型", TRADE_TYPES, key="pre_trade")
    work_height = st.number_input("作业高度 (m)", min_value=0.0, max_value=200.0, value=5.0, step=0.5, key="pre_height")
with fc2:
    shift = st.selectbox("作业时段", ["白天", "夜间"], key="pre_shift")
    new_worker_pct = st.slider("新工人占比 (%)", 0, 100, 20, 5, key="pre_newworker")
trade_specific_inputs = render_trade_specific_form(trade_type)
work_plan = st.text_area("作业计划描述", value="计划在15层外墙进行幕墙安装作业，需要搭设悬挑脚手架，使用电动吊篮运送材料。", height=120, key="pre_plan")

_, bc, _ = st.columns([2.5, 1, 2.5])
with bc:
    start_analysis = st.button("开始预判", type="primary", use_container_width=True)

if start_analysis:
    if not FAISS_INDEX_PATH.exists():
        st.error("未找到 FAISS 索引，请先初始化索引。")
        st.stop()

    if not work_plan.strip():
        st.warning("请先填写作业计划描述。")
        st.stop()

    trade_specific_text = format_trade_inputs(trade_type, trade_specific_inputs)
    query_text = "\n".join(
        [
            f"工种类型：{trade_type}",
            f"作业高度：{work_height} m",
            f"作业时段：{shift}",
            f"新工人占比：{new_worker_pct:.0f}%",
            trade_specific_text,
            f"作业计划描述：{work_plan}",
        ]
    )

    with st.spinner("正在检索历史案例…"):
        try:
            cases = retrieve(query_text, top_k=3, device="cpu")
        except Exception as exc:
            st.error(f"检索失败: {exc}")
            st.stop()

    model_name = os.getenv("DEEPSEEK_MODEL", "").strip() or None
    base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip() or None
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip() or None

    prompt = build_pre_assessment_prompt(
        work_plan=work_plan,
        trade_type=trade_type,
        work_height=work_height,
        shift=shift,
        new_worker_pct=new_worker_pct,
        trade_specific_inputs=trade_specific_inputs,
        temp_c=temp_c,
        wind_speed=wind_speed,
        humidity=humidity,
        cases=cases,
    )

    parsed = None
    fallback_reason = ""
    with st.spinner("Calling DeepSeek analysis..."):
        try:
            response = chat(
                prompt=prompt,
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.0,
                max_tokens=800,
                timeout=20.0,
            )
            parsed = parse_and_validate_pre_assessment(
                response_text=response,
                require_citations=True,
                allowed_case_ids=get_case_ids(cases),
            )
        except Exception as exc:
            fallback_reason = str(exc)

    if parsed is None:
        parsed = build_local_pre_assessment(
            work_plan=work_plan,
            trade_type=trade_type,
            work_height=work_height,
            shift=shift,
            new_worker_pct=new_worker_pct,
            trade_specific_inputs=trade_specific_inputs,
            temp_c=temp_c,
            wind_speed=wind_speed,
            humidity=humidity,
            cases=cases,
        )
        st.warning(f"当前使用离线预判模式。{fallback_reason or '大模型暂不可用。'}")

    rl = int(parsed["risk_level"])
    sev = SEVERITY_CFG.get(rl, SEVERITY_CFG[2])
    score = risk_score(rl, temp_c, wind_speed)
    band = risk_band(score)
    band_cls = rpill_cls(score)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="kpi" style="text-align:center;"><div class="kpi-label">风险等级</div><div class="kpi-val" style="color:{sev["color"]};">{rl}</div><div class="kpi-note">{sev["label"]}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="kpi" style="text-align:center;"><div class="kpi-label">综合风险分</div><div class="kpi-val">{score}</div><div class="kpi-note"><span class="rpill {band_cls}">{band}</span></div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="kpi" style="text-align:center;"><div class="kpi-label">引用案例</div><div class="kpi-val">{len(parsed.get("citations", []))}</div><div class="kpi-note">历史参考</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    hazards_txt = "；".join(parsed.get("potential_hazards", []))
    measures_txt = "；".join(parsed.get("preventive_measures", []))
    ppe_txt = "；".join(parsed.get("required_ppe", []))
    special_txt = "；".join([f"{k}: {v}" for k, v in trade_specific_inputs.items() if str(v).strip()]) or "无"
    cites_txt = ", ".join(str(c) for c in parsed.get("citations", []))
    rationale_txt = parsed.get("rationale", "")

    st.markdown(f"""<div class="rcard">
<div class="rcard-title">事前风险评估报告 <span class="rpill {band_cls}" style="margin-left:10px;">风险等级 {rl}</span></div>
<div class="rfield"><div class="rfield-label">工种专项输入</div><div class="rfield-val">{special_txt}</div></div>
<div class="rfield"><div class="rfield-label">潜在危险源</div><div class="rfield-val">{hazards_txt}</div></div>
<div class="rfield"><div class="rfield-label">预防措施</div><div class="rfield-val">{measures_txt}</div></div>
<div class="rfield"><div class="rfield-label">必需 PPE</div><div class="rfield-val">{ppe_txt}</div></div>
<div class="rfield"><div class="rfield-label">引用案例</div><div class="rfield-val">{cites_txt}</div></div>
<div class="rfield"><div class="rfield-label">评估理由</div><div class="rfield-val">{rationale_txt}</div></div>
</div>""", unsafe_allow_html=True)

    st.markdown(f'<div style="color:{C["muted"]};font-size:0.78rem;margin:6px 0;line-height:1.6;">综合风险分满分 100，按 0.7 × 严重度分 + 0.3 × 气象影响分 计算。判定标准：低 &lt; 45，中 45–74.9，高 ≥ 75。</div>', unsafe_allow_html=True)

    # ── Similar Cases ──
    st.markdown(f'<div class="sec-title" style="margin-top:28px;">最相似历史事件</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-desc">基于语义检索匹配的 Top 3 案例</div>', unsafe_allow_html=True)

    for i, case in enumerate(cases, start=1):
        similarity = float(case.get("score", 0.0))
        percentage = max(0.0, min(100.0, (similarity + 1.0) * 50.0))
        keyword_match = max(0.0, min(100.0, float(case.get("keyword_score", 0.0)) * 100.0))
        st.markdown(f"""<div class="sim">
    <div class="sim-top"><span class="sim-id">#{i} · 案例 {case.get("case_id")}</span><span class="sim-pct">{percentage:.1f}%</span></div>
    <div class="sim-bar"><div class="sim-fill" style="width:{percentage:.1f}%"></div></div>
    <div class="sim-body">{case.get("abstract", "")}</div>
    <div class="sim-tags"><span class="tag">{case.get("event_keyword", "")}</span><span class="tag">关键词匹配 {keyword_match:.1f}%</span></div>
</div>""", unsafe_allow_html=True)

render_dashboard(df)

# ─── Footer ───
st.markdown('<div class="foot">工程安全智能决策助手 · Powered by RAG + DeepSeek · Built with Streamlit</div>', unsafe_allow_html=True)
