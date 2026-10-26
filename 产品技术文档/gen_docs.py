# -*- coding: utf-8 -*-
"""
v4.3.0 技术文档 PDF 生成器（紧凑版）
使用 PyMuPDF + 微软雅黑（msyh.ttc/msyhbd.ttc）生成5份技术文档，版本对齐 v4.3.0。
按实际字符宽度换行，避免溢出；正文9.5pt、行距13.2pt、段距3.2pt，版面紧凑。
"""
import fitz
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD_FILE = 'C:/Windows/Fonts/msyhbd.ttc'
FONT = 'F0'
FONT_BOLD = 'FB'

MARGIN = 46
PAGE_W = 595  # A4
PAGE_H = 842
BODY = 9.5
HEAD1 = 13
HEAD2 = 11
HEAD3 = 10
LINE_H = 13.2
GAP = 3.2
T_SIZE = 8.5      # 表格字号
T_LINE = 11       # 表格行内行距
NAVY = (0.09, 0.21, 0.36)
NAVY2 = (0.16, 0.31, 0.51)
GOLD = (0.79, 0.64, 0.15)
GRAY = (0.35, 0.35, 0.35)

_fm_reg = fitz.Font(fontfile=FONT_FILE)
_fm_bold = fitz.Font(fontfile=FONT_BOLD_FILE)


def _save_small(doc, path):
    """嵌入字体子集化 + 压缩保存（35MB → ~0.4MB，版面与文字完全不变）"""
    try:
        doc.subset_fonts(verbose=False)
    except Exception as e:                      # 老版本 PyMuPDF 无此接口
        print(f'  ! 字体子集化跳过：{type(e).__name__}')
    doc.save(path, garbage=4, deflate=True, clean=True)
    size = os.path.getsize(path) / 1048576
    print(f'  体积 {size:.2f}MB')


def _wlen(text, size, bold=False):
    f = _fm_bold if bold else _fm_reg
    return f.text_length(text, fontsize=size)


_ASCII_RUN = re.compile(r'[\x21-\x7e]+')


def _units(text):
    """把文本切成不可再拆的排版单元：连续 ASCII 视作一个词，其余逐字"""
    out, i, n = [], 0, len(text)
    while i < n:
        m = _ASCII_RUN.match(text, i)
        if m:
            out.append(m.group())
            i = m.end()
        else:
            out.append(text[i])
            i += 1
    return out


def _wrap(text, max_w, size, bold=False):
    """按实测宽度贪心换行；不在英文单词/路径/版本号中间断行"""
    lines, cur = [], ''
    for u in _units(text):
        cand = cur + u
        if _wlen(cand, size, bold) > max_w and cur:
            if len(u) > 1 and _wlen(u, size, bold) > max_w:
                # 单词本身超宽（如长路径）：只能逐字拆
                for ch in u:
                    if _wlen(cur + ch, size, bold) > max_w and cur:
                        lines.append(cur)
                        cur = ch
                    else:
                        cur += ch
                continue
            lines.append(cur)
            cur = u
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


