# -*- coding: utf-8 -*-
"""
v4.2.0 技术文档 PDF 生成器
使用 PyMuPDF 生成5份技术文档，版本对齐 v4.2.0
"""
import fitz
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT = 'china-s'
TITLE = 'china-s'
BODY_SIZE = 10
HEAD1_SIZE = 14
HEAD2_SIZE = 12
HEAD3_SIZE = 11
MARGIN = 50
PAGE_W = 595  # A4
PAGE_H = 842
LINE_H = 16
BODY_GAP = 6


class PDFBuilder:
    def __init__(self, title, version, date, team):
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
        self.y = MARGIN

    def _ensure_space(self, needed=60):
        if self.y + needed > PAGE_H - MARGIN:
            self._new_page()

    def _write(self, text, size=BODY_SIZE, bold=False, color=(0, 0, 0), indent=0):
        self._ensure_space(size + BODY_GAP)
        x = MARGIN + indent
        self.page.insert_text((x, self.y), text, fontname=FONT, fontsize=size,
                              color=color, render_mode=0)
        self.y += size + BODY_GAP

    def _write_wrapped(self, text, size=BODY_SIZE, indent=0, color=(0, 0, 0)):
        max_chars = int((PAGE_W - MARGIN * 2 - indent) / (size * 0.9))
        words = text
        # 按字符宽度简单换行（中文）
        lines = []
        cur = ''
        for ch in words:
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur)
                cur = ''
        if cur:
            lines.append(cur)
        for ln in lines:
            self._write(ln, size=size, indent=indent, color=color)

    def add_cover(self, subtitle=''):
        # 封面页
        self.y = 250
        self._write('LegalGuardian', size=30, bold=True, color=(0.2, 0.3, 0.6))
        self._write('法律守卫', size=24, bold=True)
        self._write('')
        self._write(self.title, size=18, bold=True)
        if subtitle:
            self._write(subtitle, size=12)
        self._write('')
        self._write('')
        self._write(self.version, size=14)
        self._write(self.date, size=12)
        self._write('')
        self._write(self.team, size=12)

    def add_heading(self, text, level=1):
        self._ensure_space(30)
        if level == 1:
            self._write('', size=6)
            self._write(text, size=HEAD1_SIZE, bold=True, color=(0.15, 0.25, 0.5))
        elif level == 2:
            self._write(text, size=HEAD2_SIZE, bold=True, color=(0.2, 0.3, 0.5))
        else:
            self._write(text, size=HEAD3_SIZE, bold=True)

    def add_para(self, text):
        self._write_wrapped(text, size=BODY_SIZE)

    def add_bullet(self, text):
        self._write_wrapped('• ' + text, size=BODY_SIZE, indent=8)

    def add_table(self, headers, rows):
        self._ensure_space(80)
        col_w = (PAGE_W - MARGIN * 2) / len(headers)
        row_h = 22
        start_y = self.y

        def draw_row(y, cells, is_header=False):
            max_lines = 1
            for ci, cell in enumerate(cells):
                x = MARGIN + ci * col_w
                text_lines = self._wrap_cell(cell, col_w)
                max_lines = max(max_lines, len(text_lines))
                if is_header:
                    self.page.draw_rect(fitz.Rect(x, y, x + col_w, y + row_h * max_lines),
                                        color=(0.15, 0.25, 0.5), fill=(0.15, 0.25, 0.5))
                else:
                    self.page.draw_rect(fitz.Rect(x, y, x + col_w, y + row_h * max_lines),
                                        color=(0.6, 0.6, 0.6))
            for ci, cell in enumerate(cells):
                x = MARGIN + ci * col_w + 4
                text_lines = self._wrap_cell(cell, col_w)
                for li, ln in enumerate(text_lines):
                    col = (1, 1, 1) if is_header else (0, 0, 0)
                    self.page.insert_text((x, y + 12 + li * 12), ln, fontname=FONT,
                                          fontsize=8.5, color=col)
            return y + row_h * max_lines

        # 绘制表头
        self.y = draw_row(self.y, headers, is_header=True) + 4
        for row in rows:
            if self.y + 40 > PAGE_H - MARGIN:
                self._new_page()
            self.y = draw_row(self.y, row, is_header=False) + 4
        self.y += 6

    def _wrap_cell(self, text, col_w):
        """按列宽换行"""
        if not text:
            return ['']
        max_chars = max(1, int((col_w - 8) / 9.5))
        lines = []
        cur = ''
        for ch in str(text):
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur)
                cur = ''
        if cur:
            lines.append(cur)
        return lines

    def save(self, filename):
        self.doc.set_metadata({
            'title': self.title,
            'author': '西南民族大学法学院徐子涵团队',
            'creator': 'PyMuPDF',
            'subject': self.version
        })
        self.doc.save(os.path.join(OUT_DIR, filename))
        self.doc.close()
        print(f'✓ 生成 {filename}')


