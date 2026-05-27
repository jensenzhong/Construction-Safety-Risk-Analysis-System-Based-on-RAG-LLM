<div align="center">

# :construction: 施工安全风险智能分析系统

**Construction Safety Risk Analysis System Based on RAG + LLM**

基于检索增强生成与大语言模型的施工安全风险智能决策平台

<br/>

---

## :camera: 系统截图

### 数据管理与风险仪表盘（温度 / 风速 / 湿度）

<img width="604" height="401" alt="image" src="https://github.com/user-attachments/assets/271ef1a6-a231-4278-8ab4-4d1bf2ccca5d" />

### 事故预评估与RAG 历史案例检索

<img width="897" height="429" alt="image" src="https://github.com/user-attachments/assets/a232a902-4063-467d-8802-68efbed27e51" />
<img width="3148" height="3024" alt="PixPin_2026-03-14_12-50-13" src="https://github.com/user-attachments/assets/45e04c5e-d87a-461b-83e5-c5951010560c" />


### 月度事故趋势、事故热力图与环境因素关联分析

<img width="3200" height="4149" alt="PixPin_2026-03-14_12-47-57 - 副本(1)" src="https://github.com/user-attachments/assets/ce6cc2ec-c9c0-48a6-81a5-ca59a56fe6ea" />

<br/>

---
<br/>

