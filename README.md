# 法律守卫 (LegalGuardian) — AI法律对话实证纠正框架

**当前版本：v5.0.0**（2026-10-27 · 逻辑/形式化版：5×4 矩阵 + 语义四格 + VeriCoT 完整版）

基于西南民族大学法学院**多案例×2轮×4维实证测评** + **人民法院案例库5,515真实案例** +
**2022-2025年法考真题校准**的法学全题型 AI 审查纠正与作业评估引擎。

> 本 Skill 不做"替代律师"或"替代教师"的事——它做的是"在 AI 和法律使用者之间加一层有数据背书的审核护栏"。

---

## 📌 核心能力

| 能力 | 说明 |
|------|------|
| **24 种失效模式检测 (F1-F24)** | F1-F10 通用实证模式、F11-F18 题型特化模式、F19-F24 教信赛智慧评价模式；题型特化模式带场景门控，干净样本零误报 |
| **8 大法学题型差异化评分 (T1-T8)** | 选择题/判断题/名词解释/简答题/论述题/法条分析/案例分析 自动识别与评分，全量校准评级 A |
| **5 大标准化提问模板** | 法条验证/案例对比/多假设追问/前提挑战/实操指引 |
| **8 项安全检查清单** | 与失效模式联动，输出逐项通过/失败状态与总体风险等级 |
| **教学大纲 AI 合规审核** (v4.1.0+) | 对照教育部课程标准 18 项核心知识点核验覆盖率（≥80% 硬性阈值，触发 F24） |
| **案例库本地检索** (v4.3.0+) | 人民法院案例库 5,515 个真实案例确定性关键词检索（`rag_retriever.py`），支持相似案例佐证 |
| **法条时效性人工核验** | 官方检索入口 + 五项核对清单 + 本地留痕（`statute_verifier.py`）；离线预检废止法/条文号越界/虚构法名，不联网、不自动下结论 |
| **逻辑体检（5×4 矩阵）** | 争点/规范/事实/涵摄/边界 × 缺失/错误/矛盾/溢出，20 个单元；8 项确定性筛查（`logic_linter.py`，含废止/虚构法名与条文号越界），输出 issue + 热力图 + 逻辑分 + 修复顺序；支持批量目录与 student/ai_audit 双模式；矩阵只定位，不直接加分 |
| **语义四格 + 人工队列** | M12 争点错位、M32 事实错认、M42 推理错误、M52 边界误用；`--semantic` 生成复核包，`--semantic-input` 合并结论，`--queue-out` 导出低置信度队列 |
| **VeriCoT 完整版** | FOL 解析 → 有限域接地 → DPLL 可满足性/蕴涵检查：校验前提落地、引用存在、步骤完整、结论可推出、前提一致与反例模型；不做 NL→FOL 自动抽取 |
| **三维规制符合性评估** (v4.3.0+) | 技术 T1-T5 / 教育 E1-E4 / 法律 L1-L4 逐项评估 + 雷达数据（`regulation_assessor.py`） |

适用场景：法学作业批改、AI 法律回答审查纠正、智能考试全流程管理、教学质量多维评价、
教学大纲 AI 合规审核、法律 AI 输出合规验证、公众 AI 法律咨询风险提示、案例库本地检索。

---

## 📊 实证数据基础（不可修改的基准事实）

来自 2026 年 5 月 16 日的正式测评（大创项目「生成式AI对法学生辅助学习应用的准确性、
风险挑战及规制路径研究」，徐子涵团队），是执行所有纠正操作的唯一权威参照。

### 综合评分基线（四维 1-5 分制）

| 平台 | 准确性 | 时效性 | 逻辑性 | 引导性 | 综合 |
|------|--------|--------|--------|--------|------|
| DeepSeek | 4.03 | 4.69 | 3.66 | 2.96 | 3.84 |
| 千问 | 3.49 | 4.13 | 2.93 | 1.70 | 3.06 |

### 关键发现（必须内化的纠正依据）
1. **引导性是两者最弱维度**：DS 2.96 / 千问 1.70，R2 角色扮演可提升 40%
2. **量刑预测最大误差 71%**：许某某案 DS 预测 3.5 年 vs 实际判决 6 年
3. **千问接受虚构法律**：接受「人格权侵害惩治条例」为真实法律（识别率 0%）
4. **LPR 基准选择是两模型核心分歧**：合同成立时 vs 起诉时，结果差 30%+
5. **角色扮演不解决核心缺陷**：R2 改善引导性，但量刑偏差、前提验证缺失依然存在