def build_req_analysis():
    b = PDFBuilder('需求分析报告', 'LegalGuardian v4.2.0', '2026-08-05',
                   '西南民族大学法学院徐子涵团队')
    b.add_cover(subtitle='Requirements Analysis Report')

    b.add_heading('1. 项目背景', 1)
    b.add_para('随着大型语言模型在法律领域的广泛应用，法学生和非专业人士越来越频繁地使用AI进行法律信息检索和分析。'
               '西南民族大学法学院徐子涵团队2026年5月完成的实证研究对DeepSeek和千问Qwen3.5进行14个案例、2轮测试、'
               '4维测评，揭示了AI法律工具存在系统性的失效模式。')
    b.add_para('关键实证发现：千问对虚构法条识别率为0%；DS在许某某案中量刑预测误差高达71%（预测3.5年 vs 实际6年）；'
               '引导性得分DS平均仅2.96/5、千问仅1.70/5。')
    b.add_para('v4.1.0在v4.0.0基础上新增教信赛智慧评价赛道能力，覆盖教学大纲AI合规审核、智能考试全流程管理、'
               '教学质量多维评价三大方向。')
    b.add_para('v4.2.0完成全面性能优化与正确性修复：JSON知识库模块级缓存、作业评估进程内检测调用消除子进程启动开销、'
               '主观题评分归一化（满分作文不再误判不及格）、引用已废止法律红线规则修复、F1-F3检测→纠正链路对齐、'
               '全脚本解释器统一与健壮性重构。')

    b.add_heading('2. 问题定义', 1)
    b.add_bullet('准确性危机：AI可能引用虚构或已废止的法律（千问接受"人格权侵害惩治条例"为真实法律）')
    b.add_bullet('深度缺失：AI倾向提供"浅度正确"的回答——结论正确但缺乏深度法理分析')
    b.add_bullet('引导性不足：AI告诉用户"问题在哪"但不告诉"怎么解决"，DS引导性平均2.96/5')
    b.add_bullet('前提验证盲区：AI天然"相信"用户输入，不验证前提假设是否成立')
    b.add_bullet('用户差异化风险：同一回答对法学生和非专业人士的风险完全不同')
    b.add_bullet('v4.1.0新增：教学场景失效模式（试题歧义/评分偏移/格式违规/跨题矛盾/教学合规偏离）')

    b.add_heading('3. 目标用户分析', 1)
    b.add_table(
        ['用户类型', '核心需求', '风险等级'],
        [
            ['法学本科生/研究生', '深度法理分析、失效模式识别训练、AI辅助作业', '中'],
            ['法学教师', '教学材料审核、AI输出验证、作业批改辅助', '中低'],
            ['非专业社会人士', '通俗解释、醒目风险警示、律师咨询引导', '高'],
            ['AI工具开发者', '三维规制符合性评估、失效模式诊断', '中'],
            ['教务管理者(v4.1)', '教学大纲合规审核、教学质量多维评价', '中'],
        ]
    )

    b.add_heading('4. 功能需求', 1)
    b.add_heading('4.1 模块A：AI法律回答审核纠正', 2)
    b.add_bullet('F-A1：24大失效模式(F1-F24)自动检测——关键词规则+模式匹配')
    b.add_bullet('F-A2：8项安全检查清单执行（safety_checker.py，v4.1.0新增）')
    b.add_bullet('F-A3：四维评分+实证基线对比')
    b.add_heading('4.2 模块B：提问优化与模板推荐', 2)
    b.add_bullet('F-B1：陷阱自动识别（废止法律引用、量刑预测、未验证前提）')
    b.add_bullet('F-B2：5大模板+竞赛场景智能匹配（v4.1.0新增教信赛场景检测）')
    b.add_bullet('F-B3：问题优化生成')
    b.add_heading('4.3 模块C：法学作业评估与评分', 2)
    b.add_bullet('F-C1：8大题型(T1-T8)差异化评分')
    b.add_bullet('F-C2：红线规则（D1=0→总分归零；F24合规偏离→大纲审核不通过）')
    b.add_bullet('F-C3：24种失效模式同步检测+改进计划生成')
    b.add_heading('4.4 模块D：三维规制符合性评估', 2)
    b.add_bullet('F-D1：技术规范(T1-T5)  F-D2：教育引导(E1-E4)  F-D3：法律保障(L1-L4)')
    b.add_heading('4.5 模块E：教学大纲AI合规审核（v4.1.0新增）', 2)
    b.add_bullet('F-E1：核心知识点覆盖率核验（教育部国家标准，要求≥80%）')
    b.add_bullet('F-E2：缺失知识点清单生成')
    b.add_bullet('F-E3：大纲修订建议')

    b.add_heading('5. 非功能需求', 1)
    b.add_table(
        ['需求类别', '指标', '要求'],
        [
            ['性能', '失效模式检测', '<=5秒/次'],
            ['性能', '法学作业评估', '<=60秒/次'],
            ['可靠性', '失效模式覆盖率', '24/24模式(F1-F24)全覆盖'],
            ['可靠性', '虚构法律识别准确率', '>=95%'],
            ['可维护性', '知识库更新', 'JSON独立于脚本，可直接替换'],
            ['可扩展性', '新增失效模式', 'candidate_patterns字段'],
            ['兼容性', '输入格式', '.txt/.md/.docx'],
            ['兼容性', '模型基座', 'Qwen3-Next-80B等5个系列'],
            ['兼容性', '部署平台', 'AI龙虾智能体平台'],
        ]
    )

    b.add_heading('6. 约束条件', 1)
    b.add_bullet('模型基座限定：推理Qwen3-Next-80B/嵌入Qwen3-Embedding-8B/重排Qwen3-Reranker-8B/多模态Qwen3-VL-32B/语音Qwen3-ASR/TTS')
    b.add_bullet('平台限定：须在AI龙虾智能体开发平台上完成部署和演示')
    b.add_bullet('算力限定：基于国产芯片算力环境')
    b.add_bullet('法律定位：本Skill不替代律师/教师，不做终局性法律判断')
    b.add_bullet('实证基线不可修改：所有纠正建议必须引用14案例×2轮×4维实证测试数据')
    b.add_bullet('竞赛铁律：评分可复现（偏差≤0.2分）、评分可校准（对照实证基线）')

    b.save('01_需求分析报告.pdf')


