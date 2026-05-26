# 功能优先级补完计划（DeepSeek优先，先功能后UI）

## 摘要
目标是先完成你图片里优先级最高的两件事：
1. 阶段一：把“只输出1-4标签”的流程升级为“结构化信息抽取 + 思维链研判输出”；
2. 阶段二：补上可运行的轻量级 PSM 因果分析（先用合成数据，后续可替换真实 inspection 数据）。

本计划不包含 UI 视觉改造（按你的要求后置），仅做功能链路与脚本完善。

## 当前未完成项（按优先级）
1. `main.py` 仍是旧版 OpenAI 风格标签预测脚本，未实现结构化信息抽取。
2. DeepSeek 配置虽在 `app.py/llm/client.py` 中有入口，但缺少“严格的 DeepSeek-only 策略 + 缺钥匙时明确报错规范”。
3. RAG 推理输出尚未统一为你要求的四维结构化字段（严重度、核心危险源、管理漏洞、改进建议）。
4. PSM 因果分析脚本尚未落地（当前仓库无 inspection/complaint 真实表，需先合成演示版）。
5. 缺少阶段性验收脚本与结果报告模板（可复查性不足）。

## 实施范围与顺序

## Phase 0（前置约束，半天）
- 统一 API 政策：仅 DeepSeek，不再使用 OpenAI 专有命名作为主路径。
- 凭据策略：仅环境变量（你已确认）。
- 失败策略：若找不到 `DEEPSEEK_API_KEY`，立即 fail-fast，错误文案明确提示“请提供 DeepSeek API Key”。

## Phase 1（最高优先）：结构化信息抽取替代传统预测
### 1.1 `main.py` 重构为信息抽取批处理脚本
- 输入：任意文本列（默认 `abstract`）。
- 输出：JSON Lines / CSV，字段固定为：
  - `severity_level` (1-4)
  - `core_hazards` (list[str])
  - `management_gaps` (list[str])
  - `improvement_actions` (list[str])
  - `confidence` (0-1)
  - `reasoning_summary` (短文本)
- 实现要点：
  - 使用 DeepSeek OpenAI-compatible client（复用 `llm/client.py`，不再在 `main.py` 直接写 OpenAI 旧SDK调用）。
  - 强制 JSON schema 校验：模型输出非JSON时自动一次重试；仍失败则记录 `parse_error`。
  - CLI 参数化：
    - `--input-csv`
    - `--text-col`
    - `--output-path`
    - `--model`（默认 `deepseek-chat`）
    - `--max-rows`（便于小样本试跑）

### 1.2 RAG 链路输出与阶段一 schema 对齐
- `rag/prompting.py` 调整为信息抽取任务模板，而不仅是 severity+violations。
- 保留引用约束：输出必须含 `citations`（Case ID）。
- 输出 schema 统一为：
  - `severity_level`
  - `core_hazards`
  - `management_gaps`
  - `improvement_actions`
  - `citations`
  - `rationale`
- `app.py` 只做最小功能绑定（不做UI美化）：保证派单逻辑读取 `severity_level`。

### 1.3 Dispatch 输入契约统一
- `dispatch/logic.py` 输入字段从松散 `severity` 统一到 `severity_level`（内部兼容老字段，避免回归）。

## Phase 2（次高优先）：PSM 因果分析（先合成数据）
### 2.1 新增因果分析脚本
- 新增 `analysis/causal_psm.py`：
  - 生成可控合成数据（seed固定，确保复现）
  - 构造 treatment：`complaint_inspection`（0/1）
  - 构造 outcome：`future_incident`（0/1）
  - 协变量：`industry_risk`, `firm_size`, `prior_incidents`, `region_risk`, `safety_training_score` 等
  - 用 Logistic 回归估倾向得分 + 最近邻匹配（含 caliper）
  - 输出 `ATE/ATT` 与 bootstrap CI
- 产物：
  - `results/psm_matched_sample.csv`
  - `results/psm_effect_summary.json`
  - `results/psm_report.md`

### 2.2 真实数据接入预留（标记待办）
- 在脚本中预留 `load_real_inspection_data()` 接口。
- 明确 TODO：后续拿到 complaint-driven inspection 表后替换 `simulate_data()`。

## Phase 3（稳定性与验收）
### 3.1 最小测试集
- `tests/test_extraction_schema.py`：
  - 校验 JSON schema 完整性与类型
  - 校验 `severity_level` 范围 [1,4]
- `tests/test_rag_contract.py`：
  - 校验 `citations` 必须来源于检索结果 case_id
- `tests/test_psm_sanity.py`：
  - 合成数据中预设真实效应为负，估计结果方向应一致（ATE < 0）

### 3.2 运行验收脚本
- 新增 `scripts/verify_pipeline.ps1`：
  1. 检查环境变量；
  2. 运行小样本结构化抽取；
  3. 跑 PSM；
  4. 检查结果文件是否生成。

## 对外接口/类型变化（重要）
1. 环境变量（新增/强约束）
- `DEEPSEEK_API_KEY`（必需）
- `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com/v1`）
- `DEEPSEEK_MODEL`（默认 `deepseek-chat`）

2. 抽取输出 schema（新增标准）
- `severity_level: int`
- `core_hazards: list[str]`
- `management_gaps: list[str]`
- `improvement_actions: list[str]`
- `citations: list[int]`（RAG路径必填）

3. `main.py` 行为变更
- 从“分类预测脚本”变为“结构化抽取批处理脚本”。

## 验收标准
1. 阶段一
- `main.py` 可对输入文本批量输出结构化 JSON；
- RAG 调用返回上述结构字段，且 `citations` 不为空并可映射到 `case_id`；
- Dispatch 能根据 `severity_level` 正常生成任务。

2. 阶段二
- `analysis/causal_psm.py` 一键产出 ATE/ATT 与报告；
- 同一随机种子复跑结果波动在可接受范围（CI稳定）。

3. 稳定性
- 缺失 DeepSeek key 时不崩溃，给出明确错误指引；
- 非JSON模型输出可被重试/记录，不中断整批流程。

## 计划文件落地
- 目标文件路径：`C:\Users\23079\Downloads\Construction-Safety-Dataset-CSDataset-main\docs\FEATURE_COMPLETION_PLAN.md`
- 内容：采用本计划全文，作为后续“调用查看补充”的基线文档。

## 显式假设与默认值
1. 当前仓库没有真实 inspection/complaint 数据表，因此 Phase 2 先合成实现。
2. UI 改造不在本轮范围内，仅做功能可调用与字段契约对齐。
3. DeepSeek 为唯一线上推理提供方；不再以 OpenAI API 作为主路径。
4. 当前轮次为 Plan Mode：仅输出决策完整方案，不执行文件写入与代码改动。
