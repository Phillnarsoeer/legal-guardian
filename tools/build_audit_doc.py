#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 LegalGuardian v5.0.0 审计与升级报告（DOCX）。"""

import os
from datetime import date

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor


DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
OUT = os.path.join(DESKTOP, "LegalGuardian_v5.0.0_审计报告_2026-10-27.docx")

NAVY = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x5B, 0x66, 0x73)
LIGHT = "EAF0F6"
HEADER = "1F3A5F"


def set_run_font(run, name="宋体", size=10.5, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def add_table(doc, headers, rows, widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if widths:
        for i, w in enumerate(widths):
            for cell in table.columns[i].cells:
                cell.width = Cm(w)
    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(text)
        set_run_font(run, "黑体", font_size, True, RGBColor(0xFF, 0xFF, 0xFF))
        shade(hdr[i], HEADER)
    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(text))
            set_run_font(run, "宋体", font_size)
    doc.add_paragraph()
    return table


def para(doc, text, bold=False, size=10.5, color=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.35
    run = p.add_run(text)
    set_run_font(run, "宋体", size, bold, color)
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    run = p.add_run(text)
    set_run_font(run, "宋体", 10.5)
    return p


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.1
    run = p.add_run(text)
    set_run_font(run, "Consolas", 8.5)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F2F4F7")
    pPr.append(shd)
    return p


def heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    run = h.add_run(text)
    set_run_font(run, "黑体", 16 if level == 1 else 12.5, True, NAVY)
    h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(6)


def note_box(doc, title, lines, fill=LIGHT):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    shade(cell, fill)
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(title)
    set_run_font(run, "黑体", 10.5, True, NAVY)
    for line in lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_run_font(run, "宋体", 9.5)
    doc.add_paragraph()


def add_page_number(paragraph):
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)


def build():
    doc = Document()

    # 页面设置
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    # 默认样式
    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    # 页眉页脚
    header = section.header.paragraphs[0]
    header.text = ""
    run = header.add_run("LegalGuardian v5.0.0 · 审计与升级报告")
    set_run_font(run, "宋体", 8.5, False, GREY)
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    footer = section.footer.paragraphs[0]
    footer.text = ""
    run = footer.add_run("内部文档 · 2026-10-27 · 第 ")
    set_run_font(run, "宋体", 8.5, False, GREY)
    add_page_number(footer)
    run = footer.add_run(" 页")
    set_run_font(run, "宋体", 8.5, False, GREY)
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 封面
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("LegalGuardian")
    set_run_font(run, "黑体", 30, True, NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("v5.0.0 审计与升级报告")
    set_run_font(run, "黑体", 22, True, NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("从法条时效、5×4 逻辑矩阵到 VeriCoT 完整版")
    set_run_font(run, "宋体", 13, False, GREY)

    doc.add_paragraph()
    doc.add_paragraph()
    info = [
        ("报告日期", "2026-10-27"),
        ("审计对象", "LegalGuardian 法律守卫 Skill"),
        ("版本", "v5.0.0"),
        ("代码仓库", "https://github.com/Phillnarsoeer/legal-guardian"),
        ("发布分支", "v5.0.0（默认分支）"),
        ("发布资产", "legal-guardian-v5.0.0.skill"),
        ("审计结论", "可用于教学演示与辅助审核；不构成终局法律判断"),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in info:
        cells = table.add_row().cells
        cells[0].width = Cm(4.2)
        cells[1].width = Cm(11.0)
        shade(cells[0], LIGHT)
        p = cells[0].paragraphs[0]
        run = p.add_run(k)
        set_run_font(run, "黑体", 9.5, True, NAVY)
        p = cells[1].paragraphs[0]
        run = p.add_run(v)
        set_run_font(run, "宋体", 9.5)

    doc.add_page_break()

    # 摘要
    heading(doc, "摘要", 1)
    para(doc, "本次审计覆盖 LegalGuardian 的法条时效性、逻辑评估、语义复核、形式化验证、"
              "数据源合规、测试与发布链路。审计发现：旧版把“法条时效”简化为关键词命中、把“逻辑性”"
              "简化为关键词加分，且同一失效模式在多个维度重复计分；语义四格没有执行路径，"
              "VeriCoT 只有结构校验。上述问题会导致“看起来有分、但解释不了错误”。")
    para(doc, "v5.0.0 的处置思路是“先拆边界，再加检查点”：法条时效改为离线链接 + 人工核验 + 留痕；"
              "逻辑评估改为 5×4 矩阵 + 根因去重 + 主责维度；语义四格改为复核包 + 低置信度队列；"
              "形式化验证升级为 FOL 解析 + 有限域接地 + DPLL 蕴涵检查，并输出步骤 trace 与反例模型。")
    note_box(doc, "审计结论（一句话）", [
        "v5.0.0 已从“关键词审核”升级为“可定位、可复现、可形式化验证”的审核链路；"
        "但语义抽取仍由宿主模型完成，真实精度仍需双人标注集校准。",
    ])

    # 1 范围与方法
    heading(doc, "1. 审计范围与方法", 1)
    para(doc, "审计对象为 LegalGuardian v4.3.0 至 v5.0.0 的完整工作区，包含 SKILL.md、manifest、"
              "scripts/（20 个脚本）、reference/（12 个运行时 JSON）、templates/、panel/、tests/ 与安装包。"
              "审计同时对照 2025–2026 年法律推理研究，避免只做“工程修补”而偏离方法学。")
    add_table(doc,
              ["审计维度", "审计内容", "方法"],
              [
                  ["法条时效", "法条存在性、废止/修订、条文号、数据源合规", "文档审查、robots/条款核验、代码走查"],
                  ["逻辑评估", "评分规则、维度映射、重复计分、可解释性", "代码走查、样本回放、矩阵设计"],
                  ["语义复核", "争点/事实/推理/边界四格", "复核包设计、合并协议、低置信度队列"],
                  ["形式化验证", "FOL 表达、接地、蕴涵、反例", "解析器/DPLL 实现、单元测试、反例验证"],
                  ["测试与发布", "回归、校准、安装包、GitHub 发布", "冒烟测试、单元测试、Release 验证"],
              ],
              widths=[3.0, 8.0, 5.0])
    para(doc, "外部研究对照包括：System L（AAAI-26，双系统过度简化、IRAC 骨架）、IRAC-R1（ICML-26，"
              "结构化 IRAC 优于泛化 CoT）、VeriCoT（ICLR-26，CoT 形式化 + solver）、L-MARS（ICML-26，"
              "引用忠实度审计）、NALOMA 2025（大题拆子问题）、NLLP 2025（LLM 形式论证抽取仍弱）。")

    # 2 发现
    heading(doc, "2. 审计发现与风险登记", 1)
    para(doc, "下表按“风险—证据—处置”记录本次审计的主要发现。严重度用于排序，不替代法律判断。")
    add_table(doc,
              ["编号", "发现", "严重度", "证据", "v5.0.0 处置"],
              [
                  ["A1", "法条时效性不是权威核验：旧版只靠关键词与静态废止清单，无法证明条文号存在、版本最新。", "高",
                   "F1/F5 检测逻辑；legal_db_fetcher 在线模式依赖浏览器自动化。", "新增 statute_verifier.py：官方链接 + 五项清单 + 人工结论留痕；不爬取。"],
                  ["A2", "逻辑评分可被关键词套利：写入“大前提/小前提/结论”即可加分，检测不到矛盾与跳跃。", "高",
                   "scoring_engine.score_logic、law_assignment_evaluator D2。", "新增 5×4 矩阵 + 8 项确定性筛查；分数由 issue 计算。"],
                  ["A3", "维度映射重复计分：F7 同时进准确性与逻辑性，F1 同时进准确性与时效性。", "高",
                   "failure_patterns.dimension_mapping。", "一错一主责：M22 归准确性红旗，不扣逻辑分；根因去重。"],
                  ["A4", "语义四格没有执行路径：概念偷换、事实错认、因果误判、边界误用无法落地。", "高",
                   "原 D2 仅关键词；无 M12/M32/M42/M52。", "新增语义复核包 + --semantic-input 合并 + 低置信度队列。"],
                  ["A5", "无法形式化验证：结论“看起来对”但推不出来，缺少反例。", "中高",
                   "原 VeriCoT-lite 只做结构校验。", "新增 fol_engine.py + VeriCoT 完整版：FOL→接地→DPLL→反例。"],
                  ["A6", "数据源合规风险：flk.npc.gov.cn 的 robots 禁止自动化采集；官方无公开 API/密钥。", "高",
                   "robots.txt；无官方开发者接口。", "不爬取；只生成官方检索链接；人工核验并记录来源与时间。"],
                  ["A7", "报告面板不显示逻辑体检：JSON 有 logic，但前端忽略。", "中",
                   "panel/report_panel.html 原无 renderLogic。", "新增“I · 逻辑体检”页签：KPI、热力图、issue、红旗、派生标记。"],
                  ["A8", "测试基准合成化：0 误报/1.0 召回来自自写 fixture，不能代表真实精度。", "高",
                   "logic_eval.py 20 条合成样本。", "明确标注为合成校准；路线图要求 50–100 条双人标注。"],
              ],
              widths=[1.2, 6.3, 1.5, 4.2, 4.2],
              font_size=8.5)

    # 3 设计
    heading(doc, "3. 关键设计决策", 1)
    heading(doc, "3.1 法条时效：从“爬取”改为“链接 + 人工 + 留痕”", 2)
    para(doc, "官方数据库没有公开 API，robots 明确禁止自动化采集；用 Playwright 批量抓取既不稳定，也会把"
              "合规风险带入产品。v5.0.0 改为：生成官方检索入口与检索词 → 人工核对五项清单 → 用 --record "
              "写入本地 JSONL。脚本只做离线预检（废止法、虚构法、条文号越界），不自动下结论。")
    bullet(doc, "记录默认存于 ~/.legalguardian/verifications.jsonl，含核验人、时间、结论、检索词与种子版本。")
    bullet(doc, "预检只覆盖高频核心法（38 部法律/司法解释 + 十余部废止法 + 2 个虚构/错名），不冒充全量法规库。")
    bullet(doc, "报告区分 seed / manual / official 三种状态，未核验不得写“已官方核验”。")

    heading(doc, "3.2 逻辑评估：5×4 矩阵 + 一错一主责", 2)
    para(doc, "逻辑混乱不是一个维度，而是“前提不真、推理无效、结构不全、前后不一致”四件事。"
              "v5.0.0 用 5 个阶段（争点/规范/事实/涵摄/边界）× 4 种失效（缺失/错误/矛盾/溢出）组成 20 个单元，"
              "每个单元有定义、严重度、F 映射、信号、反例与修正。")
    add_table(doc,
              ["层", "单元", "典型表现", "主责维度"],
              [
                  ["争点", "M11–M14", "争点缺失/错位/冲突/溢出", "逻辑"],
                  ["规范", "M21–M24", "规范缺失/失效/冲突/堆砌", "M22 准确性；其余逻辑"],
                  ["事实", "M31–M34", "要件事实缺失/错认/矛盾/无关", "M32 准确性；其余逻辑/深度"],
                  ["涵摄", "M41–M44", "推理缺环/错误/结论矛盾/结论先行", "逻辑"],
                  ["边界", "M51–M54", "例外遗漏/边界误用/原则规则冲突/结论溢出", "M52 准确性；其余逻辑"],
              ],
              widths=[2.2, 3.4, 7.4, 4.6])
    para(doc, "评分公式：5.0 起扣；critical 2.0 / major 0.8 / minor 0.3 / hint 0.1；"
              "存在 critical 时逻辑分封顶 2.0，存在 M43 时封顶 2.5；跨维度问题只作红旗，不进逻辑分。"
              "根因去重：L02→L04、L03→L04 在 300 字窗口内标 derived_from，后果不重复扣分。")

    heading(doc, "3.3 语义四格：复核包 + 低置信度队列", 2)
    para(doc, "语义判断不交给关键词，也不伪装成自动模型。--semantic 生成四格复核包（M12 争点错位、"
              "M32 事实错认、M42 推理错误、M52 边界误用），每格给出通过/失败标准、所需证据与修正建议；"
              "宿主模型或人工填写 review.json，--semantic-input 合并进逻辑体检。")
    code(doc, '{\n  "reviews": [\n    {"cell": "M12", "verdict": "fail",\n'
              '     "evidence": "原文逐字片段", "why": "题目问合同效力，文本却分析侵权",\n'
              '     "fix": "回到合同效力争点", "confidence": 0.82}\n  ]\n}')
    para(doc, "规则：pass 不产生 issue；fail 产生 major issue；unclear 进入低置信度队列，不重扣。"
              "低于阈值（默认 0.6）的 issue 自动进 human_queue，可用 --queue-out 导出 JSONL。")

    heading(doc, "3.4 VeriCoT 完整版：抽取与验证分离", 2)
    para(doc, "完整版把“语言模型抽取”与“符号验证”分开：宿主模型把论证拆成 premises/steps/conclusion "
              "并写 FOL formula；脚本负责 FOL 解析、有限域接地、DPLL 可满足性/蕴涵检查。"
              "这符合 VeriCoT 的分工，而不是让一个脚本同时做 NL 理解和定理证明。")
    add_table(doc,
              ["模块", "职责", "输出"],
              [
                  ["folio_engine.py", "FOL 解析、接地、DPLL、蕴涵、反例", "entailed / not_entailed / undecided"],
                  ["vericot_check.py", "结构校验 V1–V9 + 形式化 V10–V18", "valid、score、issues、步骤 trace"],
                  ["--packet", "生成抽取模板（premises/steps/conclusion + formula）", "JSON 模板 + 填写说明"],
              ],
              widths=[4.0, 8.2, 5.4])
    para(doc, "支持：原子、¬/∧/∨/→/↔、forall/exists；函数无关、有限域；不支持函数符号与等词。"
              "原子数超过 2000 时返回 undecided，不假装证明。")

    # 4 实现
    heading(doc, "4. 实现清单与命令", 1)
    add_table(doc,
              ["文件", "作用"],
              [
                  ["scripts/statute_verifier.py", "法条时效人工核验：链接、清单、JSONL 留痕"],
                  ["scripts/logic_linter.py", "逻辑体检：8 项筛查、5×4 热力图、语义包、队列、批量、去重、条号越界"],
                  ["scripts/fol_engine.py", "FOL 解析/接地/DPLL 引擎"],
                  ["scripts/vericot_check.py", "VeriCoT 完整版：lite/full 自动切换、V1–V18、步骤 trace"],
                  ["reference/logic_taxonomy.json", "20 个矩阵单元 + 8 项检查 + 4 个语义格"],
                  ["reference/logic_rubric.json", "主责矩阵、评分锚点、去重依赖、指标目标"],
                  ["reference/statutes_seed.json", "38 部核心法/司法解释、十余部废止法、2 个虚构/错名"],
                  ["templates/irac_scaffold.md", "生成侧 IRAC 脚手架"],
                  ["templates/logic_review_template.md", "复核报告模板（矩阵/issue/修复顺序）"],
                  ["panel/report_panel.html", "新增“I · 逻辑体检”页签"],
                  ["tests/", "单元测试 + 20 条 fixture + 冒烟 44 项"],
              ],
              widths=[6.2, 11.4],
              font_size=9)
    code(doc,
         "# 法条核验\n"
         "python scripts/statute_verifier.py --law \"民法典\" --article \"第1165条\"\n"
         "python scripts/statute_verifier.py --law \"民法典\" --article \"第1165条\" \\\n"
         "    --record --verdict active --verifier \"张三\" --note \"官网核对\"\n\n"
         "# 逻辑体检 / 语义四格 / 队列 / 批量\n"
         "python scripts/logic_linter.py case.md --mode ai_audit\n"
         "python scripts/logic_linter.py case.md --semantic --question \"请分析侵权责任\"\n"
         "python scripts/logic_linter.py case.md --semantic-input review.json --json\n"
         "python scripts/logic_linter.py --batch ./homework --out results.jsonl\n"
         "python scripts/logic_linter.py case.md --queue-out queue.jsonl\n\n"
         "# VeriCoT 完整版\n"
         "python scripts/vericot_check.py --packet --text \"<原文>\"\n"
         "python scripts/vericot_check.py argument.json --json")

    # 5 验证
    heading(doc, "5. 验证结果", 1)
    add_table(doc,
              ["验证项", "结果", "说明"],
              [
                  ["全量冒烟", "44 / 44 通过", "0 FAIL / 0 KNOWN / 0 SKIP（全量模式）"],
                  ["逻辑体检单元测试", "20 / 20 通过", "矩阵、CLI、评分、语义、批量、队列、去重、条号越界"],
                  ["VeriCoT 单元测试", "全部通过", "lite + full；V2/V3/V5/V10/V14/V15/V16/V17"],
                  ["FOL 引擎单元测试", "8 / 8 通过", "modus ponens、全称三段论、反例、矛盾、量词、元数、自由变量"],
                  ["法条核验单元测试", "12 / 12 通过", "卡片、预检、记录、列表、统计、条号越界"],
                  ["合成 fixture 校准", "0 误报 / 1.0 召回", "20 条自写样本；不代表真实分布"],
                  ["安装包", "59 个文件 / 0.28MB", "不含 test_data 与产品技术文档"],
              ],
              widths=[4.0, 4.2, 9.4])
    note_box(doc, "验证边界", [
        "合成 fixture 的完美指标只说明规则与样本自洽，不能当作真实精度。",
        "正式使用前需 50–100 条双人标注样本，测 precision/recall/FPR/kappa/score MAE。",
        "FOL 验证的瓶颈在 NL→FOL 抽取，不在 DPLL；抽取质量需单独评估。",
    ])

    # 6 限制
    heading(doc, "6. 已知限制", 1)
    limits = [
        ("语义抽取依赖宿主模型", "四格复核包需要模型/人工填写；脚本只做校验、合并与队列，不自动理解语义。"),
        ("FOL 是函数无关有限域", "不支持函数符号与等词；常量/谓词多时原子数爆炸，超过 2000 返回 undecided。"),
        ("FOL 是单调逻辑", "法律“但书/例外”需显式写成 Rule(x) ∧ ¬Exception(x) → Conclusion(x)；defeasible reasoning 未内建。"),
        ("种子库覆盖有限", "38 部核心法/司法解释、十余部废止法；未收录的地方法规/规章需人工核验。"),
        ("真实精度未知", "20 条 fixture 为合成样本；尚未完成双人标注校准。"),
        ("跨文档一致性未实现", "M33/M43 需要同一学生的多题答案；当前 batch 逐文件独立分析。"),
        ("安装副本可能漂移", "当前会话加载的技能副本在独立目录；需重新安装 legal-guardian.skill 才生效。"),
    ]
    for title, text in limits:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run("• " + title + "：")
        set_run_font(run, "黑体", 10.5, True, NAVY)
        run = p.add_run(text)
        set_run_font(run, "宋体", 10.5)

    # 7 路线
    heading(doc, "7. 后续路线", 1)
    add_table(doc,
              ["优先级", "事项", "完成标准"],
              [
                  ["P0", "真实标注集与校准", "50–100 条双人标注；precision≥0.80、recall≥0.70、FPR<0.10、kappa≥0.70"],
                  ["P0", "语义四格真实校准", "M12/M32/M42/M52 分格 precision/recall；错误样本归因"],
                  ["P1", "跨文档一致性", "同一学生多题答案联合分析；检测 M33/M43 矛盾"],
                  ["P1", "数值扩展", "利息/LPR/日期/单位换算；公式与中间结果留痕"],
                  ["P2", "NL→FOL 抽取质量", "原文→金标 formula 样本；抽取一致性评估"],
                  ["P2", "Defeasible 逻辑", "Exception/Defeated 谓词模板；但书可被证明器处理"],
              ],
              widths=[1.8, 6.4, 9.4])

    # 8 发布
    heading(doc, "8. 发布信息", 1)
    add_table(doc,
              ["项目", "内容"],
              [
                  ["GitHub 仓库", "https://github.com/Phillnarsoeer/legal-guardian"],
                  ["默认分支", "v5.0.0"],
                  ["提交", "d4e610b"],
                  ["Release", "https://github.com/Phillnarsoeer/legal-guardian/releases/tag/v5.0.0"],
                  ["发布资产", "legal-guardian-v5.0.0.skill"],
                  ["安装包", "legal-guardian.skill（同内容，兼容旧安装路径）"],
              ],
              widths=[3.4, 14.2])
    para(doc, "发布前已在本仓库运行全量冒烟 44/44；安装包校验通过：不含 test_data 与产品技术文档，"
              "中文文件名无乱码。")

    # 附录
    doc.add_page_break()
    heading(doc, "附录 A：审计证据索引", 1)
    add_table(doc,
              ["证据", "位置"],
              [
                  ["24 种失效模式定义", "reference/failure_patterns.json"],
                  ["逻辑矩阵与 8 项检查", "reference/logic_taxonomy.json"],
                  ["评分/主责/去重/指标", "reference/logic_rubric.json"],
                  ["法条核验种子库", "reference/statutes_seed.json"],
                  ["逻辑体检实现", "scripts/logic_linter.py"],
                  ["FOL 引擎", "scripts/fol_engine.py"],
                  ["VeriCoT 实现", "scripts/vericot_check.py"],
                  ["冒烟测试", "tests/run_smoke.py"],
                  ["逻辑/FOL/VeriCoT 测试", "tests/test_logic_linter.py, test_fol_engine.py, test_vericot_check.py"],
                  ["测试方案", "tests/LegalGuardian_v5.0.0功能测试方案.md"],
              ],
              widths=[7.0, 10.6])

    heading(doc, "附录 B：审计声明", 1)
    para(doc, "本报告是工程与教学审计文档，不构成法律意见，也不替代律师、教师或评审专家的最终判断。"
              "报告中的分数、阈值与指标是当前实现的校准目标，不是对真实世界准确率的承诺。"
              "涉及法规时效、案例引用与量刑结论时，必须以官方渠道与人工复核为准。")

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(path)