def build_framework():
    b = PDFBuilder('框架设计说明书', 'LegalGuardian v4.2.0', '2026-08-05',
                   '西南民族大学法学院徐子涵团队')
    b.add_cover(subtitle='Framework Design Specification')

    b.add_heading('1. 总体架构', 1)
    b.add_para('LegalGuardian采用四层模块化架构：知识库层(reference/)、脚本引擎层(scripts/)、'
               '逻辑编排层(SKILL.md)、输出模板层(templates/)。各层通过JSON接口标准化通信，实现数据与逻辑的完全解耦。')
    b.add_para('v4.1.0知识库层扩展至11个JSON文件，脚本引擎层扩展至12个Python脚本。')

    b.add_heading('2. 知识库层设计', 1)
    b.add_heading('2.1 failure_patterns.json — 24大失效模式知识库', 2)
    b.add_para('含F1-F10通用模式（14案例实证）、F11-F18题型特化模式（法考校准）、'
               'F19-F24教信赛场景模式（v4.1.0新增）。每个模式含：id、名称、严重度、频次、现象、'
               '实证证据、检测关键词、纠正策略。dimension_mapping_v2定义四维评分关联矩阵。')
    b.add_heading('2.2 curriculum_requirements.json — 教育部课程要求（v4.1.0新增）', 2)
    b.add_para('教育部法学类教学质量国家标准核心知识点映射，覆盖法理学/宪法/民法/刑法/行政法/诉讼法/'
               '国际法/经济法八大领域，18个必授知识点，供F24教学大纲合规偏离检测使用。')
    b.add_heading('2.3 其他知识库', 2)
    b.add_table(
        ['文件', '内容'],
        [
            ['test_baseline.json', '14案例实证基线（DS 3.84 vs 千问3.06）'],
            ['correction_templates.json', '5大提问模板+竞赛场景匹配规则'],
            ['safety_checklist.json', '8项安全检查清单'],
            ['three_d_regulation.json', '三维规制路径(T1-T5/E1-E4/L1-L4)'],
            ['question_type_rubrics.json', '8题型差异化评分标准'],
            ['assignment_rubric.json', '五维评分标准'],
            ['legal_knowledge_base.json', '核心法条+废止预警'],
            ['case_knowledge_base.json', '案例知识库'],
        ]
    )

    b.add_heading('3. 脚本引擎层设计', 1)
    b.add_heading('3.1 failure_detector.py — 24模式检测引擎', 2)
    b.add_para('F1-F24逐模式检测函数，输出概率/严重度/检测依据。v4.1.0新增detect_f19至detect_f24。')
    b.add_heading('3.2 correction_engine.py — 纠正引擎', 2)
    b.add_para('v4.1.0扩展至F1-F24全覆盖纠正生成器，每个纠正含实证依据+修正方向+替代表述。')
    b.add_heading('3.3 safety_checker.py — 安全检查执行器（v4.1.0新增）', 2)
    b.add_para('执行reference/safety_checklist.json的8项检查，输出通过率+总体风险等级。')
    b.add_heading('3.4 template_matcher.py — 模板匹配器', 2)
    b.add_para('v4.1.0新增教信赛竞赛场景检测：教学大纲审核→[T1+T4+T5]、考试设计→[T3+T5]、评分一致性→[T5+T4]。')
    b.add_heading('3.5 其他脚本', 2)
    b.add_bullet('question_type_classifier.py — T1-T8题型识别与路由')
    b.add_bullet('answer_key_evaluator.py — 答案键验证与批量评分')
    b.add_bullet('law_assignment_evaluator_v2.py — 8题型统一评估器')
    b.add_bullet('calibrate_scoring.py — 评分校准器')
    b.add_bullet('exam_parser.py — 法考真题解析')
    b.add_bullet('scoring_engine.py — 四维评分')
    b.add_bullet('legal_db_fetcher.py — 法律检索')

    b.add_heading('4. 数据流设计', 1)
    b.add_para('用户输入(AI回复/问题/作业/教学大纲)→模块入口→知识库加载→脚本执行→JSON→模板渲染→最终报告。'
               '模块A审核链：failure_detector→correction_engine→safety_checker三阶段串联。'
               '教学合规审核链（v4.1.0）：大纲解析→curriculum_requirements对照→F24检测→合规报告。')

    b.add_heading('5. 目录结构', 1)
    b.add_para('scripts/ 12个Python脚本 | reference/ 11个JSON知识库 | templates/ 2个模板 | '
               'benchmark/ 黄金标准基准 | tests/ 集成测试 | test_data/ 案例数据')

    b.save('02_框架设计说明书.pdf')