---

## ⚠️ 失效模式体系（F1-F24）

每种模式的匹配关键词与检测策略定义于 `reference/failure_patterns.json`。

### F1-F10：通用失效模式（多案例实证归纳）

| 编号 | 名称 | 严重度 | 一句话定义 |
|------|------|--------|-----------|
| F1 | 法条幻视 | 🔴极高 | AI 接受虚构/废止法律为真实 |
| F2 | 罪名定性降维 | 🟠高 | AI 倾向轻罪定性，回避争议性定性 |
| F3 | 量刑乐观偏差 | 🟠高 | AI 系统性低估刑期（误差可达 71%） |
| F4 | 浅度正确 | 🔴极高 | 结论对但缺乏深度法理分析 |
| F5 | 前提验证盲区 | 🔴极高 | AI 不验证用户前提是否成立 |
| F6 | 引导性赤字 | 🟠高 | 缺实务操作指导（R2 可改善 40%） |
| F7 | 计算推理不一致 | 🟡中高 | 结论与计算示例内部矛盾 |
| F8 | 因果关系过度简化 | 🟠高 | 将多因一果简化为线性因果 |
| F9 | 国际法视野缺失 | 🟡中 | 局限于国内法，缺比较法 |
| F10 | 用户差异化风险盲区 | 🔴极高 | 不区分法学生/非专业人士输出 |

### F11-F18：题型特化失效模式（法考真题校准）

| 编号 | 名称 | 严重度 | 目标题型 | 一句话定义 |
|------|------|--------|---------|-----------|
| F11 | 选项混淆偏误 | 🟠高 | T1,T2 | 混淆可撤销vs无效、终止vs中止等相似概念 |
| F12 | 采分点遗漏 | 🟠高 | T5 | 简答题遗漏答案键中的关键采分点 |
| F13 | 定义要素缺失 | 🟡中高 | T4 | 名词解释缺少主体/客体/要件等要素 |
| F14 | 判对错不给理由 | 🟡中高 | T3 | 判断题只写对/错不附法律依据 |
| F15 | 法条解构不完整 | 🟠高 | T7 | 缺少构成要件→法律后果的完整映射 |
| F16 | 论述偏离题眼 | 🟡中高 | T6 | 论述题未紧扣题干核心争点 |
| F17 | 三段论结构缺失 | 🟠高 | T8 | 缺少大前提→小前提→结论推理链 |
| F18 | 要件事实识别错误 | 🔴极高 | T8 | 混淆关键法律要件事实与非关键背景 |

### F19-F24：教信赛智慧评价场景特化（v4.1.0 新增）

| 编号 | 名称 | 严重度 | 目标 | 一句话定义 |
|------|------|--------|------|-----------|
| F19 | 试题歧义偏差 | 🟠高 | 考试设计 | 试题表述可能产生歧义，导致不同学生合理理解不同 |
| F20 | 评分尺度偏移 | 🟠高 | 评分一致性 | 同一评分标准在不同批次/评分者间系统性偏严或偏松 |
| F21 | 答案格式违规 | 🟡中高 | 答题规范 | 学生以不符合题目要求的格式作答 |
| F22 | 跨题一致性破裂 | 🟠高 | 综合评估 | 同一学生在不同题型中对同一法律原则给出矛盾回答 |
| F23 | 采分点粒度失当 | 🟡中高 | 简答题设计 | 答案键采分点粒度过粗或过细 |
| F24 | 教学大纲合规偏离 | 🔴极高 | 教学管理 | 教学内容/试题未覆盖教育部课程大纲规定的必授知识点 |

---

## 🎯 8 大题型差异化评分（T1-T8）

评分标准定义于 `reference/question_type_rubrics.json`。

| 题型 | 评分方式 | 满分 |
|------|---------|------|
| T1 单选题 | 答案键精确匹配 | 1 |
| T2 多选题 | 部分得分制（少选按比例） | 2 |
| T3 判断题 | 答案键精确匹配 + 理由完整性 | 1+2 |
| T4 名词解释 | 三维关键词覆盖（概念/要素/法源） | 5 |
| T5 简答题 | 采分点覆盖法 | 10 |
| T6 论述题 | 五维加权（逻辑30%+深度25%） | 30 |
| T7 法条分析题 | 四维结构化评分 | 20 |
| T8 案例分析题 | 五维加权（准确30%+逻辑25%） | 25 |