class PDFBuilder:
    def __init__(self, title, version, date, team, cover=True, chapter=''):
        self.show_cover = cover
        self.chapter = chapter
        self.chapter_page = 0
        self.doc = fitz.open()
        self.title = title
        self.version = version
        self.date = date
        self.team = team
        self.y = MARGIN
        self.page = None
        self._new_page()

    def _new_page(self):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page.insert_font(fontname=FONT, fontfile=FONT_FILE)
        self.page.insert_font(fontname=FONT_BOLD, fontfile=FONT_BOLD_FILE)
        self.y = MARGIN

    def _ensure_space(self, needed=40):
        if self.y + needed > PAGE_H - MARGIN:
            self._new_page()

    def _line(self, text, size=BODY, bold=False, color=(0, 0, 0), indent=0):
        self._ensure_space(size + GAP)
        x = MARGIN + indent
        self.page.insert_text((x, self.y), text, fontname=FONT_BOLD if bold else FONT,
                              fontsize=size, color=color, render_mode=0)
        self.y += size + GAP

    def para(self, text, size=BODY, indent=0, color=(0, 0, 0)):
        max_w = PAGE_W - MARGIN * 2 - indent
        for ln in _wrap(text, max_w, size, False):
            self._line(ln, size=size, indent=indent, color=color)

    def bullet(self, text):
        self.para('• ' + text, indent=10)

    def heading(self, text, level=1):
        # 预留「标题 + 紧随其后的表格/正文」的空间，避免标题孤零零落在页末（孤行）
        self._ensure_space(26 + 60 if level <= 2 else 40 + 40)
        if level == 1:
            self._line('', size=5)
            self._line(text, size=HEAD1, bold=True, color=NAVY)
            self.y += 2
        elif level == 2:
            self._line(text, size=HEAD2, bold=True, color=NAVY2)
        else:
            self._line(text, size=HEAD3, bold=True)

    def cover(self, subtitle=''):
        if not self.show_cover:
            # 合并版：分级章标题条（流式排版，章节首尾相接不留空白）
            if self.y > MARGIN + 12:
                self.y += 14          # 与上一章内容留出间距，避免压住表格末行
            if self.y + 150 > PAGE_H - MARGIN:
                self._new_page()
            self.chapter_page = self.doc.page_count - 1  # 章真实起始页（流式排版页码锚点）
            y = self.y
            self.page.draw_rect(fitz.Rect(MARGIN, y - 2, MARGIN + 4, y + 13),
                                color=None, fill=GOLD)
            self.page.insert_text((MARGIN + 12, y), f'第 {int(self.chapter)} 章　{self.title}',
                                  fontname=FONT_BOLD, fontsize=13.5, color=NAVY)
            if subtitle:
                w = _wlen(subtitle, 9)
                self.page.insert_text((PAGE_W - MARGIN - w, y + 1), subtitle,
                                      fontname=FONT, fontsize=9, color=GRAY)
            self.page.draw_line(fitz.Point(MARGIN, y + 18), fitz.Point(PAGE_W - MARGIN, y + 18),
                                color=NAVY2, width=0.8)
            self.y = y + 26
            return
        self.y = 240
        self._line('LegalGuardian', size=32, bold=True, color=NAVY)
        self._line('法律守卫', size=24, bold=True)
        self.y += 10
        self._line(self.title, size=18, bold=True)
        if subtitle:
            self._line(subtitle, size=11, color=GRAY)
        self.y += 16
        self._line(self.version, size=13, bold=True, color=NAVY2)
        self._line(self.date, size=11, color=GRAY)
        self.y += 8
        self._line(self.team, size=11, color=GRAY)

    def table(self, headers, rows, widths=None):
        """自适应行高的简单表格；widths为比例列表"""
        n = len(headers)
        widths = widths or [1.0 / n] * n
        avail = PAGE_W - MARGIN * 2
        vals = [w / sum(widths) * avail for w in widths]
        self._ensure_space(60)

        def draw_row(y, cells, header=False):
            wrapped = []
            for ci, cell in enumerate(cells):
                max_w = vals[ci] - 8
                wrapped.append(_wrap(str(cell), max_w, T_SIZE, header))
            row_h = max(len(w) for w in wrapped) * T_LINE + 6
            for ci in range(n):
                x = MARGIN + sum(vals[:ci])
                rect = fitz.Rect(x, y, x + vals[ci], y + row_h)
                if header:
                    self.page.draw_rect(rect, color=NAVY, fill=NAVY)
                else:
                    self.page.draw_rect(rect, color=(0.75, 0.75, 0.75))
            for ci, cell in enumerate(cells):
                x = MARGIN + sum(vals[:ci]) + 4
                for li, ln in enumerate(wrapped[ci]):
                    col = (1, 1, 1) if header else (0, 0, 0)
                    self.page.insert_text((x, y + 8 + li * T_LINE + T_SIZE - 2), ln,
                                          fontname=FONT_BOLD if header else FONT,
                                          fontsize=T_SIZE, color=col)
            return y + row_h

        self.y = draw_row(self.y, headers, True)
        for row in rows:
            if self.y + 44 > PAGE_H - MARGIN:
                self._new_page()
                self.y = draw_row(self.y, headers, True)
            self.y = draw_row(self.y, row, False)
        self.y += 6

    def footer(self, note):
        self._ensure_space(30)
        self._line(note, size=8.5, color=GRAY)

    def save(self, filename):
        self.doc.set_metadata({
            'title': self.title,
            'author': '西南民族大学法学院参赛团队',
            'creator': 'PyMuPDF',
            'subject': self.version
        })
        _save_small(self.doc, os.path.join(OUT_DIR, filename))
        self.doc.close()
        print(f'✓ 生成 {filename}')