def build_test_cases():
    b = PDFBuilder('测试用例报告', 'LegalGuardian v4.2.0', '2026-08-05',
                   '西南民族大学法学院徐子涵团队')
    b.add_cover(subtitle='Test Cases Report')

    b.add_heading('1. 测试策略', 1)
    b.add_para('三层架构：单元测试(函数级验证)、集成测试(脚本间管道串联)、端到端测试(真实场景模拟)。'
               'v4.1.0测试范围扩展：12个Python脚本、11个JSON知识库、24种失效模式(F1-F24)。')

    b.add_heading('2. 核心集成测试用例（TC001-TC010）', 1)
    b.add_table(
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
        ]
    )

    b.add_heading('3. v4.1.0新增测试用例（TC011-TC020）', 1)
    b.add_table(
        ['编号', '模块', '名称', '结果'],
        [
            ['TC011', 'A-安全', 'safety_checker 8项检查执行', '通过'],
            ['TC012', 'C-F11', '选项混淆纠正建议生成', '通过'],
            ['TC013', 'C-F12', '采分点遗漏纠正建议生成', '通过'],
            ['TC014', 'C-F17', '三段论缺失纠正建议生成', '通过'],
            ['TC015', 'E-F24', '教学大纲合规偏离检测', '通过'],
            ['TC016', 'E-F24', '核心知识点覆盖率<80%触发', '通过'],
            ['TC017', 'B-竞赛', '教学大纲审核→[T1+T4+T5]匹配', '通过'],
            ['TC018', 'B-竞赛', '考试设计→[T3+T5]匹配', '通过'],
            ['TC019', '检测-F19', '试题歧义检测', '通过'],
            ['TC020', '检测-F22', '跨题一致性检测', '通过'],
        ]
    )

    b.add_heading('4. 基准测试结果（2026-08-05）', 1)
    b.add_table(
        ['指标', '结果'],
        [
            ['题型识别准确率', '100% (16/16 全量)'],
            ['失效模式体系', 'F1-F24 全覆盖'],
            ['检测→纠正链路', '100% 命中即纠正'],
            ['教学合规审核', 'F24覆盖率阈值80%验证通过'],
            ['综合评级', 'A (优秀校准)'],
        ]
    )

    b.add_heading('5. 回归测试（REG-001至REG-010）', 1)
    b.add_para('包含4项基础回归测试（REG-001至REG-004）与6项v4.1.0新增回归测试（REG-005至REG-010），'
               '覆盖F19-F24的检测验证：教学大纲合规、跨题一致性、试题歧义、格式违规、评分偏移、采分点粒度。')

    b.save('03_测试用例报告.pdf')


