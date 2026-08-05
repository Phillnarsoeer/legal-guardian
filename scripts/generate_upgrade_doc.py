#!/usr/bin/env python3
"""Generate LegalGuardian v1.0→v4.0 Upgrade Summary Word Document"""
import sys
import os
import datetime

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def set_run_font(run, size=None, bold=None):
    """统一设置 run 字体：微软雅黑（含东亚字体）与字号，保持输出一致"""
    run.font.name = 'Microsoft YaHei'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    return run


def main():
    doc = Document()

    # Page setup
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    font = style.font
    font.name = 'Microsoft YaHei'
    font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    def add_heading(text, level=1):
        h = doc.add_heading(text, level=level)
        for run in h.runs:
            set_run_font(run)
        return h

    def add_para(text, bold=False, size=10.5):
        p = doc.add_paragraph()
        set_run_font(p.add_run(text), size, bold)
        return p

    def add_table(headers, rows, col_widths=None):
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = 'Light Grid Accent 1'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(9)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                cell = table.rows[r+1].cells[c]
                cell.text = str(val)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
        doc.add_paragraph()
        return table

    # ===================== TITLE PAGE =====================
    doc.add_paragraph()
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = set_run_font(title.add_run('法律守卫 LegalGuardian'), 28, True)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = set_run_font(subtitle.add_run('v1.0 → v4.0 版本演进技术白皮书'), 18)

    doc.add_paragraph()
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = set_run_font(info.add_run(f'西南民族大学法学院 徐子涵团队\n生成日期: {datetime.date.today()}\nGitHub: github.com/Phillnarsoeer/legal-guardian'), 11)

    doc.add_page_break()

    # ===================== TABLE OF CONTENTS =====================
    add_heading('目录', 1)
    toc_items = [
        '一、项目概述与版本总览',
        '二、v1.0.0 — 实证基线建立（2026-07-29）',
        '三、v2.0.0 — 案例知识库扩展（2026-07-30, GitHub）',
        '四、v3.0.0 — 人民法院案例库全量接入（2026-07-30）',
        '五、v4.0.0 — 全题型法学作业评估引擎（2026-07-31）',
        '六、各版本数据资产对比',
        '七、各版本脚本能力对比',
        '八、各版本失效模式覆盖对比',
        '九、升级路线图与关键技术决策',
        '十、v4.0.0校准报告',
        '十一、未来规划与改进方向',
    ]
    for item in toc_items:
        add_para(item, size=11)

    doc.add_page_break()

    # ===================== SECTION 1: OVERVIEW =====================
    add_heading('一、项目概述与版本总览', 1)

    add_para('LegalGuardian（法律守卫）是一个基于实证研究数据的AI法律对话审查纠正与法学作业评估引擎。项目建立在西南民族大学法学院徐子涵团队2026年5月完成的「生成式AI对法学生辅助学习应用的准确性、风险挑战及规制路径研究」大创项目成果之上，将14个案例×2轮测试×4维测评的实证发现转化为可落地的自动化纠正机制。')

    add_para('项目经历了四个大版本的迭代，从最初的规则引擎发展为具备5,515个真实案例知识库、18种失效模式检测、8大法学题型全场景覆盖的综合评估平台。', size=11)

    add_heading('版本演进时间线', 2)
    add_table(
        ['版本', '发布日期', '核心升级', '案例数', '失效模式', '题型支持', 'GitHub'],
        [
            ['v1.0.0', '2026-07-29', '实证基线+10大失效模式+4模块', '14', 'F1-F10 (10)', '仅案例分析', '本地'],
            ['v2.0.0', '2026-07-30', '900案例知识库+1800QA对+案由映射', '900', 'F1-F10 (10)', '仅案例分析', '✅ phillnarsoeer'],
            ['v3.0.0', '2026-07-30', '人民法院案例库5,515真实案例全量接入', '5,515', 'F1-F10 (10)', '仅案例分析', '本地'],
            ['v4.0.0', '2026-07-31', '8大题型+18失效模式+法考真题校准', '5,515', 'F1-F18 (18)', 'T1-T8全覆盖', '本地'],
        ]
    )

    # ===================== SECTION 2: v1.0.0 =====================
    add_heading('二、v1.0.0 — 实证基线建立（2026-07-29）', 1)

    add_heading('2.1 版本概述', 2)
    add_para('v1.0.0是项目的初始版本，也是所有后续升级的实证基准。该版本将西南民族大学法学院徐子涵团队2026年5月的实证研究成果——对DeepSeek和千问Qwen3.5进行14个案例×2轮测试×4维测评——转化为可落地的自动化纠正机制。')

    add_heading('2.2 核心资产', 2)
    add_table(
        ['资产类别', '文件', '功能'],
        [
            ['知识库 (reference/)', 'failure_patterns.json', '10大失效模式(F1-F10)特征库+检测关键词'],
            ['知识库', 'test_baseline.json', '14案例实证基线数据(DS:3.84 vs 千问:3.06)'],
            ['知识库', 'correction_templates.json', '5大标准化提问模板(T1-T5)'],
            ['知识库', 'safety_checklist.json', '8项AI安全使用检查清单'],
            ['知识库', 'assignment_rubric.json', '五维百分制作业评分标准'],
            ['知识库', 'legal_knowledge_base.json', '民法典+刑法核心法条(680/1165/1255等)'],
            ['知识库', 'three_d_regulation.json', '三维规制路径(T+E+L)'],
            ['脚本 (scripts/)', 'failure_detector.py', 'F1-F10规则匹配检测引擎'],
            ['脚本', 'correction_engine.py', '实证依据纠正建议生成器'],
            ['脚本', 'scoring_engine.py', '四维评分+DS/千问基线对比'],
            ['脚本', 'template_matcher.py', '提问模板智能匹配'],
            ['脚本', 'law_assignment_evaluator.py', '五维作业评分(仅案例分析)'],
            ['脚本', 'legal_db_fetcher.py', '国家法律法规数据库检索'],
        ]
    )

    add_heading('2.3 关键设计决策', 2)
    add_para('1. 知识库与逻辑分离：reference/*.json(可修改内容)与scripts/*.py(不可变逻辑)完全解耦。')
    add_para('2. 实证锚定原则：5分=DS最佳(准确性5.0)，3分=DS平均(3.84)，1分=千问引导性(1.70)。')
    add_para('3. 审核链递进设计：检测→纠正→检查三阶段，模拟律师审查文件的真实流程。')
    add_para('4. 红线规则：D1=0(引用虚构/废止法律)→总分直接归零。')
    add_para('5. 可解释可追溯：每条审核结论须标注引用自哪个实证测试案例。')

    add_heading('2.4 局限性', 2)
    add_para('• 仅支持案例分析论文一种作业类型的评估')
    add_para('• 14个测试案例覆盖面有限，10大失效模式可能未穷尽')
    add_para('• 规则引擎基于关键词匹配，缺乏真实案例数据支撑')
    add_para('• 无法处理选择题、判断题、简答题等标准化考试题型')

    doc.add_page_break()

    # ===================== SECTION 3: v2.0.0 =====================
    add_heading('三、v2.0.0 — 案例知识库扩展（2026-07-30, GitHub）', 1)

    add_heading('3.1 版本概述', 2)
    add_para('v2.0.0是项目的第一个重大数据扩展版本，也是首次对外发布到GitHub的版本(github.com/Phillnarsoeer/legal-guardian)。该版本将案例数据从14个测试案例扩展到900个结构化案例，建立了案例类型与10大失效模式的映射关系。')

    add_heading('3.2 新增资产', 2)
    add_table(
        ['新增文件', '数据规模', '功能'],
        [
            ['reference/case_knowledge_base.json', '900案例+71种案由+1800QA对', '案例知识库，含F1-F10×案由类型映射'],
            ['reference/all_1000.json', '~1000结构化案例(19,372行)', '案例详情：法院/事实/主张/判决/适用法条'],
            ['reference/case_chunks.json', '~1000 RAG检索块(5,401行)', '案例简化为检索块，支持本地RAG'],
            ['test_data/cases/民事.json', '550民事案例(35,291行)', '民事案例子集'],
            ['test_data/cases/刑事.json', '350刑事案例(31,615行)', '刑事案例子集'],
            ['test_data/case_stats.json', '统计元数据', '案例分布统计'],
        ]
    )

    add_heading('3.3 案例知识库结构', 2)
    add_para('每个案例包含以下结构化字段：')
    add_para('• id: 唯一标识符')
    add_para('• case_number: 案号（如"(2023)A9836民初7819号"）')
    add_para('• court: 审理法院')
    add_para('• category + subcategory: 案件分类（民事/刑事 × 71种案由）')
    add_para('• plaintiff/defendant: 原被告信息')
    add_para('• facts/claims/defense: 事实+主张+抗辩')
    add_para('• holding/judgment: 法院认定+判决结果')
    add_para('• laws_applied: 适用的法条列表')
    add_para('• dispute_focus/keywords: 争议焦点+关键词')

    add_heading('3.4 失效模式×案由映射', 2)
    add_para('v2.0.0的关键创新是将10大失效模式与71种案由建立了精准映射关系：')
    add_para('• F1(法条幻视) → 借款合同、买卖合同、租赁合同')
    add_para('• F2(罪名定性降维) → 故意伤害罪、寻衅滋事罪、抢劫罪')
    add_para('• F3(量刑乐观偏差) → 故意伤害罪、诈骗罪、盗窃罪、抢劫罪')
    add_para('• F4(浅度正确) → 建设工程合同、医疗损害责任纠纷、产品责任纠纷')
    add_para('• F7(计算推理不一致) → 借款合同、建设工程合同')
    add_para('这种映射使得审查纠正可以按案由类型匹配高频失效模式，实现更精准的检测。')

    add_heading('3.5 v2.0.0脚本层面', 2)
    add_para('v2.0.0的脚本层(v1.0.0的6个脚本)未做改动，仍只支持案例分析题型的评估。新增能力主要通过知识库JSON数据的加载和引用实现。')

    doc.add_page_break()

    # ===================== SECTION 4: v3.0.0 =====================
    add_heading('四、v3.0.0 — 人民法院案例库全量接入（2026-07-30）', 1)

    add_heading('4.1 版本概述', 2)
    add_para('v3.0.0是项目的数据规模飞跃版本。通过人民法院案例库(rmfyalk.court.gov.cn)官方搜索API，采用零爬虫100%合规方案（浏览器会话Cookie认证 + 官方JSON接口 + 模拟真人浏览速度），全量接入5,515个真实案例。')

    add_heading('4.2 数据规模升级', 2)
    add_table(
        ['指标', 'v2.0.0', 'v3.0.0', '增长'],
        [
            ['案例总数', '900', '5,515', '6.1×'],
            ['案由/罪名数', '71', '535', '7.5×'],
            ['训练样本(QA对)', '1,800', '27,575', '15.3×'],
            ['RAG检索块', '900', '5,515', '6.1×'],
            ['覆盖案件类型', '民事+刑事', '刑事+民事+行政+执行+国家赔偿', '全类型'],
        ]
    )

    add_heading('4.3 新增核心资产', 2)
    add_table(
        ['文件', '规模', '内容'],
        [
            ['test_data/cases/all_cases.json', '82,709行', '5,515案例完整元数据'],
            ['test_data/cases/民事.json', '35,291行', '2,353民事案例'],
            ['test_data/cases/刑事.json', '31,615行', '2,108刑事案例'],
            ['test_data/rags/chunks.json', '5,515块', '全量RAG检索块'],
            ['test_data/case_stats.json', '更新', '5,515案例分布统计'],
            ['产品技术文档/', '5份PDF', '需求分析/框架设计/测试用例/功能指标/使用手册'],
        ]
    )

    add_heading('4.4 案例数据结构（官方字段）', 2)
    add_para('每个人民法院案例库案例包含以下官方字段：')
    add_para('• no: 入库编号（如"2026-09-3-029-001"）')
    add_para('• title: 案例标题（含当事人名称）')
    add_para('• category + subcategory: 案件分类（行政/民事/执行/刑事/国家赔偿）')
    add_para('• court + province: 审理法院+省份')
    add_para('• date: 裁判日期')
    add_para('• case_id: 案号（如"（2024）最高法行申9043号"）')
    add_para('• trial: 审理程序（一审/二审/再审/执行）')
    add_para('• ruling: 裁判要旨（核心法律规则的官方提炼）——这是评估答案正确性的权威参照')

    add_heading('4.5 v3.0.0的边界', 2)
    add_para('v3.0.0实现了数据规模的量变，但评估能力尚未质变：')
    add_para('• 6个脚本与v1.0.0相同，未做功能扩展')
    add_para('• 仍仅支持案例分析论文的评估')
    add_para('• 失效模式仍为F1-F10')
    add_para('• 5,515案例的裁判要旨是理想的标准答案来源，但缺乏自动化的题目生成和答案键构建能力')

    doc.add_page_break()

    # ===================== SECTION 5: v4.0.0 =====================
    add_heading('五、v4.0.0 — 全题型法学作业评估引擎（2026-07-31）', 1)

    add_heading('5.1 版本概述', 2)
    add_para('v4.0.0是项目的功能质变版本。基于v3.0.0的5,515真实案例知识库 + 2022-2025年法考主客观真题校准，将评估能力从单一"案例分析论文"扩展到8大法学题型，失效模式从F1-F10扩展到F1-F18，新增6个脚本实现题型自动识别、路由、差异化评分和校准。')

    add_heading('5.2 8大题型支持体系', 2)
    add_table(
        ['编号', '题型', '评分方式', '需要答案键', '典型分值', '来源校准'],
        [
            ['T1', '单项选择题', '答案键精确匹配', '是', '1分/题', '法考客观题1-50题'],
            ['T2', '多项选择题', '部分得分制(少选按比例)', '是', '2分/题', '法考客观题51-85题'],
            ['T3', '判断题', '精确匹配+理由完整性', '是', '1-3分/题', '本科期末标准'],
            ['T4', '名词解释', '三维关键词覆盖(概念50%+要素30%+法源20%)', '是', '3-5分/题', '本科基础'],
            ['T5', '简答题', '采分点覆盖法', '是', '5-15分/题', '法考主观题/考研'],
            ['T6', '论述题', '五维加权(逻辑30%+深度25%+准确20%)', '建议', '30分/题', '法考主观题第一题'],
            ['T7', '法条分析题', '四维结构化(定位+背景+解构+衔接)', '建议', '20分/题', '考研法学'],
            ['T8', '案例分析题', '五维加权(准确30%+逻辑25%+深度20%)', '建议', '25分/题', '法考主观题核心'],
        ]
    )

    add_heading('5.3 18种失效模式（F1-F10 + F11-F18）', 2)
    add_table(
        ['编号', '名称', '严重度', '目标题型', '一句话定义'],
        [
            ['F1', '法条幻视', '🔴极高', '全部', 'AI接受虚构/废止法律为真实'],
            ['F2', '罪名定性降维', '🟠高', 'T6,T8', 'AI倾向轻罪定性'],
            ['F3', '量刑乐观偏差', '🟠高', 'T8', '系统性低估刑期(误差可达71%)'],
            ['F4', '浅度正确', '🔴极高', 'T4-T8', '结论对但缺乏深度法理分析'],
            ['F5', '前提验证盲区', '🔴极高', '全部', 'AI不验证用户前提是否成立'],
            ['F6', '引导性赤字', '🟠高', 'T6,T8', '缺实务操作指导'],
            ['F7', '计算推理不一致', '🟡中高', 'T8', '结论与计算示例内部矛盾'],
            ['F8', '因果关系过度简化', '🟠高', 'T6,T8', '将多因一果简化为线性因果'],
            ['F9', '国际法视野缺失', '🟡中', 'T6', '局限于国内法'],
            ['F10', '用户差异化风险盲区', '🔴极高', 'T6', '不区分法学生/非专业人士输出'],
            ['F11', '选项混淆偏误', '🟠高', 'T1,T2', '混淆可撤销vs无效等相似概念'],
            ['F12', '采分点遗漏', '🟠高', 'T5', '简答题遗漏关键采分点'],
            ['F13', '定义要素缺失', '🟡中高', 'T4', '名词解释缺少核心要素'],
            ['F14', '判对错不给理由', '🟡中高', 'T3', '判断题只写对/错不附法律依据'],
            ['F15', '法条解构不完整', '🟠高', 'T7', '缺少构成要件→法律后果映射'],
            ['F16', '论述偏离题眼', '🟡中高', 'T6', '论述题未紧扣核心争点'],
            ['F17', '三段论结构缺失', '🟠高', 'T8', '缺少大前提→小前提→结论推理'],
            ['F18', '要件事实识别错误', '🔴极高', 'T8', '混淆关键要件事实与非关键背景'],
        ]
    )

    add_heading('5.4 新增6个脚本', 2)
    add_table(
        ['脚本', '功能', '输入', '输出'],
        [
            ['question_type_classifier.py', 'T1-T8题型自动识别+路由评分', '学生答案文本+可选答案键', '题型分类+客观/半客观题评分JSON'],
            ['answer_key_evaluator.py', '答案键验证+批量客观题评分+模板生成', '答案键JSON', '验证结果/批量评分/题型模板'],
            ['law_assignment_evaluator_v2.py', '8题型统一评估器(路由+评分+检测+报告)', '作业文件+可选答案键', '完整评估报告JSON'],
            ['calibrate_scoring.py', '基于黄金标准基准测试的评分校准', '基准测试JSON', '准确率/MAE/召回率/综合评级'],
            ['exam_parser.py', '法考真题PDF→结构化答案键', '法考真题PDF', '标准答案键JSON'],
            ['failure_detector.py', '升级至F1-F18检测(原F1-F10+新增F11-F18)', '待审文本', '18模式检测结果+四维评分'],
        ]
    )

    add_heading('5.5 新增参考数据', 2)
    add_table(
        ['文件', '功能'],
        [
            ['reference/question_type_rubrics.json', '8题型差异化评分标准+答案键JSON Schema'],
            ['reference/failure_patterns.json (更新)', '新增patterns_v2(F11-F18)+dimension_mapping_v2'],
            ['benchmark/gold_standard/all_types_benchmark.json', '7项题型基准+4项回归测试'],
            ['benchmark/answer_keys/', '基于2022-2025法考真题的结构化答案键'],
        ]
    )

    add_heading('5.6 关键技术决策', 2)
    add_para('1. 题型识别优先级：T8 > T1 > T2 > T7 > T6 > T5 > T4 > T3。案例分析优先（因可能含选择题子问题），选择题次之（特征明确）。')
    add_para('2. 答案键必选vs可选：客观题(T1-T3)和半客观题(T4-T5)必须提供答案键才能评分；主观题(T6-T8)答案键可选，无答案键时仍可进行五维加权评分和失效模式检测。')
    add_para('3. 客观题评分零容忍：T1不选/多选=0分；T2多选/错选=0分，仅少选可得部分分。')
    add_para('4. 法考真题校准：2022年-2025年共8套客观题+4套主观题真题用于校准题型识别pattern和评分阈值。')
    add_para('5. 红线规则扩展：F1(法条幻视)在任何主观题题型(T4-T8)中触发→法律依据维度直接0分。')

    doc.add_page_break()

    # ===================== SECTION 6: DATA ASSETS COMPARISON =====================
    add_heading('六、各版本数据资产对比', 1)

    add_table(
        ['资产类别', 'v1.0.0', 'v2.0.0', 'v3.0.0', 'v4.0.0'],
        [
            ['测试案例', '14', '14', '14', '14'],
            ['结构化案例库', '—', '900', '900', '1,000'],
            ['人民法院案例库', '—', '—', '5,515', '5,515'],
            ['案由/罪名', '—', '71', '535', '535'],
            ['QA训练对', '—', '1,800', '27,575', '27,575'],
            ['RAG检索块', '—', '900', '5,515', '5,515'],
            ['法考真题(校准)', '—', '—', '—', '12套(8客观+4主观)'],
            ['失效模式', '10 (F1-F10)', '10 (F1-F10)', '10 (F1-F10)', '18 (F1-F18)'],
            ['支持题型', '1 (案例分析)', '1', '1', '8 (T1-T8)'],
            ['评分维度', '五维(D1-D5)', '五维', '五维', '五维+答案键+采分点+三维关键词'],
            ['reference JSON', '7', '7', '7', '8 (+question_type_rubrics)'],
            ['脚本数', '6', '6', '6', '12'],
            ['基准测试', '10用例', '10用例', '10用例', '15用例(+5)'],
        ]
    )

    doc.add_page_break()

    # ===================== SECTION 7: SCRIPT CAPABILITY COMPARISON =====================
    add_heading('七、各版本脚本能力对比', 1)

    add_table(
        ['能力维度', 'v1.0.0', 'v2.0.0', 'v3.0.0', 'v4.0.0'],
        [
            ['失效模式检测', 'F1-F10 关键词正则', '同v1 (加载900案例知识库)', '同v1 (加载5,515案例)', 'F1-F18 题型路由检测'],
            ['纠正建议生成', '实证引用+替代表述', '同v1', '同v1', '同v1 + 题型特化纠正'],
            ['AI回答评分', '四维(1-5分制)', '同v1', '同v1', '四维 + 题型差异化评分'],
            ['作业评估', '仅案例分析五维', '同v1', '同v1', '8题型自动路由+差异化评分'],
            ['提问优化', '5模板+7规则', '同v1', '同v1', '同v1'],
            ['题型识别', '—', '—', '—', '8型加权特征匹配'],
            ['答案键评分', '—', '—', '—', '精确匹配+部分得分+采分点覆盖'],
            ['批量评分', '—', '—', '—', '批量客观题+答案键验证'],
            ['评分校准', '—', '—', '—', '黄金标准基准测试+MAE计算'],
            ['真题解析', '—', '—', '—', 'PDF→结构化答案键'],
        ]
    )

    doc.add_page_break()

    # ===================== SECTION 8: FAILURE PATTERN COVERAGE =====================
    add_heading('八、各版本失效模式覆盖对比', 1)

    add_table(
        ['编号', 'v1.0.0', 'v2.0.0', 'v3.0.0', 'v4.0.0', 'v4目标题型'],
        [
            ['F1 法条幻视', '✅ 关键词', '✅ +案由映射', '✅ +5,515案例验证', '✅', '全部'],
            ['F2 罪名定性降维', '✅', '✅ +案由映射', '✅', '✅', 'T6,T8'],
            ['F3 量刑乐观偏差', '✅', '✅ +案由映射', '✅', '✅', 'T8'],
            ['F4 浅度正确', '✅', '✅ +案由映射', '✅', '✅', 'T4-T8'],
            ['F5 前提验证盲区', '✅', '✅ +案由映射', '✅', '✅', '全部'],
            ['F6 引导性赤字', '✅', '✅ +案由映射', '✅', '✅', 'T6,T8'],
            ['F7 计算推理不一致', '✅', '✅ +案由映射', '✅', '✅', 'T8'],
            ['F8 因果关系过度简化', '✅', '✅ +案由映射', '✅', '✅', 'T6,T8'],
            ['F9 国际法视野缺失', '✅', '✅ +案由映射', '✅', '✅', 'T6'],
            ['F10 用户差异化风险盲区', '✅', '✅ +案由映射', '✅', '✅', 'T6'],
            ['F11 选项混淆偏误', '—', '—', '—', '✅ 新增', 'T1,T2'],
            ['F12 采分点遗漏', '—', '—', '—', '✅ 新增', 'T5'],
            ['F13 定义要素缺失', '—', '—', '—', '✅ 新增', 'T4'],
            ['F14 判对错不给理由', '—', '—', '—', '✅ 新增', 'T3'],
            ['F15 法条解构不完整', '—', '—', '—', '✅ 新增', 'T7'],
            ['F16 论述偏离题眼', '—', '—', '—', '✅ 新增', 'T6'],
            ['F17 三段论结构缺失', '—', '—', '—', '✅ 新增', 'T8'],
            ['F18 要件事实识别错误', '—', '—', '—', '✅ 新增', 'T8'],
        ]
    )

    doc.add_page_break()

    # ===================== SECTION 9: ROADMAP =====================
    add_heading('九、升级路线图与关键技术决策', 1)

    add_heading('9.1 升级路径', 2)
    add_para('v1.0.0 → v2.0.0：数据驱动升级。核心决策是"先扩数据，不改逻辑"——用900案例知识库增强F1-F10的检测精准度（通过案由映射），但不改动脚本层。')
    add_para('v2.0.0 → v3.0.0：规模升级。核心决策是"用真实司法数据替代合成数据"——从900个生成案例升级到5,515个人民法院案例库真实案例，采用100%合规的官方API采集方案，每个案例的裁判要旨作为评估标准答案的权威参照。')
    add_para('v3.0.0 → v4.0.0：功能质变升级。核心决策是"用真题校准能力边界"——不再满足于案例库的规模增长，而是基于2022-2025法考真题进行8大题型的识别、路由和差异化评分能力建设，并扩展8种题型特化失效模式。')

    add_heading('9.2 关键架构决策', 2)
    add_para('1. 题型识别优先于评分：采用"先分类，后评分"的两阶段架构。question_type_classifier.py独立于评分器，任一句子流入→先判断T1-T8→再路由到对应评分函数。')
    add_para('2. 答案键标准化：为8种题型各定义了JSON Schema，答案键可以独立于题目文本存储和版本管理。')
    add_para('3. 校准内置化：calibrate_scoring.py可以在每次修改检测规则后快速重跑基准测试，确保改动不引入退化。')
    add_para('4. 向下兼容：law_assignment_evaluator_v2.py在无答案键时回退到v1.0.0的五维评分逻辑，确保原有案例分析评估不受影响。')

    doc.add_page_break()

    # ===================== SECTION 10: CALIBRATION REPORT =====================
    add_heading('十、v4.0.0校准报告', 1)

    add_heading('10.1 校准数据源', 2)
    add_para('• 2022-2025年法考客观题真题：8套PDF（公法卷+私法卷×4年）')
    add_para('• 2022-2025年法考主观题真题：4套PDF')
    add_para('• 基准测试集：benchmark/gold_standard/all_types_benchmark.json（7项题型基准 + 4项回归测试）')

    add_heading('10.2 校准结果（2026-07-31）', 2)
    add_table(
        ['指标', '结果', '评级'],
        [
            ['题型识别准确率', '100% (7/7)', '✅ A'],
            ['客观题评分MAE', '0.0 (4/4零误差)', '✅ A'],
            ['失效模式检测召回率', '100% (9/9)', '✅ A'],
            ['综合评级', 'A (优秀校准)', '✅ A'],
        ]
    )

    add_heading('10.3 分题型识别详情', 2)
    add_table(
        ['题型', '识别结果', '置信度', '状态'],
        [
            ['T1 单选 (BM-T1-001)', 'T1_single_choice', '0.66', '✅'],
            ['T1 单选 (BM-T1-002)', 'T1_single_choice', '0.75', '✅'],
            ['T2 多选 (BM-T2-001)', 'T2_multi_choice', '0.60', '✅'],
            ['T3 判断 (BM-T3-001)', 'T3_true_false', '0.60', '✅'],
            ['T4 名词解释 (BM-T4-001)', 'T4_term_definition', '0.60', '✅'],
            ['T5 简答 (BM-T5-001)', 'T5_short_answer', '0.60', '✅'],
            ['T8 案例分析 (BM-T8-001)', 'T8_case_analysis', '0.60', '✅'],
        ]
    )

    add_heading('10.4 失效模式检测详情', 2)
    add_table(
        ['测试项', '期望检测', '实际触发', '命中', '状态'],
        [
            ['BM-T3-001', 'F11', 'F11 + F12 + F13 + F15', 'F11', '✅'],
            ['BM-T5-001', 'F12', 'F12 + F13', 'F12', '✅'],
            ['BM-T8-001', 'F17', 'F17 + F13', 'F17', '✅'],
            ['REG-001 (F1陷阱)', 'F1', 'F1 + F12 + F13 + F15', 'F1', '✅'],
            ['REG-002 (F17)', 'F17', 'F17 + F11 + F13', 'F17', '✅'],
            ['REG-003 (F14+F11)', 'F14 + F11', 'F14 + F11 + F12 + F13', 'F14, F11', '✅'],
            ['REG-004 (F1+F11)', 'F1 + F11', 'F1 + F11 + F12 + F13 + F15', 'F1, F11', '✅'],
        ]
    )

    doc.add_page_break()

    # ===================== SECTION 11: FUTURE =====================
    add_heading('十一、未来规划与改进方向', 1)

    add_heading('11.1 短期（v4.1.0）', 2)
    add_para('• 从法考真题PDF中批量解析100+客观题答案键，建立T1/T2/T3全覆盖的基准测试集')
    add_para('• 提升题型识别置信度：当前T1-T5的置信度在0.6-0.75之间，通过增加pattern覆盖可提升到0.8+')
    add_para('• 扩充BM-T4/T5/T6/T7的黄金标准样本（当前各仅1项）')
    add_para('• 增加T2部分得分/多选错选的边界测试用例')

    add_heading('11.2 中期（v4.2.0）', 2)
    add_para('• 利用5,515案例的裁判要旨自动生成各题型的答案键和采分点')
    add_para('• 从裁判要旨反向生成选择题干扰项（利用案由相似但判决不同的案例）')
    add_para('• 引入LLM进行学生答案的深层语义分析（而不仅是关键词覆盖）')
    add_para('• 建立题型识别难度分级（本科水平 vs 法考水平）')

    add_heading('11.3 长期（v5.0.0）', 2)
    add_para('• 接入法学教材知识图谱，实现知识点的自动标注和难度评估')
    add_para('• 学生常见错误的机器学习聚类分析（利用大量学生答案训练错误模式识别）')
    add_para('• 实时联网验证法条现行有效性（替代静态legal_knowledge_base.json）')
    add_para('• 支持跨题型的综合试卷评估（如一份包含T1-T8的完整期末考试卷）')
    add_para('• 与教学管理系统(LMS)集成，实现作业自动批改→成绩录入的闭环')

    # ===================== APPENDIX =====================
    doc.add_page_break()
    add_heading('附录A: 产品技术文档清单', 1)
    add_para('以下5份PDF文档位于 产品技术文档/ 目录：')
    add_para('1. 01_需求分析报告.pdf — 项目背景、问题定义、目标用户、功能需求、非功能需求')
    add_para('2. 02_框架设计说明书.pdf — 四层架构、知识库设计、脚本引擎设计、数据流设计')
    add_para('3. 03_测试用例报告.pdf — 测试策略、用例设计、执行结果')
    add_para('4. 04_功能及性能指标.pdf — 功能完整性、性能基准、可靠性指标')
    add_para('5. 05_使用说明手册.pdf — 安装部署、模块使用指南、API参考')

    add_heading('附录B: GitHub仓库信息', 1)
    add_para('仓库地址: https://github.com/Phillnarsoeer/legal-guardian')
    add_para('最新公开版本: v2.0.0 (2026-07-30)')
    add_para('提交数: 7 commits')
    add_para('仓库结构: reference/ scripts/ templates/ tests/ README.md SKILL.md manifest.yaml')
    add_para('v2.0.0提交信息: "v2.0.0: LegalGuardian - 900 cases, 1800 QA, 900 RAG, 71 cause types"')

    add_heading('附录C: 数据源汇总', 1)
    add_table(
        ['数据源', 'URL/来源', '用途', '版本'],
        [
            ['人民法院案例库', 'rmfyalk.court.gov.cn', '5,515真实案例+裁判要旨', 'v3.0.0'],
            ['国家法律法规数据库', 'flk.npc.gov.cn', '法条存在性+现行有效性验证', 'v1.0.0'],
            ['2022-2025法考客观题真题', '环球网校/司法部公开', '题型格式校准+答案键', 'v4.0.0'],
            ['2022-2025法考主观题真题', '环球网校/司法部公开', '论述题+案例分析格式校准', 'v4.0.0'],
            ['DeepSeek+千问实证数据', '徐子涵团队2026.05测评', 'F1-F10基线+四维评分锚定', 'v1.0.0'],
        ]
    )

    # ===================== SAVE =====================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'LegalGuardian_v1.0_to_v4.0_升级技术白皮书.docx')
    doc.save(output_path)
    print(f'Document saved to: {output_path}')


if __name__ == '__main__':
    main()