def build_req_analysis(out=None, cover=True):
    global _STREAM
    if _STREAM is not None:
        b = _STREAM
        b.chapter, b.title = '01', '需求分析报告'
    else:
        b = PDFBuilder('需求分析报告', 'LegalGuardian v4.3.0', '2026-08-19',
                       '西南民族大学法学院参赛团队', cover=cover, chapter='01')
    b.cover(subtitle='Requirements Analysis Report')

    b.heading('1. 项目背景')
    b.para('大型语言模型在法律场景快速渗透，但实证测评显示其输出存在系统性失效。团队对 DeepSeek、千问 Qwen 完成'
           '14 案例 × 2 轮 × 4 维测评：千问虚构法条识别率 0%、DS 许某某案量刑预测误差 71%（预测 3.5 年 vs 实际 6 年）、'
           '引导性得分 DS 2.96/5、千问 1.70/5。LegalGuardian 以该实证基线为不可修改的校准锚点，'
           '构建"检测—纠正—评分"闭环，落实竞赛铁律：评分可复现（偏差≤0.2）、可校准（对照实证基线）。'
            '项目自 v1.0.0 至 v4.3.0 完成 8 个版本迭代（2026-07-29 至 08-19，GitHub 仓库全程可查），各版本演进如下表所示。')
    b.table(
        ['版本', '日期', '核心升级'],
        [
            ['v1.0.0', '07-29', '框架创立：AI 法律对话实证校正框架'],
            ['v2.0.0', '07-30', '数据奠基：900 案例、1,800 QA、900 RAG、71 案由'],
            ['v3.0.0', '07-31', '规模跃升：5,515 法院案例、535 案由、27,575 QA，RAG 检索上线'],
            ['v4.0.0', '07-31', '能力成型：18 失效模式、8 大题型评分、法考真题校准'],
            ['v4.1.0', '08-03', '体系扩展：F1-F24 全模式、教学大纲合规审核、安全检查器、竞赛场景匹配、基准 16 项'],
            ['v4.2.0', '08-05', '质量攻坚：JSON 模块级缓存、主观题归一化、废止法红线修复、去 20 处死代码'],
            ['v4.2.1', '08-17', '发布准备：文档结构优化与版本化'],
            ['v4.3.0', '08-17', '简洁精进：红线统一、全量校准 C→A、案例检索、三维规制、报告面板；冒烟 41 项全绿'],
        ],
        widths=[1.0, 0.9, 5.1]
    )

    b.heading('2. 问题定义')
    b.bullet('准确性危机：AI 可能引用虚构或已废止法律（千问将"人格权侵害惩治条例"视为真实法律）')
    b.bullet('深度缺失：结论正确但缺乏深度法理分析，即"浅度正确"')
    b.bullet('引导性不足：指出"问题在哪"但不告诉"怎么解决"（DS 引导性 2.96/5）')
    b.bullet('前提验证盲区：AI 天然相信用户输入，不验证前提假设是否成立')
    b.bullet('用户差异化风险：同一回答对法学生与非专业人士风险等级完全不同')
    b.bullet('教学场景失效（v4.1）：试题歧义、评分偏移、格式违规、跨题矛盾、教学合规偏离')

    b.heading('3. 目标用户分析')
    b.table(
        ['用户类型', '核心需求', '风险等级'],
        [
            ['法学本科生/研究生', '深度法理分析、失效模式识别训练、AI 辅助作业', '中'],
            ['法学教师', '教学材料审核、AI 输出验证、作业批改辅助', '中低'],
            ['非专业社会人士', '通俗解释、醒目风险警示、律师咨询引导', '高'],
            ['AI 工具开发者', '三维规制符合性评估、失效模式诊断', '中'],
            ['教务管理者(v4.1)', '教学大纲合规审核、教学质量多维评价', '中'],
        ],
        widths=[1.6, 3.4, 1.0]
    )

    b.heading('4. 功能需求')
    b.table(
        ['模块', '功能', '要点'],
        [
            ['A 审核纠正', '24 模式检测 F1-F24', '关键词规则+模式匹配，输出概率/严重度/依据；命中即纠正'],
            ['A 安全检查', '8 项检查 C1-C8', '法条来源核对、量刑边界、多平台交叉、人工核实标注等'],
            ['A 四维评分', '实测基线对比', '准确/时效/逻辑/引导 vs 14 案例实证基线'],
            ['B 提问优化', '5 大模板+场景匹配', '陷阱识别（废止法律/量刑预测/未验证前提）+ 问题重写'],
            ['C 作业评估', '8 题型 T1-T8', '差异化评分；红线规则 D1=0→总分归零'],
            ['C 失效检测', '24 模式同步检测', '作业内嵌失效模式识别 + 改进计划'],
            ['D 三维评估', 'T1-T5/E1-E4/L1-L4', '技术规范、教育引导、法律保障逐项合规性'],
            ['E 大纲合规', '覆盖率核验（≥80%）', '教育部标准+18 必授知识点；缺失清单+修订建议'],
        ],
        widths=[1.4, 2.0, 3.6]
    )

    b.heading('5. 非功能需求')
    b.table(
        ['类别', '指标', '要求'],
        [
            ['性能', '失效模式检测 / 作业评估', '≤5 秒/次 / ≤60 秒/次'],
            ['可靠性', '失效模式覆盖', '24/24 全覆盖（F1-F24）'],
            ['可靠性', '虚构法律识别准确率', '≥95%'],
            ['可维护性', '知识库更新', 'JSON 独立于脚本，可直接替换'],
            ['可扩展性', '新增失效模式', 'candidate_patterns 字段'],
            ['兼容性', '输入格式', '.txt / .md / .docx'],
            ['兼容性', '模型基座', 'Qwen3-Next-80B 等 5 个系列'],
            ['兼容性', '部署平台', 'AI 龙虾智能体平台'],
        ],
        widths=[1.2, 2.4, 3.4]
    )

    b.heading('6. 约束条件')
    b.table(
        ['约束', '要求'],
        [
            ['模型基座', '推理 Qwen3-Next-80B / 嵌入 Qwen3-Embedding-8B / 重排 Qwen3-Reranker-8B / 多模态 Qwen3-VL-32B / 语音 Qwen3-ASR、Qwen3-TTS'],
            ['平台与算力', '须在 AI 龙虾智能体平台部署演示，基于国产芯片算力环境'],
            ['法律定位', '不替代律师/教师，不做终局性法律判断'],
            ['实证基线', '所有纠正建议必须引用 14 案例×2 轮×4 维实证数据'],
            ['竞赛铁律', '评分可复现（偏差≤0.2 分）、评分可校准（对照实证基线）'],
        ],
        widths=[1.2, 5.8]
    )

    if _STREAM is None:
        b.save(out or '01_需求分析报告.pdf')