def build_performance():
    b = PDFBuilder('功能及性能指标', 'LegalGuardian v4.2.0', '2026-08-05',
                   '西南民族大学法学院徐子涵团队')
    b.add_cover(subtitle='Functional & Performance Metrics')

    b.add_heading('1. 功能指标汇总', 1)
    b.add_table(
        ['模块', '功能数', '核心指标'],
        [
            ['A: AI回答审核', '8项', '24/24失效模式覆盖，四维评分+基线对比'],
            ['A: 安全检查(v4.1)', '8项', '8项安全检查清单执行，风险联动'],
            ['B: 提问优化', '4项', '5模板+竞赛场景匹配'],
            ['C: 作业评估', '5项', '8题型差异化评分，红线规则100%执行'],
            ['D: 三维评估', '3项', '13项(T+E+L)全覆盖'],
            ['E: 教学合规(v4.1)', '3项', '核心知识点覆盖率核验（≥80%）'],
            ['全流程', '1项', '检测→纠正→安全→评分→报告管道'],
        ]
    )

    b.add_heading('2. 响应时间', 1)
    b.add_table(
        ['操作', '目标', '实测'],
        [
            ['失效模式检测', '<=5秒', '<=3秒'],
            ['纠正建议生成', '<=10秒', '<=8秒'],
            ['安全检查执行(v4.1)', '<=5秒', '<=2秒'],
            ['模板匹配+优化', '<=5秒', '<=3秒'],
            ['作业评估', '<=60秒', '<=45秒'],
            ['全流程审核链', '<=45秒', '<=30秒'],
            ['教学合规审核(v4.1)', '<=30秒', '<=20秒'],
        ]
    )

    b.add_heading('3. 实证基线对比', 1)
    b.add_table(
        ['维度', 'DS基线', '千问基线', 'LG目标', '提升'],
        [
            ['准确性', '4.03', '3.49', '>=4.5', '+0.47'],
            ['时效性', '4.69', '4.13', '>=4.5', '-0.19(保守)'],
            ['逻辑性', '3.66', '2.93', '>=4.0', '+0.34'],
            ['引导性', '2.96', '1.70', '>=3.0', '+0.04'],
            ['综合', '3.84', '3.06', '>=4.0', '+0.16'],
        ]
    )

    b.add_heading('4. 可靠性指标', 1)
    b.add_bullet('虚构法律识别率目标100%（千问基线0%）')
    b.add_bullet('废止法律标注率目标100%')
    b.add_bullet('引导性最低阈值3.0/5（实证最弱维度）')
    b.add_bullet('红线规则执行率100%（D1=0→归零）')
    b.add_bullet('评分可复现性：同一输入偏差<=0.2分（确定性规则）')
    b.add_bullet('教学合规阈值：核心知识点覆盖率>=80%（F24）')

    b.add_heading('5. 资源消耗与可扩展性', 1)
    b.add_table(
        ['指标', '当前值', '扩展能力'],
        [
            ['Skill包大小', '~800KB', '<=1MB'],
            ['知识库大小', '~1.2MB(11文件)', '<=2MB'],
            ['模型调用', '推理<2000 token', '单次审核'],
            ['失效模式', '24个(F1-F24)', 'candidate_patterns扩展'],
            ['基准测试', '16项+10回归', 'items数组追加'],
        ]
    )

    b.save('04_功能及性能指标.pdf')


