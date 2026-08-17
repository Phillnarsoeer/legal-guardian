# LegalGuardian v4.2.1 功能测试方案

> 测试对象：本仓库根目录（`SKILL.md` / `manifest.yaml` 所在目录）
> 文档日期：2026-08-11　|　配套运行器：`tests/run_smoke.py`　|　本方案所有结论均基于**实机运行验证**（Python 3.12.10, Windows 11）

---

## 目录
- [一、核心结论速览](#一核心结论速览)
- [二、测试环境](#二测试环境)
- [三、测试方向与详细步骤](#三测试方向与详细步骤)
- [四、自动化运行器使用说明](#四自动化运行器使用说明)
- [五、实测 PASS/FAIL 报告（2026-08-11）](#五实测-passfail-报告2026-08-11)
- [六、已知问题清单](#六已知问题清单)
- [七、建议的下一步改进](#七建议的下一步改进)

---

## 一、核心结论速览

**skill 基本可用**：三阶段链路（检测→纠正→安全检查）、红线归零、主观题归一化、F22 插值修复、模板推荐、作业评估 v2、四维评分、离线法条检索**均实测工作正常**；`--quick` 校准可复现 A 级声明；数据规模声明（F1-F24 / T1-T8 / 8 安全项 / 5 模板 / 5515 案例 / 5515 块 / 22060+5515 训练）**全部为真**。

**但存在 7 类已知问题**（详见[第六节](#六已知问题清单)），其中 **4 项是必须修的功能缺陷**：

| 严重度 | 问题 | 一句话 |
|--------|------|--------|
| 🔴 | F1/F17 误报 | 干净回答（AI 已纠正废止法、含完整三段论）仍被判 critical |
| 🔴 | F2 死代码 | "罪名定性降维"模式因中英键名不匹配**永远不会触发** |
| 🔴 | 校准声明夸大 | 全量校准实际 **C 级**（68.8%），仅 `--quick`(4 项) 才是 A；SKILL.md 却宣称"16/16 100%" |
| 🟠 | 红线不一致 | F1 虚构法条命中不会归零 D1，仅"已废止"子串才触发（与 rubric 文档矛盾） |
| 🟠 | 模块 D 未实现 | 三维规制评估**无任何脚本产出报告**，纯文档功能 |
| 🟠 | 模块 E 数据源错位 | F24 用的是硬编码 8 项，不读 `curriculum_requirements.json` 的 18 项 |
| 🟡 | reference/ 陈旧数据 | 4 个 v2.0.0 文件（case_chunks=900 等）残留，与 5515 声明不符 |

---

## 二、测试环境

```bash
LG="$(pwd)"
cd "$LG"
python --version        # 需 >=3.9；本机 3.12.10 ✓
python -c "import json" # 运行器纯标准库，无第三方依赖
# 可选：PyMuPDF(fitz) 用于 exam_parser / gen_docs 测试
# 建议在副本上测试，避免污染 git 仓库：
cp -r "$LG" "$LG"_test
```

---

## 三、测试方向与详细步骤

### 方向 1：安装 / 技能识别 / 打包完整性（Level 0）

**目的**：确认 Claude Code 能识别 skill、`.skill` 包可解压、已安装版本正确。

```bash
# 1. SKILL.md frontmatter 与 manifest.yaml 一致
python -c "
import yaml
fm = yaml.safe_load(open('SKILL.md', encoding='utf-8').read().split('---')[1])
mf = yaml.safe_load(open('manifest.yaml', encoding='utf-8'))
assert fm['name'] == mf['name'] == 'legal-guardian' and mf['version'] == '4.2.1'
print('PASS: 识别元数据一致')
"
# 2. .skill 合法 zip，含全部 8 个顶层目录（运行器 E4 已自动化）
python -c "
import zipfile
z = zipfile.ZipFile('legal-guardian.skill')
assert z.testzip() is None
tops = {n.split('/')[0] for n in z.namelist()}
req = {'manifest.yaml','SKILL.md','benchmark','reference','scripts','templates','tests','test_data'}
print('缺失:', req - tops)
"
# 3. 已安装副本一致
diff -rq --exclude=.git --exclude=legal-guardian.skill --exclude=产品技术文档 \
  "C:/Users/123/.claude/skills/legal-guardian" "$LG"
# 4. 在 Claude Code 中 /legal-guardian 触发，确认技能加载
```

**注意**：`.skill` 内 `test_data/cases/刑事.json`、`民事.json` 两个**中文文件名解压后会乱码**（zip 中心目录 UTF-8 往返损坏），消费脚本按文件名查找会失败。

---

### 方向 2：数据资产完整性（Level 1）

**目的**：验证 SKILL.md 的 6 大数据声明（运行器 D1-D10 已自动化）。

```bash
python -c "
import json
def L(f): return len(json.load(open(f, encoding='utf-8')))
def LINES(f): return sum(1 for _ in open(f, encoding='utf-8'))

fp = json.load(open('reference/failure_patterns.json', encoding='utf-8'))
ids = [p['id'] for p in fp['patterns']+fp['patterns_v2']]
assert len(ids)==24 and ids==[f'F{i}' for i in range(1,25)]
assert len(json.load(open('reference/safety_checklist.json',encoding='utf-8'))['checklist'])==8
assert len(json.load(open('reference/correction_templates.json',encoding='utf-8'))['templates'])==5
assert len(json.load(open('reference/question_type_rubrics.json',encoding='utf-8'))['question_types'])==8
assert L('test_data/cases/all_cases.json')==5515
assert L('test_data/rags/chunks.json')==5515
assert LINES('test_data/training/train.jsonl')==22060
assert LINES('test_data/training/val.jsonl')==5515
print('PASS: F1-F24/8项/5模板/8题型/5515案例/5515块/22060+5515 声明全部属实')
"
# 已知不符（记为缺陷）：
#   reference/case_chunks.json   = 900 块（声明 5515，v2.0.0 残留）
#   reference/train.jsonl       = 1440 行（声明 22060，v2.0.0 残留）
#   reference/val.jsonl         = 360  行（声明 5515，v2.0.0 残留）
#   reference/case_knowledge_base.json = total_cases 900（声明 5515）
#   benchmark meta.total_items  = 50   （实际 26 项）
#   T3 判断题满分 = 1（SKILL.md 声称 1+2=3）
```

---

### 方向 3：脚本冒烟 / 单元测试（Level 2）

**目的**：逐个确认 13 个脚本 CLI 可用、输出合法 JSON、报错符合 v4.2.1"结构化错误"声明。**全部命令已由 `tests/run_smoke.py` 自动化**，此处列出等价手工命令：

```bash
# 失效检测（对照 tests/test_data 各样本的 expected_detection 字段）
python scripts/failure_detector.py tests/test_data/sample_ai_response_f1.json    # 应 F1 critical
python scripts/failure_detector.py tests/test_data/sample_ai_response_multi.json # 应 F1+F4+F6
python scripts/failure_detector.py tests/test_data/sample_ai_response_clean.json # 应 0 触发【实测误报】

# 检测→纠正链路（Windows 下勿用管道，写中间文件）
python scripts/failure_detector.py tests/test_data/sample_ai_response_f1.json > det.json
python scripts/correction_engine.py det.json

# 安全检查（联动检测结果）
python scripts/safety_checker.py tests/test_data/sample_ai_response_f1.json --detections det.json

# 模板匹配（⚠️ 传"问题文本"，不是文件路径）
python scripts/template_matcher.py "根据《民法通则》第X条我能要回利息吗"   # → T4
python scripts/template_matcher.py "朋友故意伤害大概判几年"               # → T2

# 作业评估 v1 / v2
python scripts/law_assignment_evaluator.py tests/test_data/sample_assignment.md --course case_analysis
python scripts/law_assignment_evaluator_v2.py tests/test_data/sample_assignment.md

# 四维评分
python scripts/scoring_engine.py tests/test_data/sample_ai_response_f1.json

# 题型分类 / 答案键
python scripts/answer_key_evaluator.py --validate <答案键.json>    # 畸形键→结构化错误(rc=1但JSON含error)
python scripts/question_type_classifier.py "<学生答案文本>" --answer-key <键.json>   # ⚠️ 位置参数是字面文本，不是文件路径

# 校准（quick 与全量结果不同，务必分开记录，见方向6）
python scripts/calibrate_scoring.py --quick
python scripts/calibrate_scoring.py

# 本地法条检索（⚠️ 检索 reference/legal_knowledge_base.json，非 5515 案例库）
python scripts/legal_db_fetcher.py --search "故意伤害"     # 命中刑法234条
python scripts/legal_db_fetcher.py --search "民间借贷"     # 0 结果（KB 结构所致）

# 法考 PDF 解析（需真实真题 PDF，PyMuPDF）
python scripts/exam_parser.py <2022真题.pdf> --type objective
```

---

### 方向 4：五大模块功能测试（Level 3）

#### 模块 A — AI 回答审核（核心，三阶段）
- 阶段1 检测：24 模式逐一验证；严重度分级（F1/F3/F5/F18/F24=🔴，F2/F4/F6/...=🟠）
- 阶段2 纠正：每个 fired 模式断言 `empirical_evidence.test_case` 非空（铁律1）
- 阶段3 安全：8 项清单 C1-C8 逐项状态；C1（引法条未标核实渠道）→fail
- 附加：确定性——同输入跑两次逐字节一致（铁律8）

#### 模块 B — 提问优化（5 模板 + 4 竞赛场景）
```bash
python scripts/template_matcher.py "审核一下这份教学大纲是否符合国家标准"   # 教学大纲审核→T1+T4 ✓
python scripts/template_matcher.py "帮我出份试卷"                            # 智能考试设计→T3+T5
python scripts/template_matcher.py "两个批次的评分尺度是否一致"               # 评分一致性→T5+T4
python scripts/template_matcher.py "做一次合规审核"                          # 合规审核→T1+T4
```

#### 模块 C — 作业评估（8 题型 + 红线 + 归一化）
- **红线（实测 PASS）**：`根据《民法通则》第108条...` → D1=0, 总分 0
- **红线盲区（缺陷）**：`人格权侵害惩治条例`（F1 虚构法条）**不触发**归零
- **主观题归一化（实测 PASS）**：T8 raw 18.7/25 → 74.8 → "及格"而非"不及格"
- 8 题型路由：用 benchmark 16 项题干喂 `question_type_classifier`，T1/T2 需正确区分

#### 模块 D — 三维规制评估（⚠️ 未实现）
```bash
grep -rl "three_d_regulation" scripts/   # 仅 correction_engine 引用它补 regulation_reference
```
**结论**：无任何脚本产出 radar/评估报告，只能靠 LLM 读 JSON 手工输出——**记为一等缺陷，无法自动化测试**。

#### 模块 E — 教学大纲合规（F24）
- F24 阈值边界：覆盖 5/8 知识点 → fired(0.62)；覆盖全部 8 项 → 不 fired
- **关键事实**：detector 用 `failure_patterns.json` 硬编码 8 项，**不读** `curriculum_requirements.json` 的 18 项
- 无独立报告生成脚本，报告装配在 prompt 层

---

### 方向 5：集成 / 端到端（Level 4）

现成清单 `tests/integration_cases.json` 定义 TC001-TC015，但**无运行器**，需手工复现：

| 用例 | 覆盖 | 复现方式 | 实测现状 |
|------|------|---------|---------|
| TC001-003 | 模块A | `failure_detector` 三样本 | TC003 误报 FAIL |
| TC004-006 | 模块B | `template_matcher "<问题>"`（传文本！） | 逐句传文本 PASS |
| TC007-008 | 模块C | v1/v2 评估器 | PASS（74.6分；红线归零） |
| TC009 | 模块D | 无脚本 | **FAIL（未实现）** |
| TC010 | 全流程 | 检测\|纠正 管道 | **Windows 编码断链 FAIL** |
| TC011-015 | T1/T2/T3/T8 | v2 + 答案键 | TC011 T1 可能误判 T3 |

**建议**：三阶段链路一律用**中间文件**串联（`run_smoke.py` 的 I1 已演示正确做法），Windows 管道会因 UTF-8/GBK 断链。

---

### 方向 6：校准与回归基准复现（Level 5）⭐ 最重要

```bash
python scripts/calibrate_scoring.py --quick   # = 100% / MAE 0.0 / 召回100% / A   → 复现 v4.0/v4.2 声明 ✓
python scripts/calibrate_scoring.py           # = 68.8% / MAE 0.33 / 召回59.3% / C → 无法复现 v4.1 "16/16" ✗
```

**校准盲区**（基准只测召回、不罚误报）：
- `failure_detection.details` 里额外误报极多（如 REG-002 expected=[F17] 实际 fired 5 个）
- `BM-T2-002` 多选答案键存成 LIST、评分器要 string → 误判 T1、0 分 vs 期望 2 分
- `MAE 0.0` 仅覆盖 6 道客观题且用正确答案自构学生回答

**对外宣称口径**：若需宣称"100%/A"，必须注明"仅 4 项快速模式"。

---

### 方向 7：边界 / 异常 / 负例（Level 6）

| 用例 | 输入 | 预期 | 实测 |
|------|------|------|------|
| 空文件 | 空文本 → 检测/评估 | 结构化错误 | 待补 |
| 畸形答案键 | 缺 qtype 字段 | 明确 error | ✅（rc=1 但 JSON 含 error） |
| 缺失文件 | 不存在路径 | 结构化 error 非 traceback | 待补 |
| 超长作业 | >32767 字符 | v2 进程内检测不受限 | 待补 |
| **负例误报** | 干净的 AI 回答 | 0 触发 | ❌ F1/F17/F24 误报 |
| **编码边界** | 管道 UTF-8→GBK | 不报错 | ❌ JSONDecodeError |
| 确定性 | 同输入×2 | 逐字节一致 | ✅ |

---

### 方向 8：性能测试（Level 7）

依据 `产品技术文档/04_功能及性能指标.pdf` 声称指标：
- 失效检测 ≤ **3s**；作业评估 ≤ **45s**（`time python ...` 实测取均值）
- 长文本：生成 5 万字作业，验证不触发命令行 32767 限制
- 校准全量：实测 **0.1s**（v4.2 进程内检测 + JSON 缓存生效）

### 方向 9：文档 / 打包一致性（Level 8）
```bash
cd 产品技术文档 && python gen_docs.py && cd ..   # 重新生成 5 个 PDF（版本号 v4.2.1）
grep -c "v1.0.0" templates/*.md                  # 模板 footer 仍硬编码 v1.0.0（文档陈旧）
```

---

## 四、自动化运行器使用说明

```bash
cd "$LG"
python tests/run_smoke.py               # 全量（35 项，约 1-2 分钟）
python tests/run_smoke.py --quick       # 跳过全量校准（33 项，约 20-40 秒）
python tests/run_smoke.py --verbose     # 失败项打印详情
python tests/run_smoke.py --no-report   # 不写 tests/smoke_report.md
```

**状态位语义**：
- `PASS` —— 符合预期
- `FAIL` —— 意外失败（**影响退出码**）
- `KNOWN` —— 已记录已知缺陷（不影响退出码，用于"缺陷存在的守卫"）
- `SKIP` —— 被 `--quick` 跳过

退出码 `0` = 无意外失败；`1` = 存在意外失败。可在 CI 里作为门禁：`python tests/run_smoke.py && echo "SKILL OK"`。

---

## 五、实测 PASS/FAIL 报告（2026-08-11）

运行 `python tests/run_smoke.py` 全量结果：**PASS=28　FAIL=0　KNOWN=7　共 35 项，退出码 0**

> 注：上表为 **full 模式**数字。`--quick` 模式跳过两个校准项（S13/S14），为 **PASS=27 / KNOWN=6 / SKIP=2**，其余不变。

| 组 | 通过 | 已知缺陷 |
|----|------|---------|
| ENV 环境与元数据 (E1-E5) | 5 | — |
| DATA 数据资产完整性 (D1-D10) | 7 | D8/D9/D10（元数据矛盾 + v2.0.0 残留） |
| SMOKE 脚本冒烟 (S1-S20) | 13 | S3/S4/S5/S14（误报 + F2 死代码 + 全量校准 C 级） |
| INTEG 集成链路 (I1-I2) | 2 | — |

> 完整明细见 `tests/smoke_report.md`。

---

## 六、已知问题清单

| # | 严重度 | 问题 | 影响 | 复现 |
|---|--------|------|------|------|
| 1 | 🔴 | F1 误报：提及"民法通则"即命中 repealed_law，不区分"AI 主动纠正废止"与"AI 沿用废止法" | 干净回答被判 critical；TC003 回归必失败 | `failure_detector sample_ai_response_clean.json` |
| 2 | 🔴 | F17 误报：含显式"大前提/小前提/结论"仍命中"三段论缺失"(0.9) | 高质量回答被误伤 | 干净三段论文本 |
| 3 | 🔴 | F2 死代码：`detect_f2()` 匹配中文罪名但比对英文键 → 永不触发 | "罪名定性降维"功能失效 | 含"仅分析故意伤害罪"文本 |
| 4 | 🔴 | 全量校准 C 级（68.8%/0.33/59.3%），SKILL.md 却宣称"v4.1 16/16 100%" | 对外指标夸大 | `calibrate_scoring.py`（无 --quick） |
| 5 | 🟠 | 红线不一致：F1 虚构法条命中不归零 D1，仅"已废止"子串触发 | 与 `question_type_rubrics.json` red_lines 文档矛盾 | v2 评估 `人格权侵害惩治条例` 文本 |
| 6 | 🟠 | 模块 D 三维规制评估未实现：无脚本产出报告 | 功能不可用 | `grep three_d_regulation scripts/` |
| 7 | 🟠 | 模块 E 不读 `curriculum_requirements.json`（18 项），F24 用硬编码 8 项 | 教学大纲审核数据源错位 | 检查 `detect_f24()` 数据源 |
| 8 | 🟠 | Windows 管道断链：检测(UTF-8) \| 纠正(GBK) → JSONDecodeError | TC010 在 Windows 失败 | 管道组合测试 |
| 9 | 🟡 | reference/ 内 4 个 v2.0.0 陈旧文件（case_chunks=900、train=1440、val=360、case_knowledge_base=900） | 与 5515 声明不符，易误导下游 | 数据核对 |
| 10 | 🟡 | `legal_db_fetcher` 检索的是法条知识库，非 5515 案例库；`chunks.json` 无消费脚本 | "5515 案例 RAG 检索"实际无执行路径 | `--search "民间借贷"`=0 结果 |
| 11 | 🟡 | benchmark `meta.total_items=50` 与实 26 项不符；T3 默认满分=1、带理由满分=3（SKILL.md 表写"1+2"是满分口径，`max_score_default` 字段未注明口径） | 元数据/口径不一致 | JSON 核对 |
| 12 | 🟡 | `.skill` 内中文文件名（刑事/民事.json）解压乱码 | 按名查找失败 | zip 解压 |
| 13 | 🟡 | `integration_cases.json` 无运行器，TC004-006 传"路径"与 `template_matcher` 传"文本"接口不符 | 清单不可直接执行 | 手工复现 |
| 14 | 🟡 | 模板 footer 硬编码 v1.0.0；v1 评估器仍报"10 大失效模式"（应 24） | 文档陈旧 | `grep` |

**根因备注**（经对抗性评审 + 代码逐行确认）：
- **F1 误报**：`detect_f1()` 是整体子串匹配（`if law in text`），不检测"已废止/已被取代/已失效"等**纠正信号**——干净回答只因出现"民法通则"四字即被标记。修复方向：嫌疑法条命中旁做纠正文语境豁免。
- **F2 死代码**：`detect_f2()` 的 `rel` 字典键是**英文**（`'intentional injury': ...`），而罪名列表是中文——`sc in rel` 对中文罪名**恒为 False**，任何中文文本都不会触发。修复方向：把 `rel` 键改为中文罪名。
- **F17 误报**：`conclusion_words` 缺"**结论**"，且不识别显式"大前提/小前提/结论"标记——完整三段论仍被当缺失。修复方向：补关键词 + 显式标记豁免。
- **红线不一致**：`law_assignment_evaluator.py` 用硬编码 3 项废止法列表（民法通则/经济合同法/治安管理处罚条例），与 F1 检测器**完全解耦**；`question_type_rubrics.json` 承诺的"F1触发 ⇒ D1 0分"未真正落地。修复方向：评估器直接消费检测器输出而非自维护残缺列表。
- **RAG 无执行路径**：`legal_db_fetcher.py` 检索 `legal_knowledge_base.json`（法条库）；`test_data/rags/chunks.json`（5515 块）**无任何脚本消费**。修复方向：新增案例 RAG 检索脚本或下调 SKILL.md 声明。

---

## 七、建议的下一步改进

1. **修 F1/F17/F2**（缺陷 1/2/3，最高优先）：F1 需判断"AI 是否已纠正废止"（如命中"已废止/已被取代"关键词则豁免）；F17 需识别"大前提/小前提/结论"显式标记；F2 需把比对键改为中文罪名。
2. **校准口径修正**（缺陷 4）：SKILL.md 校准表改为区分 `--quick(4项)` 与全量(26项) 两行，如实标注 C 级并附改进方向。
3. **红线统一**（缺陷 5）：让 F1 检测结果与评分红线联动（检测命中即 D1 归零），而非仅子串匹配。
4. **补案例检索入口**（缺陷 10）：为 `chunks.json`/`all_cases.json` 写一个真正的案例 RAG 检索脚本，或明确把 `legal_db_fetcher` 定位为法条检索器。
5. **清 v2.0.0 残留**（缺陷 9）：删除/更新 reference/ 下 4 个陈旧文件。
6. **修 Windows 编码**（缺陷 8）：子进程统一 `PYTHONIOENCODING=utf-8`（`run_smoke.py` 已示范）。
7. **补负例回归集**：把 clean 样本 + F2/F17 触发器收进 `tests/test_data/`，防误报回归。
8. **CI 门禁**：`python tests/run_smoke.py` 作为版本发布的必跑检查。