def build_framework(out=None, cover=True):
    global _STREAM
    if _STREAM is not None:
        b = _STREAM
        b.chapter, b.title = '02', '框架设计说明书'
    else:
        b = PDFBuilder('框架设计说明书', 'LegalGuardian v4.3.0', '2026-08-19',
                       '西南民族大学法学院参赛团队', cover=cover, chapter='02')
    b.cover(subtitle='Framework Design Specification')

    b.heading('1. 总体架构')
    b.para('LegalGuardian 采用四层模块化架构：知识库层（reference/）、脚本引擎层（scripts/）、逻辑编排层（SKILL.md）、'
           '输出模板层（templates/）。层间以 JSON 标准接口通信，实现数据与逻辑完全解耦，知识库可独立更新。')

    b.heading('2. 知识库层设计（9 个 JSON 文件）')
    b.table(
        ['文件', '内容', '规模/要点'],
        [
            ['failure_patterns.json', '24 大失效模式知识库', 'F1-F10 通用/ F11-F18 题型特化/ F19-F24 场景；含严重度、实证证据、纠正策略'],
            ['curriculum_requirements.json', '教育部课程要求', '八大领域、18 个必授知识点，供 F24 合规检测'],
            ['test_baseline.json', '实证基线', '14 案例 2 轮 4 维（DS 3.84 vs 千问 3.06）'],
            ['correction_templates.json', '提问模板', '5 大模板 + 竞赛场景匹配规则'],
            ['safety_checklist.json', '安全检查清单', '8 项检查 C1-C8'],
            ['three_d_regulation.json', '三维规制路径', '技术 T1-T5 / 教育 E1-E4 / 法律 L1-L4'],
            ['question_type_rubrics.json', '题型评分标准', '8 题型 T1-T8 差异化规则'],
            ['assignment_rubric.json', '作业评分标准', '五维评分'],
            ['legal_knowledge_base.json', '法条与预警', '核心法条 + 废止预警'],
        ],
        widths=[2.2, 1.6, 3.2]
    )

    b.heading('3. 脚本引擎层设计（15 个 Python 脚本）')
    b.table(
        ['脚本', '职责'],
        [
            ['failure_detector.py', 'F1-F24 逐模式检测引擎，输出概率/严重度/依据'],
            ['correction_engine.py', 'F1-F24 全覆盖纠正生成器（实证依据+修正方向+替代表述）'],
            ['safety_checker.py', '执行 8 项安全检查，输出通过率+总体风险等级'],
            ['question_type_classifier.py', 'T1-T8 题型识别与路由'],
            ['law_assignment_evaluator_v2.py', '8 题型统一评估器（红线规则 D1=0 归零）'],
            ['scoring_engine.py', '四维评分'],
            ['template_matcher.py', '5 模板匹配 + 竞赛场景检测（大纲→T1+T4+T5；考试→T3+T5）'],
            ['answer_key_evaluator.py', '答案键验证与批量评分'],
            ['calibrate_scoring.py', '评分校准（对照实证基线）'],
            ['exam_parser.py', '法考真题解析'],
            ['rag_retriever.py', '5,515 案例库确定性检索（v4.3.0）'],
            ['regulation_assessor.py', '三维规制评估（v4.3.0 落地）'],
            ['report_builder.py', '全链路可视化报告（v4.3.0）'],
            ['legal_db_fetcher.py', '法律知识检索'],
            ['law_assignment_evaluator.py', '历史评估器（v4.0）'],
        ],
        widths=[2.6, 4.4]
    )

    b.heading('4. 数据流设计')
    b.para('用户输入（AI 回复/问题/作业/大纲）→ 模块入口 → 知识库加载 → 脚本执行 → JSON → 模板渲染 → 最终报告。'
           '模块A 审核链：failure_detector → correction_engine → safety_checker 三阶段串联；'
           '模块E 合规链：大纲解析 → curriculum_requirements 对照 → F24 检测 → 合规报告。')

    b.heading('5. 目录结构')
    b.table(
        ['目录', '内容'],
        [
            ['scripts/', '15 个 Python 脚本（检测/纠正/评分/检索/报告）'],
            ['reference/', '9 个 JSON 知识库（数据与逻辑分离，可独立替换）'],
            ['templates/', '2 个输出模板'],
            ['benchmark/', '黄金标准基准'],
            ['tests/', '集成测试；test_data/ 案例数据'],
            ['panel/', '可视化报告面板（零依赖、离线可用）'],
        ],
        widths=[1.6, 5.4]
    )

    b.heading('6. 版本演进与架构影响')
    b.table(
        ['版本', '架构变化'],
        [
            ['v1.0-v2.0', '单一脚本流程：检测+纠正，知识库雏形'],
            ['v3.0-v4.0', '数据层独立：RAG 检索、题型评分与考试校准模块成型'],
            ['v4.1.0', '场景扩展：模块E 大纲合规审核、安全检查器、场景门控'],
            ['v4.3.0', '能力升级：rag_retriever / regulation_assessor / report_builder + 可视化面板；精简包'],
        ],
        widths=[1.4, 5.6]
    )

    if _STREAM is None:
        b.save(out or '02_框架设计说明书.pdf')