![](https://img.shields.io/badge/方法-RAG%20%2B%20LLM-FF6F61?style=for-the-badge&labelColor=2D2D2D)
![](https://img.shields.io/badge/数据-53000%2B%20OSHA事故-4A90D9?style=for-the-badge&labelColor=2D2D2D)
![](https://img.shields.io/badge/分析-因果推断%20PSM-50C878?style=for-the-badge&labelColor=2D2D2D)

![](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![](https://img.shields.io/badge/Streamlit-1.55+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![](https://img.shields.io/badge/FAISS-Vector_Search-0467DF?style=flat-square&logo=meta&logoColor=white)
![](https://img.shields.io/badge/DeepSeek-LLM-5A67D8?style=flat-square&logo=openai&logoColor=white)
![](https://img.shields.io/badge/Sentence_Transformers-Embedding-FF9900?style=flat-square&logo=huggingface&logoColor=white)
![](https://img.shields.io/badge/PyInstaller-Windows_Packaging-13AA52?style=flat-square&logo=windows&logoColor=white)
![](https://img.shields.io/badge/Plotly-Visualization-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![](https://img.shields.io/badge/License-MIT-green?style=flat-square)

<br/>

</div>

---

## :bookmark_tabs: 目录

<details open>
<summary><b>展开 / 收起</b></summary>
<br/>

- [:star2: 项目简介](#star2-项目简介)
- [:brain: 核心技术](#brain-核心技术)
- [:building_construction: 系统架构](#building_construction-系统架构)
- [:camera: 系统截图](#camera-系统截图)
- [:jigsaw: 功能模块](#jigsaw-功能模块)
- [:open_file_folder: 项目结构](#open_file_folder-项目结构)
- [:wrench: 技术栈](#wrench-技术栈)
- [:rocket: 快速开始](#rocket-快速开始)
- [:bar_chart: 数据与索引](#bar_chart-数据与索引)
- [:test_tube: 测试](#test_tube-测试)
- [:package: Windows 打包分发](#package-windows-打包分发)
- [:question: 常见问题](#question-常见问题)
- [:lock: 安全说明](#lock-安全说明)
- [:world_map: Roadmap](#world_map-roadmap)
- [:balance_scale: 声明](#balance_scale-声明)

</details>

<br/>

---

## :star2: 项目简介

本系统是一个面向 **建筑工程施工安全** 领域的智能风险分析平台，以 **53,000+ 条 OSHA 真实事故记录** 为知识库，结合 **检索增强生成（RAG）** 与 **大语言模型（DeepSeek）**，为施工现场提供智能化的安全决策支持。

系统核心能力：

- :dart: **事故预评估** — 输入施工计划、工种、环境参数，自动输出结构化风险报告
- :mag: **语义案例检索** — 基于 FAISS 向量索引的毫秒级相似事故检索
- :chart_with_upwards_trend: **可视化仪表盘** — 实时环境风险监测与事故趋势分析
- :bar_chart: **因果推断分析** — 基于 PSM（倾向得分匹配）的环境因素影响量化
- :desktop_computer: **一键部署** — PyInstaller 打包，无需 Python 环境即可运行

<br/>

---

## :brain: 核心技术

> **RAG（检索增强生成）**：将大规模事故知识库与 LLM 推理能力结合，让模型基于真实案例给出有据可依的安全建议，而非凭空生成。

```
传统方式：  人工查阅规范 → 经验判断 → 主观评估
                  ↓
本系统：    语义检索历史案例 → LLM 结构化分析 → 量化风险评估
```

| 传统模式 | 本系统 |
|:--------:|:------:|
| 人工查阅事故报告 | FAISS 毫秒级语义检索 |
| 经验主观判断 | LLM 结构化推理 |
| 单一因素分析 | 多维环境因素关联 |
| 事后总结 | 事前预评估 |
| 静态报表 | 实时可视化仪表盘 |

<br/>

---

## :building_construction: 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    施工安全风险智能分析系统                            │
├──────────────────┬──────────────────┬───────────────────────────────┤
│   数据层          │    分析层         │    展示层                      │
│                  │                  │                               │
│  OSHA 事故数据   │  RAG 语义检索     │  Streamlit Web UI             │
│  53,000+ 记录    │  DeepSeek LLM    │  Plotly 可视化                 │
│  FAISS 向量索引  │  PSM 因果推断     │  风险仪表盘                    │
│  环境参数数据    │  本地兜底评估     │  结构化报告                    │
│                  │                  │                               │
│   📦 存储        │    🧠 推理        │    📊 交互                     │
└──────────────────┴──────────────────┴───────────────────────────────┘
```

**数据流向**：

```
用户输入（工种/环境/计划）
        ↓
  语义向量化（sentence-transformers）
        ↓
  FAISS 相似案例检索 + 关键词混合打分
        ↓
  构建 Prompt（检索结果 + 用户输入）
        ↓
  DeepSeek LLM 结构化推理
        ↓
  输出：风险等级 / 危险源 / 预防措施 / PPE / 引用案例
```


## :jigsaw: 功能模块

### :one: 事故预评估与风险建议

> 输入施工计划、工种、环境参数（温度/风速/湿度），系统自动输出结构化风险报告

| 输出项 | 说明 |
|:------:|:----:|
| :warning: 风险等级 | 1-4 级量化评估 |
| :boom: 潜在危险源 | 基于历史案例识别 |
| :clipboard: 管理薄弱点 | 制度与流程缺陷 |
| :shield: 预防措施 | 针对性安全建议 |
| :rescue_worker_helmet: 必备 PPE | 个人防护装备清单 |
| :books: 引用案例 | 相似历史事故参考 |

---

### :two: RAG 语义检索引擎

> 混合检索策略：语义相似度 + 关键词匹配，双重打分确保召回质量

- :zap: **向量化**：`sentence-transformers/all-MiniLM-L6-v2` 生成 384 维语义向量
- :mag_right: **索引**：FAISS 向量索引，支持毫秒级 Top-K 检索
- :dart: **混合打分**：`hybrid_score = α × semantic + β × keyword`
- :globe_with_meridians: **多语言扩展**：中英关键词提示扩展（高处/坠落/触电 ↔ fall/electrocution）

---

### :three: 可视化风险仪表盘

> 实时环境监测 + 事故画像 + 趋势分析

- :thermometer: **环境风险仪表** — 温度、风速、湿度三维监测
- :chart_with_upwards_trend: **事故月度趋势** — 时间序列分析
- :world_map: **事故热力图** — 地理分布可视化
- :busts_in_silhouette: **事故画像** — 工种、危害类型、季节分布
- :link: **环境关联** — 温度/风速与事故率相关性

---

### :four: PSM 因果推断分析

> 基于倾向得分匹配（Propensity Score Matching）量化环境因素对事故严重程度的因果效应

- 控制混杂变量（工种、季节、地区）
- 估计处理效应（ATE / ATT）
- 输出匹配样本与效应报告

<br/>

---

## :open_file_folder: 项目结构

```
Construction-Safety-Risk-Analysis-System/
├── app.py                              # 🖥️ Streamlit 主应用（Web UI）
├── launcher.py                         # 🚀 打包后启动入口
├── main.py                             # 📋 批量结构化抽取脚本
├── requirements.txt                    # 📦 Python 依赖清单
├── ConstructionSafetyAssistant.spec    # 🔧 PyInstaller 打包规格
├── settings.example.json              # ⚙️ 配置模板（不含密钥）
├── run_app.bat                         # ▶️ Windows 一键启动
├── stop_app.bat                        # ⏹️ 停止服务
├── .gitignore                          # 🔒 Git 忽略规则
├── LICENSE                             # 📄 MIT 许可证
│
├── rag/                                # 🔍 RAG 检索模块
│   ├── config.py                       #    ├── 数据与索引路径配置
│   ├── index_builder.py                #    ├── FAISS 索引构建
│   ├── retrieval.py                    #    ├── 检索与混合打分
│   ├── prompting.py                    #    ├── 提示词构建
│   ├── extraction_schema.py            #    ├── 结构化输出校验
│   └── local_pre_assessment.py         #    └── 本地兜底预评估
│
├── llm/                                # 🧠 LLM 调用模块
│   └── client.py                       #    └── DeepSeek 配置解析与调用
│
├── analysis/                           # 📊 因果分析模块
│   └── causal_psm.py                   #    └── 倾向得分匹配（PSM）
│
├── sensors/                            # 📡 传感器模块
│   └── api.py                          #    └── 传感器读取接口（当前 mock）
│
├── scripts/                            # 🛠️ 工具脚本
│   ├── start_app.py                    #    ├── 开发态启动逻辑
│   ├── stop_app.ps1                    #    ├── 停止服务
│   ├── build_windows_installer.py      #    ├── 一键生成安装器
│   └── installer_bootstrap.py          #    └── 安装器引导脚本
│
├── tests/                              # ✅ 测试用例（12 项）
├── indexes/                            # 🗂️ FAISS 索引与元数据
├── results/                            # 📈 分析结果输出
├── release/                            # 📦 发布产物（安装器）
├── docs/screenshots/                   # 📸 系统截图
├── 文档信息归档/                         # 📚 项目文档归档
└── Injury Severity.CSV                 # 🗃️ OSHA 事故数据集（53,000+）
```

<br/>

---

## :wrench: 技术栈

| 类别 | 技术 | 说明 |
|:---:|:---:|:---:|
| :globe_with_meridians: Web 框架 | Streamlit | 快速构建数据应用 |
| :brain: 大语言模型 | DeepSeek Chat | OpenAI 兼容接口 |
| :mag: 向量检索 | FAISS | Meta 开源向量数据库 |
| :abc: 文本嵌入 | sentence-transformers | all-MiniLM-L6-v2 |
| :chart_with_upwards_trend: 可视化 | Plotly | 交互式图表 |
| :bar_chart: 数据处理 | Pandas / NumPy | 数据分析与处理 |
| :test_tube: 因果推断 | statsmodels / scipy | PSM 倾向得分匹配 |
| :package: 打包分发 | PyInstaller | Windows 安装器生成 |
| :snake: 运行环境 | Python 3.12+ | 主语言 |

<br/>

---

## :rocket: 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/jensenzhong/Construction-Safety-Risk-Analysis-System-Based-on-RAG-LLM.git
cd Construction-Safety-Risk-Analysis-System-Based-on-RAG-LLM
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

复制示例配置文件并填入你的 DeepSeek API Key：

```bash
cp settings.example.json settings.json
```

编辑 `settings.json`：

```json
{
  "deepseek": {
    "api_key": "your_api_key_here",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  }
}
```

或使用环境变量：

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY="your_api_key"

# Linux / macOS
export DEEPSEEK_API_KEY="your_api_key"
```

### 5. 启动应用

```bash
# 方式 A：使用项目脚本（推荐）
run_app.bat

# 方式 B：直接运行
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

> :bulb: **提示**：浏览器访问 `http://127.0.0.1:8501`

<br/>

---

## :bar_chart: 数据与索引

### 数据集

默认使用 `Injury Severity.CSV`，包含 **53,000+** 条 OSHA 真实事故记录。

| 字段 | 说明 |
|:---:|:---:|
| `abstract` | 事故描述文本（用于检索与分析） |
| `event_keyword` | 事故关键词分类 |
| `degree_of_inj_x` | 伤害严重程度 |
| `date` | 事故发生日期 |
| `temp` / `wind_speed` / `wind_deg` | 环境参数 |

### 构建索引

```bash
python -m rag.index_builder --device cpu
```

生成文件：
- `indexes/faiss.index` — FAISS 向量索引
- `indexes/metadata.parquet` — 结构化元数据

<br/>

---

## :test_tube: 测试

```bash
pytest -q
```

测试覆盖（12 项）：

| 模块 | 测试内容 |
|:---:|:---:|
| RAG | 引用过滤与约束验证 |
| 预评估 | 输出结构完整性 |
| LLM | DeepSeek 配置解析 |
| 启动器 | 配置播种逻辑 |
| PSM | 因果分析健全性 |

<br/>

---

## :package: Windows 打包分发

### 一键打包安装器

```bash
python scripts/build_windows_installer.py
```

产物：`release/ConstructionSafetyAssistant-Installer.exe`

### 安装后运行

1. 运行安装器，按提示完成安装
2. 桌面 / 开始菜单启动 **Construction Safety Assistant**
3. 浏览器自动打开 `http://127.0.0.1:8501`

> :bulb: 打包版本已内置 Python 运行时和所有依赖，无需额外安装。

<br/>

---

## :question: 常见问题

| 问题 | 解决方案 |
|:---:|:---:|
| 启动后浏览器没打开 | 手动访问 `http://127.0.0.1:8501` |
| 提示缺少索引文件 | 运行 `python -m rag.index_builder --device cpu` |
| DeepSeek 报 API Key 缺失 | 检查 `settings.json` 或环境变量 `DEEPSEEK_API_KEY` |
| 查看启动日志 | `%LOCALAPPDATA%\ConstructionSafetyAssistant\launcher.log` |
| 如何停止服务 | 运行 `stop_app.bat` 或关闭终端窗口 |

<br/>

---

## :lock: 安全说明

本项目已配置 `.gitignore` 保护敏感文件：

- :white_check_mark: `settings.json`（含 API Key）**不会**被提交
- :white_check_mark: `.env` 文件**不会**被提交
- :white_check_mark: `settings.example.json` 提供安全配置模板

> :rotating_light: **请勿将真实 API Key 提交到公开仓库。**

<br/>

---

## :world_map: Roadmap

- [ ] 接入真实传感器（MQTT / HTTP / 串口）
- [ ] 增加多工种风险模板库
- [ ] 引入用户权限与审计日志
- [ ] 支持多项目 / 多工地数据隔离
- [ ] 增强检索评估指标与可解释性
- [ ] 支持更多 LLM 后端（GPT-4、Claude、通义千问）
- [ ] 移动端适配与小程序版本

<br/>

---

## :balance_scale: 声明

> :information_source: 本项目为广州大学大学生创新训练项目，基于公开的 OSHA 事故数据集进行研究开发。系统中的传感器数据为模拟数据，仅用于展示系统设计理念和核心功能。

<br/>

<div align="center">

**施工安全风险智能分析系统** · 2025

Made with :heart: by Jensen Zhong

</div>