**评分锚定规则**：5 分=DS 最佳表现 / 3 分=DS 综合平均 3.84 / 1 分=千问引导性 1.70。
**绝对红线**：作业出现 F1（法条虚构）→ 法律依据维度直接 0 分；F24（知识点覆盖率<80%）→ 大纲审核不通过。

---

## 🧩 工作模块

| 模块 | 功能 |
|------|------|
| **A. AI 法律回答审核纠正**（核心） | 失效模式检测 → 纠正建议生成 → 安全检查清单 + 案例库相似案例佐证 + 法条时效人工核验，输出审核报告 |
| **B. 提问优化与模板推荐** | 分析原始问题陷阱，匹配 5 大标准化模板并给出优化后提问 |
| **C. 法学作业评估与评分** | 8 题型自动识别、差异化评分、红线统一（F1 命中即 D1 归零）、五维评估报告 |
| **D. 三维规制符合性评估** (v4.3.0+) | 技术(T1-T5)/教育(E1-E4)/法律(L1-L4) 逐项评估 + 雷达数据 + 路线图 |
| **E. 教学大纲 AI 合规审核** (v4.1.0+) | 覆盖率核验（18 项知识点）+ F24 检测 + 修订建议 |
| **F. 可视化报告面板** (v4.3.0+) | `panel/report_panel.html` 零依赖单文件：一键生成全链路"审核案卷"，内嵌 3 份示例（AI 审核/大纲审核/作业评估），支持拖入 JSON 与打印/导出 PDF |
| **G. 逻辑体检** | `logic_linter.py`：5×4 矩阵 + 8 项确定性筛查，输出 issue、热力图、逻辑分与修复顺序；已接入 `report_builder.py` 的 `logic` 模块 |

---

## 📁 目录结构

```
legal-guardian/
├── SKILL.md                  # 技能主文档（Claude Code 指令）
├── manifest.yaml             # 技能清单（名称/版本/描述）
├── README.md                 # 本文件
├── scripts/                  # 20 个 Python 脚本
│   ├── failure_detector.py   # 失效模式检测（F1-F24，场景门控）
│   ├── correction_engine.py  # 纠正建议生成
│   ├── safety_checker.py     # 8 项安全检查清单
│   ├── template_matcher.py   # 标准化提问模板推荐
│   ├── scoring_engine.py     # 四维评分与基线对比
│   ├── question_type_classifier.py  # 题型识别与路由（T1-T8）
│   ├── answer_key_evaluator.py      # 答案键验证/批量评分
│   ├── law_assignment_evaluator.py  # 五维评估库 + v1 入口
│   ├── law_assignment_evaluator_v2.py # 8题型统一评估器（主入口）
│   ├── legal_db_fetcher.py          # 法条库检索（本地优先）
│   ├── statute_verifier.py          # 法条时效人工核验（链接+清单+留痕）
│   ├── logic_linter.py              # 逻辑体检（5×4 矩阵 + 8 项筛查）
│   ├── vericot_check.py             # VeriCoT 完整版（FOL + 有限域 DPLL）
│   ├── fol_engine.py                # 一阶逻辑解析/接地/DPLL 引擎
│   ├── rag_retriever.py             # 案例库检索（5,515 例，v4.3.0+）
│   ├── regulation_assessor.py       # 三维规制评估（v4.3.0+）
│   ├── report_builder.py            # 全链路报告构建（v4.3.0+）
│   ├── calibrate_scoring.py         # 评分校准器（开发工具）
│   ├── exam_parser.py               # 法考真题 PDF 解析器（开发工具）
│   └── generate_upgrade_doc.py      # 升级文档生成（开发工具）
├── panel/                    # 可视化报告面板（v4.3.0+）
│   ├── report_panel.html     # 零依赖单文件（内嵌 3 份示例数据，双击即用）
│   ├── demo_report.json      # 示例：AI 回答审核全链路报告
│   ├── demo_syllabus.json    # 示例：教学大纲合规审核
│   └── demo_assignment.json  # 示例：法学作业评估
├── reference/                 # JSON 知识库（12 个运行时文件，无历史残留）
│   ├── failure_patterns.json  # 24 种失效模式特征库
│   ├── correction_templates.json    # 5 大提问模板
│   ├── safety_checklist.json        # 8 项安全检查清单
│   ├── question_type_rubrics.json   # 8 题型评分标准
│   ├── assignment_rubric.json       # 作业评分标准
│   ├── curriculum_requirements.json # 教学大纲合规标准（18 项知识点）
│   ├── legal_knowledge_base.json    # 法条知识库
│   ├── statutes_seed.json           # 法条核验种子库（核心法/废止法/虚构法）
│   ├── logic_taxonomy.json          # 逻辑矩阵（5 阶段 × 4 失效 × 20 单元）
│   ├── logic_rubric.json            # 逻辑评分/主责/去重/指标
│   ├── test_baseline.json           # 实证基线
│   └── three_d_regulation.json      # 三维规制标准
├── benchmark/                 # 黄金标准基准测试集（16 基准 + 10 回归）
├── templates/                 # 报告/生成模板（logic_review_template.md、irac_scaffold.md）
├── tests/  +  test_data/      # 冒烟测试（44 项）与测试数据
├── test_data/                 # 大数据资产：5,515 案例 / RAG 块 / 训练样本（仓库级证据）
└── 产品技术文档/               # 5 份 PDF（由 gen_docs.py 生成）
```