def build_test_cases(out=None, cover=True):
    global _STREAM
    if _STREAM is not None:
        b = _STREAM
        b.chapter, b.title = '03', '测试用例报告'
    else:
        b = PDFBuilder('测试用例报告', 'LegalGuardian v4.3.0', '2026-08-19',
                       '西南民族大学法学院参赛团队', cover=cover, chapter='03')
    b.cover(subtitle='Test Cases Report')

    b.heading('1. 测试策略')
    b.para('三层架构：单元测试（函数级验证）、集成测试（脚本间管道串联）、端到端测试（真实场景模拟）。'
           '覆盖 15 个脚本、9 个 JSON 知识库、24 种失效模式（F1-F24），并以全量冒烟测试（41 项，0 FAIL（2026-08-19 全绿））为基线。')

    b.heading('2. 核心集成测试用例（TC001-TC010）')
    b.table(
        ['编号', '模块', '名称', '结果'],
        [
            ['TC001', 'A-基础', '法条幻视检测（F1）', '通过'],
            ['TC002', 'A-进阶', '多模式同时检测（F1+F3）', '通过'],
            ['TC003', 'A-边界', '优质回答零误报', '通过'],
            ['TC004', 'B-基础', '废止法律问题优化', '通过'],
            ['TC005', 'B-进阶', '量刑预测优化', '通过'],
            ['TC006', 'B-实务', '实操需求匹配', '通过'],
            ['TC007', 'C-基础', '中等作业评估', '通过'],
            ['TC008', 'C-红线', '红线规则触发', '通过'],
            ['TC009', 'D-评估', '三维规制评估', '通过'],
            ['TC010', 'ALL', '端到端审核链', '通过'],
        ],
        widths=[1.0, 1.2, 3.6, 1.2]
    )

    b.heading('3. 教学/场景新增用例（TC011-TC020）')
    b.table(
        ['编号', '模块', '名称', '结果'],
        [
            ['TC011', 'A-安全', 'safety_checker 8 项检查执行', '通过'],
            ['TC012', 'C-F11', '选项混淆纠正建议生成', '通过'],
            ['TC013', 'C-F12', '采分点遗漏纠正建议生成', '通过'],
            ['TC014', 'C-F17', '三段论缺失纠正建议生成', '通过'],
            ['TC015', 'E-F24', '教学大纲合规偏离检测', '通过'],
            ['TC016', 'E-F24', '核心知识点覆盖率 <80% 触发', '通过'],
            ['TC017', 'B-竞赛', '教学大纲审核→[T1+T4+T5] 匹配', '通过'],
            ['TC018', 'B-竞赛', '考试设计→[T3+T5] 匹配', '通过'],
            ['TC019', '检测-F19', '试题歧义检测', '通过'],
            ['TC020', '检测-F22', '跨题一致性检测', '通过'],
        ],
        widths=[1.0, 1.2, 3.6, 1.2]
    )

    b.heading('4. 基准测试结果（2026-08-05）')
    b.table(
        ['指标', '结果'],
        [
            ['题型识别准确率', '100%（16/16 全量）'],
            ['失效模式体系', 'F1-F24 全覆盖'],
            ['检测→纠正链路', '100% 命中即纠正'],
            ['教学合规审核', 'F24 覆盖率阈值 80% 验证通过'],
            ['综合评级', 'A（优秀校准，全量 26 项）'],
        ],
        widths=[2.2, 4.8]
    )

    b.heading('5. 回归测试')
    b.para('REG-001~004：基础功能回归；REG-005~010：v4.1.0 新增场景回归，覆盖教学大纲合规、跨题一致性、'
           '试题歧义、格式违规、评分偏移、采分点粒度六类 F19-F24 检测验证。')

    b.heading('6. 版本迭代测试演进')
    b.table(
        ['版本', '测试能力演进'],
        [
            ['v1.0-v2.0', '手工验证为主，无自动化测试'],
            ['v3.0-v4.0', '黄金标准基准集建立，回归基线化'],
            ['v4.1.0', '基准扩展至 16 项 + 10 回归；场景门控零误报验证'],
            ['v4.2.0', '性能与正确性回归：缓存、归一化、红线规则'],
            ['v4.3.0', '冒烟测试 41 项 0 FAIL；全量校准 26 项评级 A'],
        ],
        widths=[1.4, 5.6]
    )

    if _STREAM is None:
        b.save(out or '03_测试用例报告.pdf')