def build_manual():
    b = PDFBuilder('使用说明手册', 'LegalGuardian v4.2.0', '2026-08-05',
                   '西南民族大学法学院徐子涵团队')
    b.add_cover(subtitle='User Manual')

    b.add_heading('1. 概述', 1)
    b.add_para('LegalGuardian(法律守卫)是基于实证数据的AI法律对话审查纠正与法学作业评估Skill。'
               'v4.2.0覆盖24种失效模式(F1-F24)、8大题型(T1-T8)、教学大纲AI合规审核，'
               '并完成性能优化（知识库模块级缓存、进程内检测调用）与正确性修复'
               '（主观题评分归一化、红线规则、检测→纠正链路对齐）。'
               '面向法学学生/教师、教务管理者、非专业社会人士、AI工具开发者。')

    b.add_heading('2. 安装部署', 1)
    b.add_bullet('前提：AI龙虾智能体平台账号+Qwen3系列模型权限+Python 3.10+')
    b.add_bullet('步骤1：获取Skill包(legal-guardian.skill)或git clone https://github.com/Phillnarsoeer/legal-guardian')
    b.add_bullet('步骤2：AI龙虾平台→技能管理→上传技能→选择.skill文件→确认')
    b.add_bullet('步骤3：验证——在对话中提及法律问题，确认Skill自动激活')

    b.add_heading('3. 核心模块使用指南', 1)
    b.add_heading('3.1 模块A：AI法律回答审核纠正', 2)
    b.add_para('场景：获得AI法律回答，需验证准确性并获取纠正建议。对话方式：粘贴AI回答，附言"请审核这段AI法律回答"。'
               '命令行：python scripts/failure_detector.py input.txt | python scripts/correction_engine.py --stdin | python scripts/safety_checker.py --stdin')
    b.add_heading('3.2 模块B：提问优化与模板推荐', 2)
    b.add_para('场景：准备向AI提问法律问题。对话方式：写出原始问题，附言"请优化这个问题的提问方式"。')
    b.add_heading('3.3 模块C：法学作业评估与评分', 2)
    b.add_para('场景：提交法学作业，进行8大题型差异化评分。命令行：python scripts/law_assignment_evaluator_v2.py 作业.docx')
    b.add_heading('3.4 模块D：三维规制符合性评估', 2)
    b.add_para('场景：评估AI法律工具合规性。输出技术T1-T5+教育E1-E4+法律L1-L4逐项报告。')
    b.add_heading('3.5 模块E：教学大纲AI合规审核（v4.1.0新增）', 2)
    b.add_para('场景：上传法学教学大纲，核验是否符合教育部课程标准和必授知识点要求。'
               '对话方式：粘贴教学大纲内容，附言"请审核这份教学大纲的合规性"。'
               '系统自动检测F24教学大纲合规偏离，输出覆盖率+缺失知识点清单+修订建议。')

    b.add_heading('4. 安全检查使用（v4.1.0新增）', 1)
    b.add_para('对所有审核结果执行8项安全检查清单(C1-C8)，覆盖：法条来源核对、罪名定性反向思考、'
               '量刑预测风险边界、多平台交叉验证、遗漏争点、需人工核实标注、不替代律师、计算一致性。')

    b.add_heading('5. 命令行快速参考', 1)
    b.add_para('# 模块A - AI回答审核')
    b.add_para('python scripts/failure_detector.py input.txt')
    b.add_para('python scripts/correction_engine.py result.json')
    b.add_para('python scripts/safety_checker.py input.txt --detections result.json')
    b.add_para('# 模块B - 提问优化')
    b.add_para('python scripts/template_matcher.py "原始问题"')
    b.add_para('# 模块C - 作业评估')
    b.add_para('python scripts/law_assignment_evaluator_v2.py 作业.docx')
    b.add_para('# 模块E - 教学大纲合规审核')
    b.add_para('python scripts/failure_detector.py 大纲.txt  (检测F24)')

    b.add_heading('6. 常见问题', 1)
    b.add_bullet('Q: Skill未自动激活？A: 检查manifest.yaml的description关键词，确认Skill已启用')
    b.add_bullet('Q: 检测到但无纠正建议？A: 确认reference/下所有JSON知识库文件完整')
    b.add_bullet('Q: 如何更新法律知识？A: 直接编辑reference/legal_knowledge_base.json')
    b.add_bullet('Q: 如何更新教学合规标准？A: 直接编辑reference/curriculum_requirements.json')

    b.save('05_使用说明手册.pdf')


if __name__ == '__main__':
    print('=== 生成 LegalGuardian v4.2.0 技术文档 ===')
    build_req_analysis()
    build_framework()
    build_test_cases()
    build_performance()
    build_manual()
    print('=== 全部完成 ===')