> 注：v5.0.0 精简包 `legal-guardian.skill`（约 0.28MB）仅含运行时必需文件；同时输出 `legal-guardian-v5.0.0.skill` 便于 Release。
> （SKILL.md/manifest/README/scripts/reference/benchmark/templates/tests/panel）；
> `test_data` 大数据资产（约 44MB）与 `产品技术文档` 保留在仓库作为实证证据。

---

## 🚀 安装与使用

### 作为 Claude Code Skill 安装
1. 将 `legal-guardian.skill`（zip 包，约 0.28MB）解压到 `~/.claude/skills/legal-guardian/`
2. 重启 Claude Code，在对话中直接使用 `legal-guardian` skill
3. 注：精简包不含 `test_data/`（5,515 案例库/训练语料为仓库级证据数据）。如需案例库检索（`rag_retriever.py`），从仓库将 `test_data/rags/chunks.json` 与 `test_data/cases/all_cases.json` 复制到技能目录对应路径

### 可视化报告面板（路演/评审演示）
```bash
# 1. 生成全链路报告 JSON（任意 AI 回答/作业/大纲文本）
python scripts/report_builder.py 输入.txt --query "民间借贷 利息" --out panel/demo_report.json
# 2. 双击打开 panel/report_panel.html —— 无需服务器，离线可用；
#    内嵌 3 份示例可直接演示，也可拖入上一步生成的 JSON
# 3. 浏览器"打印"可导出 PDF 版审核案卷
```

### 主要脚本调用

```bash
# 失效模式检测
python scripts/failure_detector.py <输入文本文件路径>

# 纠正建议生成
python scripts/correction_engine.py <检测结果JSON文件路径>

# 法学作业评估（8题型统一）
python scripts/law_assignment_evaluator_v2.py <作业文件> [--answer-key <JSON>]

# 题型自动识别
python scripts/question_type_classifier.py <输入文本> [--answer-key <JSON>]

# 安全检查
python scripts/safety_checker.py <输入文本> [--detections <检测结果JSON>]

# 提问模板推荐
python scripts/template_matcher.py "<用户原始问题文本>"

# 案例库检索（5,515 例，v4.3.0+）
python scripts/rag_retriever.py --query "民间借贷 利息上限" -k 5 [--detail]

# 法条时效人工核验（离线生成链接+清单，核对后留痕）
python scripts/statute_verifier.py --law "民法典" --article "第1165条"
python scripts/statute_verifier.py --law "民法典" --article "第1165条" \
    --record --verdict active --verifier "张三" --note "官网核对"
python scripts/statute_verifier.py --list   # 查看记录；--stats / --pending 同理

# 逻辑体检（5×4 矩阵 + 8 项筛查）
python scripts/logic_linter.py <作业/回答文件>
python scripts/logic_linter.py <文件> --json --out logic.json
python scripts/logic_linter.py <文件> --mode ai_audit      # AI 审核门控：先规范、后争点
python scripts/logic_linter.py --batch <目录> --out results.jsonl
python scripts/logic_linter.py <文件> --semantic --question "请分析李某的侵权责任"
python scripts/logic_linter.py <文件> --semantic-input review.json
python scripts/logic_linter.py <文件> --queue-out queue.jsonl
# 全链路报告默认包含 logic 模块；也可 --modules logic 单独生成

# VeriCoT 完整版：先生成结构化模板，再校验
python scripts/vericot_check.py --packet --text "<原文>"
python scripts/vericot_check.py argument.json

# 三维规制评估（v4.3.0+）
python scripts/regulation_assessor.py --text "<AI法律工具功能描述>" [--detections <检测JSON>]

# 评分校准（开发工具）
python scripts/calibrate_scoring.py [--quick]

# 法考真题解析（开发工具）
python scripts/exam_parser.py <PDF路径> --type objective|subjective
```