def build_performance(out=None, cover=True):
    global _STREAM
    if _STREAM is not None:
        b = _STREAM
        b.chapter, b.title = '04', '功能及性能指标'
    else:
        b = PDFBuilder('功能及性能指标', 'LegalGuardian v4.3.0', '2026-08-19',
                       '西南民族大学法学院参赛团队', cover=cover, chapter='04')
    b.cover(subtitle='Functional & Performance Metrics')

    b.heading('1. 功能指标汇总')
    b.table(
        ['模块', '功能数', '核心指标', '引入'],
        [
            ['A：AI 回答审核', '8 项', '24/24 失效模式覆盖，四维评分+基线对比', 'v1.0'],
            ['A：安全检查', '8 项', '8 项清单执行，风险联动', 'v4.1'],
            ['B：提问优化', '4 项', '5 模板+竞赛场景匹配', 'v4.1'],
            ['C：作业评估', '5 项', '8 题型差异化评分，红线规则 100% 执行', 'v4.0'],
            ['D：三维评估', '3 项', '13 项（T+E+L）全覆盖', 'v4.3'],
            ['E：教学合规', '3 项', '核心知识点覆盖率核验（≥80%）', 'v4.1'],
            ['报告面板', '4 项', '零依赖可视化"数字案卷"，打印/导出 PDF', 'v4.3'],
            ['全流程', '1 项', '检测→纠正→安全→评分→报告管道', 'v4.3'],
        ],
        widths=[1.8, 0.9, 3.1, 0.9]
    )

    b.heading('2. 响应时间')
    b.table(
        ['操作', '目标', '实测'],
        [
            ['失效模式检测', '≤5 秒', '≤3 秒'],
            ['纠正建议生成', '≤10 秒', '≤8 秒'],
            ['安全检查执行(v4.1)', '≤5 秒', '≤2 秒'],
            ['模板匹配+优化', '≤5 秒', '≤3 秒'],
            ['作业评估', '≤60 秒', '≤45 秒'],
            ['全流程审核链', '≤45 秒', '≤30 秒'],
            ['教学合规审核(v4.1)', '≤30 秒', '≤20 秒'],
        ],
        widths=[2.4, 1.8, 1.8]
    )

    b.heading('3. 实证基线对比（1-5 分制）')
    b.table(
        ['维度', 'DS 基线', '千问基线', 'LG 目标', '目标差距'],
        [
            ['准确性', '4.03', '3.49', '≥4.5', '+0.47'],
            ['时效性', '4.69', '4.13', '≥4.5', '−0.19（已超额）'],
            ['逻辑性', '3.66', '2.93', '≥4.0', '+0.34'],
            ['引导性', '2.96', '1.70', '≥3.0', '+0.04'],
            ['综合', '3.84', '3.06', '≥4.0', '+0.16'],
        ],
        widths=[1.4, 1.2, 1.2, 1.2, 1.7]
    )
    b.para('注：目标差距 = LG 目标 − DS 基线，正值表示仍需补齐，负值表示已超出目标；两基线均为同一 14 案例 × 2 轮 × 4 维实证测评结果。',
           size=8.5, color=GRAY)

    b.heading('4. 可靠性指标')
    b.table(
        ['指标', '目标/实测'],
        [
            ['虚构法律识别率', '目标 100%（千问基线 0%）'],
            ['废止法律标注率', '目标 100%'],
            ['引导性最低阈值', '3.0/5（实证最弱维度）'],
            ['红线规则执行率', '100%（D1=0→归零）'],
            ['评分可复现性', '同一输入偏差 ≤0.2 分（确定性规则）'],
            ['教学合规阈值', '核心知识点覆盖率 ≥80%（F24）'],
        ],
        widths=[2.4, 4.6]
    )

    b.heading('5. 资源消耗与可扩展性')
    b.table(
        ['指标', '当前值', '扩展能力'],
        [
            ['Skill 包大小', '约 0.16MB（v4.3.0 精简，原 14MB）', '≤1MB'],
            ['知识库大小', '约 0.8MB（9 文件）', '≤2MB'],
            ['模型调用', '推理 <2000 token/次', '单次审核'],
            ['失效模式', '24 个（F1-F24）', 'candidate_patterns 扩展'],
            ['基准测试', '16 项 + 10 回归', 'items 数组追加'],
        ],
        widths=[2.0, 3.2, 1.8]
    )

    if _STREAM is None:
        b.save(out or '04_功能及性能指标.pdf')


