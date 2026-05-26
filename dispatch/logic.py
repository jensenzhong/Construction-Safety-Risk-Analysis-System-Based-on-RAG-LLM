from typing import Dict, List

DISPATCH_MAP = {
    1: [
        "记录事件并通知班组长",
        "72 小时内完成安全复盘",
    ],
    2: [
        "安排现场医疗检查",
        "通知专职安全员到场",
        "检查涉事设备与作业区域",
    ],
    3: [
        "立即派驻安全员并现场管控",
        "临时停止相关作业",
        "启动事故报告与根因复盘",
    ],
    4: [
        "启动应急响应并联系急救",
        "立即下达停工令",
        "调度安全总监与现场指挥到场",
    ],
}


def _resolve_severity_level(severity_level=None, severity=None) -> int:
    value = severity_level if severity_level is not None else severity
    try:
        return int(value)
    except Exception:
        return -1


def build_dispatch(severity_level=None, severity=None) -> Dict:
    resolved = _resolve_severity_level(severity_level=severity_level, severity=severity)
    tasks: List[str] = DISPATCH_MAP.get(resolved, ["严重度未知：请人工复核并分派措施"])
    return {
        "severity_level": resolved,
        "tasks": tasks,
    }