### 逻辑体检与形式化校验的测试（开发/维护）

```bash
python tests/test_logic_linter.py      # 20 项单元测试（矩阵/CLI/评分/语义/批量/队列）
python tests/logic_eval.py             # 20 条合成 fixture 的误差校准
python tests/test_vericot_check.py     # VeriCoT 单元测试（lite + full）
python tests/test_fol_engine.py        # FOL 引擎 8 项单元测试
python tests/test_statute_verifier.py  # 法条核验助手 12 项单元测试
```

> 合成 fixture 的 0 误报 / 1.0 召回只说明规则与样本自洽，不代表真实分布；正式使用前需用 50–100 条双人标注样本重新校准，并按 `logic-rubric` 的 precision/recall 目标验收。

---

## 📜 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| **v5.0.0** | 2026-10-27 | **逻辑/形式化版**：5×4 逻辑体检矩阵（20 单元/8 项筛查）、语义四格 M12/M32/M42/M52、低置信度队列、批量与双门控、根因去重、条号越界；新增 VeriCoT 完整版（FOL + 有限域 DPLL + 步骤 trace/反例）；面板逻辑页签；冒烟 44 项 0 FAIL 0 KNOWN |
| **v4.3.0** | 2026-08-19 | **简洁精进版**：F1 纠正文豁免/F2 死代码复活/F11 正则对合并/题型特化模式场景门控/F24 读 18 项知识点；红线统一（F1 命中⇒D1 归零）；题型识别 5 处修复；新增 rag_retriever + regulation_assessor（模块D 落地）；删除 reference/ 5 个 v2.0.0 残留（-1.9MB）；安装包瘦身 14MB→约2MB；全量校准 C→A（100%/0.0/69.2%）；冒烟 39 项 0 FAIL 0 KNOWN |
| **v4.2.1** | 2026-08-17 | **文档结构优化**：SKILL.md 547→258 行、manifest 与模板版本对齐、校准口径修正（区分快速/全量）；全量冒烟测试 PASS=28 / FAIL=0 |
| **v4.2.0** | 2026-08-05 | **性能优化 + 正确性修复 + 代码质量重构**（全 13 脚本）：JSON 知识库缓存、进程内检测调用消除子进程/32767 字符限制、主观题评分归一化、红线规则修复、检测→纠正链路对齐、`sys.executable` 统一 |
| v4.1.0 | 2026-08 | 教信赛智慧评价强化：新增 F19-F24 失效模式、教学大纲 AI 合规审核（模块E）、竞赛铁律 |
| v4.0.0 | 2026-07 | 全题型作业评估：新增 F11-F18 题型特化失效模式、8 大题型 T1-T8 差异化评分、5 个新脚本 |
| v3.0.0 | 2026-07 | 人民法院案例库全量知识库：5,515 真实案例、535 种案由/罪名、27,575 组问答训练样本、RAG 检索块 |
| v2.0.0 | — | 数据扩充：900 案例、1,800 QA、900 RAG、71 种原因类型 |
| v1.0.0 | — | 初始版本 |

### v4.3.0 校准结果（2026-08-19）

| 指标 | 快速模式（4 项） | 全量模式（26 项） |
|------|-----------------|------------------|
| 题型识别准确率 | 100% | 100% |
| 客观题评分 MAE | 0.0 | 0.0 |
| 失效模式检测召回率 | 100% | 69.2%（5 项基准以题干作输入，属基准设计限制） |
| 综合评级 | A（优秀校准） | A（优秀校准） |

---

## ⚖️ 适用范围与限制

**适用**：中国法律体系下法律问答审核（民法、刑法为主）、法学本科/研究生作业评估（T1-T8）、
AI 法律工具输出质量审核、教学大纲 AI 合规审核（教信赛智慧评价赛道）。

**限制**：
- 行政法、国际法、税法等专业领域审核精度有限
- 不替代律师出具正式法律意见；不适用于非中文法律体系
- 评分结果应作为参考而非最终成绩
- F20/F22 检测需多份输入，单文本仅为基础信号

---

**作者**：徐子涵团队（西南民族大学法学院大创项目）· 教信赛智慧评价赛道
**仓库**：https://github.com/Phillnarsoeer/legal-guardian