def build_manual(out=None, cover=True):
    global _STREAM
    if _STREAM is not None:
        b = _STREAM
        b.chapter, b.title = '05', '使用说明手册'
    else:
        b = PDFBuilder('使用说明手册', 'LegalGuardian v4.3.0', '2026-08-19',
                       '西南民族大学法学院参赛团队', cover=cover, chapter='05')
    b.cover(subtitle='User Manual')

    b.heading('1. 概述')
    b.para('LegalGuardian（法律守卫）是基于实证数据的 AI 法律对话审查纠正与法学教育评估 Skill。'
           '覆盖 24 种失效模式（F1-F24）、8 大题型（T1-T8）、教学大纲合规审核、三维规制评估与 5,515 案例库检索；'
           '面向法学学生/教师、教务管理者、非专业社会人士与 AI 工具开发者。')

    b.heading('2. 安装部署')
    b.bullet('前提：AI 龙虾智能体平台账号 + Qwen3 系列模型权限 + Python 3.10+')
    b.bullet('步骤 1：获取 Skill 包（legal-guardian.skill）或 git clone 仓库')
    b.bullet('步骤 2：AI 龙虾平台 → 技能管理 → 上传技能 → 选择 .skill 文件 → 确认')
    b.bullet('步骤 3：验证——对话中提及法律问题，确认 Skill 自动激活')

    b.heading('3. 核心模块使用指南')
    b.table(
        ['模块', '使用方式', '关键输出'],
        [
            ['A 审核纠正', '粘贴 AI 回答，附言"请审核这段 AI 法律回答"', '24 模式检测报告+纠正建议+安全等级'],
            ['B 提问优化', '写出原始问题，附言"请优化提问方式"', '陷阱识别+推荐模板+优化后问题'],
            ['C 作业评估', 'python scripts/law_assignment_evaluator_v2.py 作业.docx', '8 题型评分+红线判定+改进计划'],
            ['D 三维评估', 'python scripts/regulation_assessor.py --text "功能描述"', 'T1-T5/E1-E4/L1-L4 逐项状态+雷达图'],
            ['E 大纲合规', '粘贴大纲，附言"请审核教学大纲合规性"', '覆盖率+缺失知识点清单+修订建议'],
            ['报告面板', 'python scripts/report_builder.py 输入.txt --out panel/report.json', '双击 panel/report_panel.html 可视化'],
        ],
        widths=[1.4, 2.8, 2.8]
    )

    b.heading('4. 安全检查（v4.1.0 新增）')
    b.para('对所有审核结果执行 8 项安全检查（C1-C8）：法条来源核对、罪名定性反向思考、量刑预测风险边界、'
           '多平台交叉验证、遗漏争点、需人工核实标注、不替代律师、计算一致性。')

    b.heading('5. 命令行快速参考')
    for line in [
        '# 模块A —— AI 回答审核',
        'python scripts/failure_detector.py input.txt',
        'python scripts/correction_engine.py result.json',
        'python scripts/safety_checker.py input.txt --detections result.json',
        '# 模块B —— 提问优化',
        'python scripts/template_matcher.py "原始问题"',
        '# 模块C —— 作业评估',
        'python scripts/law_assignment_evaluator_v2.py 作业.docx',
        '# 模块E —— 大纲合规（检测 F24）',
        'python scripts/failure_detector.py 大纲.txt',
        '# 案例检索（v4.3.0）',
        'python scripts/rag_retriever.py --query "民间借贷 利息上限" -k 5',
        '# 三维规制评估（v4.3.0）',
        'python scripts/regulation_assessor.py --text "工具功能描述"',
        '# 报告面板（v4.3.0）',
        'python scripts/report_builder.py 输入.txt --out panel/demo_report.json && start panel/report_panel.html',
    ]:
        b.para(line, size=8.5, indent=4)

    b.heading('6. 版本与升级说明')
    b.para('当前版本 v4.3.0（2026-08-17）。自 v1.0.0 起历经 8 个版本迭代（GitHub 仓库 phillnarsoeer/legal-guardian 全程可查）：'
           'v1.0 框架创立 → v2.0/v3.0 数据奠基（900→5,515 案例）→ v4.0 能力成型（18 模式/8 题型）→ '
           'v4.1 体系扩展（F1-F24/大纲合规/安全检查）→ v4.2 质量攻坚（性能/正确性/重构）→ '
           'v4.3 简洁精进（红线统一/案例检索/三维规制/报告面板）。')
    b.bullet('升级步骤：以仓库最新版替换 scripts/ 与 reference/（结构向后兼容，旧版输出可直接导入报告面板）')
    b.bullet('版本核对：检查 manifest.yaml 的 version 字段与 SKILL.md 头部 frontmatter 一致')

    b.heading('7. 常见问题')
    b.bullet('Q：Skill 未自动激活？ A：检查 manifest.yaml 的 description 关键词，确认 Skill 已启用')
    b.bullet('Q：检测到但无纠正建议？ A：确认 reference/ 下所有 JSON 知识库文件完整')
    b.bullet('Q：如何更新法律知识？ A：直接编辑 reference/legal_knowledge_base.json')
    b.bullet('Q：如何更新教学合规标准？ A：直接编辑 reference/curriculum_requirements.json')

    if _STREAM is None:
        b.save(out or '05_使用说明手册.pdf')


_STREAM = None  # 流式合并模式：非 None 时各 build 函数续写该文档（合并版连续排版，不留空白页）


DOC_FILES = [
    ('01_需求分析报告.pdf', '01', '需求分析报告', 'Requirements Analysis Report',
     '项目背景 · 问题定义 · 用户分析 · 功能与非功能需求'),
    ('02_框架设计说明书.pdf', '02', '框架设计说明书', 'Framework Design Specification',
     '四层模块化架构 · 知识库与脚本引擎 · 数据流设计'),
    ('03_测试用例报告.pdf', '03', '测试用例报告', 'Test Cases Report',
     '测试策略 · 集成用例 TC001-TC020 · 基准与回归'),
    ('04_功能及性能指标.pdf', '04', '功能及性能指标', 'Functional & Performance Metrics',
     '功能指标 · 响应时间 · 实证基线对比 · 可靠性'),
    ('05_使用说明手册.pdf', '05', '使用说明手册', 'User Manual',
     '安装部署 · 模块使用 · 命令行参考 · 版本与升级'),
]

_BUILDERS = {
    '01': build_req_analysis, '02': build_framework, '03': build_test_cases,
    '04': build_performance, '05': build_manual,
}


def build_merged():
    """合并 5 份文档：连续流式排版（章节首尾相接，不留空白页），唯一总封面 + 目录 + 每章分级章标题条"""
    global _STREAM
    _STREAM = PDFBuilder('产品技术文档', 'LegalGuardian v4.3.0', '2026-08-19',
                         '西南民族大学法学院参赛团队', cover=False)
    ranges = []
    for fn, num, title, _sub, _desc in DOC_FILES:
        _BUILDERS[num]()
        ranges.append((_STREAM.chapter_page, _STREAM.doc.page_count, int(num), title))
    doc = _STREAM.doc
    end_y = _STREAM.y
    _STREAM = None

    # 第 1 页：总封面 + 目录
    doc.insert_page(0, width=PAGE_W, height=PAGE_H)
    page = doc[0]
    page.insert_font(fontname=FONT, fontfile=FONT_FILE)
    page.insert_font(fontname=FONT_BOLD, fontfile=FONT_BOLD_FILE)
    y = 160
    page.insert_text((MARGIN, y), 'LegalGuardian', fontname=FONT_BOLD, fontsize=32, color=NAVY)
    y += 42
    page.insert_text((MARGIN, y), '产品技术文档', fontname=FONT_BOLD, fontsize=24)
    y += 34
    page.insert_text((MARGIN, y), 'v4.3.0 · 2026-08-19 · 西南民族大学法学院参赛团队',
                     fontname=FONT, fontsize=11, color=GRAY)
    y += 16
    page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_W - MARGIN, y), color=GOLD, width=0.9)
    y += 38
    page.insert_text((MARGIN, y), '目　录', fontname=FONT_BOLD, fontsize=15, color=NAVY)
    y += 30
    for i, (fn, num, title, sub, desc) in enumerate(DOC_FILES):
        s, e, _n, _t = ranges[i]
        page.insert_text((MARGIN + 14, y), num, fontname=FONT_BOLD, fontsize=11, color=GOLD)
        page.insert_text((MARGIN + 42, y), title, fontname=FONT_BOLD, fontsize=12, color=NAVY)
        page.insert_text((MARGIN + 42, y + 17), desc, fontname=FONT, fontsize=9, color=GRAY)
        pno = str(s + 2).zfill(2)  # 章首 1-based 页码（目录页为 01）
        w = _wlen(pno, 9)
        page.insert_text((PAGE_W - MARGIN - w, y), pno, fontname=FONT, fontsize=9, color=GRAY)
        y += 60
    total = doc.page_count
    page.draw_line(fitz.Point(MARGIN, y + 6), fitz.Point(PAGE_W - MARGIN, y + 6),
                   color=(0.85, 0.87, 0.90), width=0.6)
    page.insert_text((MARGIN, y + 24), f'本合集包含 5 份技术文档 · 共 {total} 页',
                     fontname=FONT, fontsize=9, color=GRAY)
    info = '版本 v4.3.0 · 2026-08-19'
    w = _wlen(info, 9)
    page.insert_text((PAGE_W - MARGIN - w, y + 24), info, fontname=FONT, fontsize=9, color=GRAY)
    pno = '· 01 ·'
    w = _wlen(pno, 8.5)
    page.insert_text(((PAGE_W - w) / 2, PAGE_H - 26), pno, fontname=FONT, fontsize=8.5, color=GRAY)

    # 正文页脚：居中页码 + 左侧章节归属 + 右侧项目名
    for idx in range(1, total):
        p = doc[idx]
        pno = f'· {idx + 1:02d} ·'
        w = _wlen(pno, 8.5)
        p.insert_text(((PAGE_W - w) / 2, PAGE_H - 26), pno,
                      fontname=FONT, fontsize=8.5, color=GRAY)
        src_idx = idx - 1
        cur = None
        for s, e, n, t in ranges:
            if s <= src_idx:
                cur = (s, e, n, t)
            else:
                break
        if cur:
            p.insert_text((MARGIN, PAGE_H - 26), f'第 {cur[2]} 章　{cur[3]}',
                          fontname=FONT, fontsize=8, color=GRAY)
        txt = 'LegalGuardian v4.3.0'
        w = _wlen(txt, 8)
        p.insert_text((PAGE_W - MARGIN - w, PAGE_H - 26), txt,
                      fontname=FONT, fontsize=8, color=GRAY)

    # 末页结束标记（收尾留白区，消除空白感）
    end_page = doc[doc.page_count - 1]
    end_page.draw_line(fitz.Point(MARGIN, end_y + 28), fitz.Point(PAGE_W - MARGIN, end_y + 28),
                       color=(0.85, 0.87, 0.90), width=0.6)
    t = '— 文档完 —'
    w = _wlen(t, 9)
    end_page.insert_text(((PAGE_W - w) / 2, end_y + 46), t,
                         fontname=FONT, fontsize=9, color=GRAY)

    merged = doc
    merged.set_metadata({
        'title': 'LegalGuardian v4.3.0 产品技术文档（合并版）',
        'author': '西南民族大学法学院参赛团队',
        'creator': 'PyMuPDF',
        'subject': 'LegalGuardian v4.3.0'
    })
    _save_small(merged, os.path.join(OUT_DIR, '产品技术文档.pdf'))
    merged.close()
    print(f'✓ 生成 产品技术文档.pdf（共 {total} 页，流式排版无空白页）')


if __name__ == '__main__':
    print('=== 生成 LegalGuardian v4.3.0 技术文档（紧凑版）===')
    build_req_analysis()
    build_framework()
    build_test_cases()
    build_performance()
    build_manual()
    build_merged()
    print('=== 全部完成 ===')
