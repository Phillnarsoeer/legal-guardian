# -*- coding: utf-8 -*-
"""作品演示 PPT 生成器 —— LegalGuardian v4.3.0（22 页，16:9）
深蓝+金色法律风；覆盖：背景痛点/需求/方案设计/技术实现/创新点/教育应用场景/实施效果。
"""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')

NAVY = '16355C'
NAVY_D = '0F2440'
GOLD = 'C9A227'
BLUE2 = '4A6FA5'
BG = 'F5F7FA'
CARD = 'FFFFFF'
LINE = 'D9E0EA'
TXT = '1F2937'
GRAY = '6B7280'
LIGHT = 'EFF3F8'
WHITE = 'FFFFFF'
RISK = 'B03A2E'
GOOD = '1E7A46'

SW, SH = 13.333, 7.5
FONT = '微软雅黑'
TOTAL = 23


def C(hexs):
    return RGBColor.from_string(hexs)


def set_font(run, size=12, bold=False, color=TXT, name=FONT):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.name = name
    f.color.rgb = C(color)
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {})
        rPr.append(ea)
    ea.set('typeface', name)


def text(slide, x, y, w, h, paras, anchor='t', wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}[anchor]
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[pd.get('align', 'l')]
        p.space_after = Pt(pd.get('gap', 2))
        p.line_spacing = pd.get('ls', 1.08)
        for rd in pd['runs']:
            r = p.add_run()
            r.text = rd[0]
            set_font(r, rd[1], rd[2], rd[3])
    return tb


def shape(slide, kind, x, y, w, h, fill=None, line=None, lw=0.75, radius=None):
    sp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius is not None:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    if fill:
        sp.fill.solid()
        sp.fill.fore_color.rgb = C(fill)
    else:
        sp.fill.background()
    if line:
        sp.line.color.rgb = C(line)
        sp.line.width = Pt(lw)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def rect(slide, x, y, w, h, fill, line=None, radius=None):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, radius=radius)


def card(slide, x, y, w, h, title, body, tsize=13.5, bsize=10.5, tcolor=None,
         fill=CARD, line=LINE, body_paras=None, title_color=None):
    rect(slide, x, y, w, h, fill, line, radius=0.045)
    paras = [{'runs': [(title, tsize, True, title_color or NAVY)], 'gap': 3}]
    if body_paras:
        paras += body_paras
    elif body:
        paras.append({'runs': [(body, bsize, False, GRAY)], 'gap': 0, 'ls': 1.12})
    text(slide, x + 0.22, y + 0.18, w - 0.44, h - 0.36, paras)


def chip(slide, x, y, w, h, label, fill=LIGHT, color=NAVY, size=10.5, bold=True, line=None):
    rect(slide, x, y, w, h, fill, line, radius=0.25)
    text(slide, x, y + 0.03, w, h - 0.06,
         [{'runs': [(label, size, bold, color)], 'align': 'c'}], anchor='m')


def header(slide, tag, title, sub=None):
    text(slide, 0.55, 0.30, 10, 0.3, [{'runs': [(tag, 10.5, True, GOLD)]}])
    text(slide, 0.55, 0.56, 12.2, 0.62, [{'runs': [(title, 25, True, NAVY)]}])
    shape(slide, MSO_SHAPE.RECTANGLE, 0.57, 1.18, 1.35, 0.045, fill=GOLD)
    if sub:
        text(slide, 0.57, 1.30, 12.2, 0.34, [{'runs': [(sub, 11, False, GRAY)]}])
        return 1.85
    return 1.60


def footer(slide, n):
    shape(slide, MSO_SHAPE.RECTANGLE, 0.55, 7.08, 12.23, 0.012, fill=LINE)
    text(slide, 11.6, 7.14, 1.2, 0.3,
         [{'runs': [(f'{n:02d} / {TOTAL}', 9, False, '9AA3B2')], 'align': 'r'}])


def table(slide, x, y, w, headers, rows, col_w, font=10, head_fill=NAVY,
          row_h=0.40, zebra='F3F6FA'):
    n = len(headers)
    gt = slide.shapes.add_table(len(rows) + 1, n, Inches(x), Inches(y),
                                Inches(w), Inches(row_h * (len(rows) + 1))).table
    gt.first_row = True
    gt.horz_banding = False

    def fill_cell(cell, txt, bold, color, fill, size=font):
        cell.fill.solid()
        cell.fill.fore_color.rgb = C(fill)
        cell.margin_left = Inches(0.10)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.02)
        cell.margin_bottom = Inches(0.02)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = txt
        set_font(r, size, bold, color)

    for ci, cw in enumerate(col_w):
        gt.columns[ci].width = Inches(cw)
    for ci, htxt in enumerate(headers):
        fill_cell(gt.cell(0, ci), htxt, True, WHITE, head_fill)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            fill_cell(gt.cell(ri + 1, ci), val, False, TXT, WHITE if ri % 2 == 0 else zebra)
    return gt


def band(slide, y, h, title, body, fill=LIGHT, x=0.55, w=12.23, tsize=12.5, bsize=10):
    rect(slide, x, y, w, h, fill, None, radius=0.03)
    paras = [{'runs': [(title, tsize, True, NAVY)], 'gap': 2}]
    if body:
        paras.append({'runs': [(body, bsize, False, TXT)], 'gap': 0, 'ls': 1.14})
    text(slide, x + 0.25, y + 0.13, w - 0.5, h - 0.26, paras)


def new_slide(prs, bg=BG):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = C(bg)
    return s


# ---------------------------------------------------------------- slides

def s01_cover(prs):
    s = new_slide(prs, NAVY)
    text(s, 0.9, 0.85, 10, 0.35,
         [{'runs': [('AI 龙虾智能体平台 · 教育 Skill 创新设计大赛', 12, True, GOLD)]}])
    text(s, 0.9, 1.85, 11.5, 0.9, [{'runs': [('LegalGuardian 法律守卫', 44, True, WHITE)]}])
    shape(s, MSO_SHAPE.RECTANGLE, 0.95, 2.98, 2.1, 0.05, fill=GOLD)
    text(s, 0.9, 3.35, 11.6, 0.5,
         [{'runs': [('面向法学教育的 AI 法律输出审核 · 纠正 · 评估 Skill', 17, False, 'E8ECF4')]}])
    text(s, 0.9, 4.05, 11.6, 0.4,
         [{'runs': [('24 种失效模式检测 · 8 大题型评估 · 教学大纲合规审核 · 5,515 案例库检索',
                     11.5, False, 'A7B4C8')]}])
    shape(s, MSO_SHAPE.RECTANGLE, 0, 6.35, 13.333, 0.045, fill=GOLD)
    text(s, 0.9, 6.62, 11.5, 0.4,
         [{'runs': [('西南民族大学法学院参赛团队　　|　　v4.3.0　　|　　2026-08', 12, False, 'D6DEEA')]}])
    footer(s, 1)


def s02_toc(prs):
    s = new_slide(prs)
    text(s, 0.55, 0.42, 8, 0.75, [{'runs': [('目录', 30, True, NAVY)]}])
    shape(s, MSO_SHAPE.RECTANGLE, 0.57, 1.22, 1.5, 0.045, fill=GOLD)
    items = [
        ('01', '背景与痛点', '实证研究：AI 法律工具的系统性失效'),
        ('02', '方案设计', '五模块闭环：检测 · 纠正 · 安全 · 评分 · 报告'),
        ('03', '技术实现', '国产模型基座 + AI 龙虾智能体平台'),
        ('04', '技术创新点', '实证知识库 · 题型特化 · 案例检索'),
        ('05', '教育应用场景', '教学 · 学习 · 评价与科研'),
        ('06', '实施效果与展望', '性能实测 · 校准评级 · 未来规划'),
    ]
    xs = [0.55, 4.73, 8.91]
    for i, (num, t, d) in enumerate(items):
        x = xs[i % 3]
        y = 1.72 + (i // 3) * 2.25
        rect(s, x, y, 3.86, 1.95, CARD, LINE, radius=0.05)
        text(s, x + 0.28, y + 0.20, 1.4, 0.55, [{'runs': [(num, 26, True, GOLD)]}])
        text(s, x + 0.28, y + 0.80, 3.3, 0.5, [{'runs': [(t, 16, True, NAVY)]}])
        text(s, x + 0.28, y + 1.30, 3.3, 0.5, [{'runs': [(d, 9.5, False, GRAY)]}])
    footer(s, 2)


def s03_pain(prs):
    s = new_slide(prs)
    top = header(s, '01 背景与需求', '实证研究揭示：AI 法律工具存在系统性失效',
                 '西南民族大学法学院团队 2026年5月 · DeepSeek / 千问 Qwen · 14 案例 × 2 轮 × 4 维测评')
    metrics = [
        ('0%', '千问 · 虚构法条识别率', 'AI 接受虚构法律为真实（"人格权侵害惩治条例"），不标注废止/修订'),
        ('71%', 'DS · 量刑预测误差', '许某某案预测 3.5 年 → 实际 6 年；AI 系统性低估刑期'),
        ('2.96 / 5', 'DS · 引导性得分', '指出"问题在哪"，但不告诉"怎么解决"'),
        ('1.70 / 5', '千问 · 引导性得分', '四维测评中最弱维度，用户最容易踩坑'),
    ]
    x = 0.55
    for num, t, d in metrics:
        rect(s, x, 2.10, 2.98, 2.15, CARD, LINE, radius=0.05)
        text(s, x + 0.22, 2.28, 2.6, 0.65, [{'runs': [(num, 30, True, GOLD)]}])
        text(s, x + 0.22, 3.00, 2.6, 0.4, [{'runs': [(t, 12.5, True, NAVY)]}])
        text(s, x + 0.22, 3.42, 2.62, 0.8, [{'runs': [(d, 9.5, False, GRAY)], 'ls': 1.14}])
        x += 3.10
    band(s, 4.55, 1.55, '致命组合：准确性危机 × 深度缺失 × 引导性不足 × 前提验证盲区',
         '"浅度正确"：结论正确但缺乏深度法理分析；AI 天然相信用户前提；同一回答对法学生与非专业人士风险完全不同。'
         '24 种失效模式（F1-F24）被证实系统性存在 —— 需要"第三方审核"。')
    footer(s, 3)


def s04_versions(prs):
    s = new_slide(prs)
    top = header(s, '01 背景与需求', '版本迭代：21 天 · 8 个版本 · 全程可查',
                 'GitHub 开源仓库 phillnarsoeer/legal-guardian —— v1.0.0 → v4.3.0 八次里程碑标记，迭代过程完整可追溯')
    stages = [
        ('01 数据奠基', 'v1.0.0 → v2.0.0 ｜ 07-29 ~ 07-30',
         'AI 法律对话实证校正框架创立\n900 案例 / 1,800 QA / 900 RAG 块 / 71 案由'),
        ('02 规模跃升', 'v3.0.0 ｜ 07-31',
         '人民法院案例库 5,515 案例 / 535 案由\n27,575 问答对，RAG 案例检索上线'),
        ('03 能力成型', 'v4.0.0 ｜ 07-31',
         '18 种失效模式 + 8 大题型评分\n法考真题校准 + 训练语料（1,800 QA）'),
        ('04 体系扩展', 'v4.1.0 ｜ 08-03',
         'F1-F24 全体系 / 教学大纲合规审核\n8 项安全检查 / 竞赛场景匹配；基准 16 项'),
        ('05 质量攻坚', 'v4.2.0 → v4.2.1 ｜ 08-05 ~ 08-17',
         'JSON 模块级缓存 / 正则单遍扫描\n主观题归一化 / 废止法红线修复 / 死代码清理'),
        ('06 简洁精进', 'v4.3.0 ｜ 08-17（冒烟全绿 08-19）',
         '红线统一 / 全量校准 C→A / 包 14MB→0.16MB\n案例检索 + 三维规制 + 可视化报告面板'),
    ]
    for i, (num, t, d) in enumerate(stages):
        cx = 0.55 + (i % 3) * 4.18
        cy = 1.85 + (i // 3) * 2.12
        rect(s, cx, cy, 3.98, 1.95, CARD, LINE, radius=0.05)
        text(s, cx + 0.22, cy + 0.15, 3.5, 0.3, [{'runs': [(num, 10.5, True, GOLD)]}])
        text(s, cx + 0.22, cy + 0.48, 3.55, 0.4, [{'runs': [(t, 12.5, True, NAVY)]}])
        body = [{'runs': [(ln, 9.5, False, GRAY)], 'gap': 1, 'ls': 1.12} for ln in d.split('\n')]
        text(s, cx + 0.22, cy + 0.90, 3.55, 1.0, body)
    band(s, 6.15, 0.75, '迭代方法论：实证驱动 · 数据为王 · 质量优先',
         '语料 900 → 5,515 案例（6.1×）；失效模式 18 → 24；冒烟 39 → 41 项全绿 —— 每一次迭代都对齐实证基线，'
         '可验证、可追溯（GitHub tags 全程留痕）。')
    footer(s, 4)


def s05_users(prs):
    s = new_slide(prs)
    top = header(s, '01 背景与需求', '五类用户 · 三大校园场景', None)
    table(s, 0.55, 1.85, 7.75,
          ['用户类型', '核心需求', '风险'],
          [
              ['法学本科生 / 研究生', '深度法理分析、失效模式识别训练、AI 辅助作业', '中'],
              ['法学教师', '教学材料审核、AI 输出验证、作业批改辅助', '中低'],
              ['非专业社会人士', '通俗解释、醒目风险警示、律师咨询引导', '高'],
              ['AI 工具开发者', '三维规制符合性评估、失效模式诊断', '中'],
              ['教务管理者', '教学大纲合规审核、教学质量多维评价', '中'],
          ],
          col_w=[1.95, 4.65, 1.15], row_h=0.52)
    scenes = [
        ('智慧教学', '教学大纲合规审核 · 作业智能批改 · 智能考试管理'),
        ('智慧学习', 'AI 回答审核 · 提问优化 · 失效模式识别训练'),
        ('智慧评价', '教学质量评价 · 课程目标达成度 · 合规审核'),
    ]
    y = 1.85
    for t, d in scenes:
        cards_title = t
        card(s, 8.55, y, 4.23, 1.50, cards_title, d)
        y += 1.75
    band(s, 6.35, 0.62, '核心矛盾：AI 越"好用"，越需要第三方审核 —— 法律 AI 输出可信度成为教育场景的刚性需求', None, tsize=11.5)
    footer(s, 5)


def s05_overview(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '五大模块闭环：检测 → 纠正 → 安全 → 评分 → 报告', None)
    mods = [
        ('A', '审核纠正', '24 模式 F1-F24 检测\n8 项安全检查 C1-C8\n四维评分 + 基线对比'),
        ('B', '提问优化', '5 大提问模板\n竞赛场景智能匹配\n陷阱识别 + 问题重写'),
        ('C', '作业评估', '8 题型差异化评分\n红线规则 D1=0→归零\n错因归因 + 改进计划'),
        ('D', '三维评估', '技术规范 T1-T5\n教育引导 E1-E4\n法律保障 L1-L4'),
        ('E', '教学合规', '覆盖率核验 ≥80%\n缺失知识点清单\n大纲修订建议'),
    ]
    x = 0.55
    for tag, t, d in mods:
        rect(s, x, 1.85, 2.34, 2.45, CARD, LINE, radius=0.05)
        text(s, x + 0.2, 2.02, 1.9, 0.45, [{'runs': [(tag, 20, True, GOLD)]}])
        text(s, x + 0.2, 2.50, 2.0, 0.45, [{'runs': [(t, 15, True, NAVY)]}])
        body = [{'runs': [(ln, 9.5, False, GRAY)], 'gap': 1, 'ls': 1.12} for ln in d.split('\n')]
        text(s, x + 0.2, 3.05, 2.05, 1.5, body)
        x += 2.47
    # pipeline
    labels = ['检测', '纠正', '安全', '评分', '报告']
    x = 0.55
    for i, lb in enumerate(labels):
        chip(s, x, 5.05, 1.68, 0.66, lb, fill=NAVY, color=WHITE, size=13)
        if i < 4:
            text(s, x + 1.70, 5.17, 0.5, 0.4, [{'runs': [('▶', 14, False, GOLD)]}])
        x += 2.41
    band(s, 6.20, 0.68, '报告面板：一键生成"数字案卷"式全链路可视化（零依赖、离线可用），路演评审演示利器', None, tsize=11.5)
    footer(s, 5)


def s06_moduleA(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '模块A：AI 法律回答审核与纠正', None)
    groups = [
        ('F1-F10　通用模式', '法条幻视、罪名定性降维、量刑乐观偏差… 来自 14 案例实证测评'),
        ('F11-F18　题型特化模式', '选项混淆偏误、采分点遗漏、三段论结构缺失… 按 2022-2025 法考真题校准'),
        ('F19-F24　教信赛场景模式', '试题歧义偏差、评分尺度偏移、答案格式违规、跨题一致性破裂、采分点粒度失当、教学大纲合规偏离'),
    ]
    y = 1.85
    for t, d in groups:
        card(s, 0.55, y, 7.55, 1.42, t, d)
        y += 1.62
    steps = [
        ('failure_detector.py', '24 模式逐项检测，输出概率 / 严重度 / 检测依据'),
        ('correction_engine.py', '实证依据 + 修正方向 + 替代表述，命中即纠正'),
        ('safety_checker.py', 'C1-C8 安全检查，输出通过率 + 总体风险等级'),
    ]
    y = 1.85
    for t, d in steps:
        card(s, 8.35, y, 4.43, 1.32, t, d, tsize=12.5)
        y += 1.52
    card(s, 8.35, 6.42 - 1.32 + 0.5, 4.43, 0.95, '四维评分', '准确 / 时效 / 逻辑 / 引导，对照实证基线', tsize=12.5)
    band(s, 6.45, 0.55, '审核输出：单次推理 <2000 token，确定性规则引擎保证可复现、可审计', None, fill=LIGHT, tsize=10.5, bsize=9.5)
    footer(s, 7)


def s07_moduleB(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '模块B：提问优化与模板推荐', None)
    traps = [
        ('废止法律引用', '用户引用已废止《民法通则》，AI 未纠正 → 推荐"法条验证型"模板'),
        ('量刑预测', 'AI 误差可达 71%（实证）→ 推荐"案例对比型 / 多假设追问型"模板'),
        ('未验证前提', 'AI 天然相信用户输入 → 推荐"前提挑战型"模板前置校验'),
    ]
    x = 0.55
    for t, d in traps:
        card(s, x, 1.85, 3.98, 1.72, '陷阱：' + t, d, tsize=12.5)
        x += 4.13
    tmpls = [
        ('T1', '法条验证型', '现行有效性验证'),
        ('T2', '案例对比型', '判例对照分析'),
        ('T3', '多假设追问型', '多角度推演'),
        ('T4', '前提挑战型', '前提前置校验'),
        ('T5', '实操指引型', '可执行步骤'),
    ]
    x = 0.55
    for tid, tn, td in tmpls:
        rect(s, x, 3.95, 2.34, 1.30, LIGHT, None, radius=0.07)
        text(s, x + 0.18, 4.10, 2.0, 0.35, [{'runs': [(tid + ' ' + tn, 12, True, NAVY)]}])
        text(s, x + 0.18, 4.48, 2.0, 0.6, [{'runs': [(td, 9, False, GRAY)]}])
        x += 2.47
    band(s, 5.60, 1.35, '教信赛场景智能匹配（v4.1）',
         '教学大纲审核 → [T1+T4+T5]；考试设计 → [T3+T5]；评分一致性 → [T5+T4]　|　'
         '实证：R2 角色扮演测试中引导性提升 40%')
    footer(s, 8)


def s08_moduleC(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '模块C：法学作业评估与评分', None)
    qtypes = ['单项选择题', '多项选择题', '判断题', '名词解释', '简答题', '论述题', '法条分析题', '案例分析题']
    x = 0.55
    for q in qtypes:
        chip(s, x, 1.90, 1.40, 0.58, q, size=9.5, fill=NAVY, color=WHITE, bold=False)
        x += 1.56
    cards = [
        ('五维加权评分', 'D1 法律依据准确性 30% · D2 论证逻辑 25% · D3 法理深度 20% · D4 实务操作性 15% · D5 学术规范 10%'),
        ('红线规则', 'D1=0 → 总分归零；F24 教学合规偏离 → 大纲审核不通过；F1 命中 → D1 归零（统一口径）'),
        ('失效同步检测', '作业内嵌 24 模式检测：错因归因 + 个性化改进计划，作业即"诊断"'),
        ('校准保障', '2022-2025 法考真题校准；评分可复现（同一输入偏差 ≤0.2 分）'),
    ]
    x = 0.55
    for t, d in cards:
        card(s, x, 2.85, 2.98, 2.45, t, d, tsize=12.5, bsize=9.5)
        x += 3.10
    band(s, 5.70, 1.15, '使用方式：作业.docx 一键出分',
         '对话：粘贴作业 → 8 题型自动识别 + 差异化评分 + 红线判定 + 改进计划；支持批量答案键验证（answer_key_evaluator）')
    footer(s, 9)


def s09_moduleDE(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '模块D：三维规制评估 + 模块E：教学大纲合规审核', None)
    regs = [
        ('技术规范 T1-T5', '模型能力边界、免责声明、可追溯性等合规要求'),
        ('教育引导 E1-E4', '学习导向、风险警示设计、教学伦理引导'),
        ('法律保障 L1-L4', '数据安全、隐私保护、法律责任边界'),
    ]
    y = 1.85
    for t, d in regs:
        card(s, 0.55, y, 7.55, 1.28, t, d, tsize=12.5)
        y += 1.48
    card(s, 8.35, 1.85, 4.43, 3.72, '模块E：教学大纲 AI 合规审核',
         None, tsize=13,
         body_paras=[
             {'runs': [('核验：教育部法学类国家标准 · 八大领域 · 18 个必授知识点', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
             {'runs': [('阈值：核心知识点覆盖率 ≥80%（F24）', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
             {'runs': [('输出：覆盖率报告 + 缺失知识点清单 + 大纲修订建议', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
         ])
    band(s, 5.85, 1.05, '谁在用？',
         '教务管理者 / 教师：上传大纲 → F24 检测 → 合规报告；AI 工具开发者：评估工具合规性 → T/E/L 雷达图 + 改进路线图')
    footer(s, 10)


def s10_arch(prs):
    s = new_slide(prs)
    top = header(s, '02 方案设计', '四层模块化架构 · 数据与逻辑完全解耦', None)
    layers = [
        ('输出模板层', 'templates/', '2 个模板：渲染最终报告与"数字案卷"式可视化面板'),
        ('逻辑编排层', 'SKILL.md', '技能意图路由、模块调度、场景门控（题型特化/教信赛场景）'),
        ('脚本引擎层', 'scripts/', '15 个 Python 脚本：检测 / 纠正 / 安全 / 评分 / 检索 / 报告'),
        ('知识库层', 'reference/', '9 个 JSON 知识库：规则、基线、课程要求、案例库'),
    ]
    y = 1.85
    for lname, lp, d in layers:
        rect(s, 0.55, y, 7.55, 0.92, CARD, LINE, radius=0.06)
        text(s, 0.80, y + 0.12, 2.1, 0.4, [{'runs': [(lname, 13.5, True, NAVY)]}])
        text(s, 0.80, y + 0.48, 2.6, 0.34, [{'runs': [(lp, 10, False, GOLD)]}])
        text(s, 2.95, y + 0.26, 4.95, 0.5, [{'runs': [(d, 9.5, False, GRAY)], 'ls': 1.1}])
        y += 1.06
    flows = ['用户输入', '模块入口', '知识库加载', '脚本执行', 'JSON 结果', '模板渲染 → 报告']
    rect(s, 8.35, 1.85, 4.43, 4.15, LIGHT, None, radius=0.05)
    text(s, 8.60, 2.02, 4.0, 0.35, [{'runs': [('数据流（一次完整审核）', 12.5, True, NAVY)]}])
    y = 2.48
    for i, f in enumerate(flows):
        chip(s, 8.70, y, 3.20, 0.40, f, fill=CARD, color=TXT, size=9.5, bold=False, line=LINE)
        y += 0.49
    text(s, 8.60, 5.50, 4.0, 0.5,
         [{'runs': [('层间以 JSON 标准接口通信；知识库独立于脚本，可直接替换、热更新', 9, False, GRAY)], 'ls': 1.12}])
    band(s, 6.35, 0.55, '架构价值：新增失效模式只需在知识库注册（candidate_patterns），无需改动引擎代码', None, tsize=10.5)
    footer(s, 11)


def s11_tech(prs):
    s = new_slide(prs)
    top = header(s, '03 技术实现', '国产模型基座 + AI 龙虾智能体平台', None)
    table(s, 0.55, 1.90, 8.05,
          ['模型（国产）', '在 Skill 中的角色'],
          [
              ['Qwen3-Next-80B（推理）', '失效检测 / 纠正生成 / 评分 / 大纲审核'],
              ['Qwen3-Embedding-8B（嵌入）', '语义检索与案例召回'],
              ['Qwen3-Reranker-8B（重排）', '检索候选精排'],
              ['Qwen3-VL-32B（多模态）', '试卷 / 课件图像理解'],
              ['Qwen3-ASR（语音识别）', '课堂问答转写'],
              ['Qwen3-TTS（语音合成）', '教学反馈播报'],
          ],
          col_w=[3.35, 4.70], row_h=0.52)
    card(s, 8.85, 1.90, 3.93, 1.75, 'AI 龙虾智能体平台',
         'Skill 上传 → 自动激活 → 技能编排；平台账号 + 智算资源在线分配。')
    card(s, 8.85, 3.85, 3.93, 1.75, '国产算力环境',
         '基于国产芯片的算力环境，保障每支队伍模型调用与评测资源。')
    band(s, 6.30, 0.68, '轻量 & 可控',
         '单次审核推理开销 <2000 token；知识库 JSON 本地维护；确定性规则引擎保证结果可复现、可审计。')
    footer(s, 12)


def s12_innov1(prs):
    s = new_slide(prs)
    top = header(s, '04 技术创新点', '创新点一：实证驱动的失效模式知识库', None)
    band(s, 1.90, 1.45, '实证基线 = 不可修改的校准锚点',
         '14 案例 × 2 轮 × 4 维实测数据（DeepSeek 3.84 vs 千问 3.06）；所有纠正建议必须引用实证证据 —— '
         '拒绝"模型直觉"，只相信"测出来的结论"。',
         tsize=13)
    table(s, 0.55, 3.75, 7.55,
          ['环节', '内容', '实证意义'],
          [
              ['检测', '24 模式知识库（severity / frequency / evidence / 关键词）', '每条模式均有实证证据字段'],
              ['纠正', '实证依据 + 修正方向 + 替代表述', '纠正建议可溯源、可审计'],
              ['评分', '四维评分对照 DS / 千问基线', '评分可校准（竞赛铁律）'],
          ],
          col_w=[1.2, 3.75, 2.6], row_h=0.52)
    card(s, 8.35, 3.75, 4.43, 1.75, '校准成果',
         '虚构法律识别：千问基线 0% → LG 目标 100%（≥95%）；综合校准评级 C → A，评分可复现偏差 ≤0.2 分。')
    band(s, 5.85, 0.95, '链路要求：检测有证据、纠正有依据、评分有对照',
         '全流程可溯源、可审计 —— 实证基线既是"校准锚点"，也是评委可核验的"证据链"。')
    footer(s, 13)


def s13_innov2(prs):
    s = new_slide(prs)
    top = header(s, '04 技术创新点', '创新点二：题型特化 + 场景门控', None)
    card(s, 0.55, 1.85, 5.95, 2.30, '题型特化模式 F11-F18',
         '每个题型绑定专属失效模式：单项选择 → 选项混淆偏误；简答 → 采分点遗漏；'
         '案例分析 → 三段论结构缺失… 按法考真题（2022-2025）逐题型校准。', tsize=13)
    card(s, 0.55, 4.35, 5.95, 2.30, '场景门控',
         '教信赛场景模式 F19-F24 仅在对应场景触发（试题歧义 / 评分偏移 / 格式违规 / 跨题矛盾 / 粒度失当 / 合规偏离），'
         '干净样本误报 7 → 0。', tsize=13)
    metrics = [('7 → 0', '干净样本误报'), ('100%', '题型识别（16/16）'), ('C → A', '综合校准评级')]
    y = 1.85
    for num, t in metrics:
        rect(s, 8.35, y, 4.43, 1.45, CARD, LINE, radius=0.06)
        text(s, 8.55, y + 0.18, 4.0, 0.7, [{'runs': [(num, 26, True, GOLD)]}])
        text(s, 8.55, y + 0.95, 4.0, 0.4, [{'runs': [(t, 11.5, True, NAVY)]}])
        y += 1.60
    band(s, 6.30, 0.68, '红线统一（v4.3.0）', 'F1 命中即 D1 归零；题型识别 5 处规则修复；确定性与可复现性优先。', tsize=10.5)
    footer(s, 14)


def s14_innov3(prs):
    s = new_slide(prs)
    top = header(s, '04 技术创新点', '创新点三：案例库确定性检索 + 三维规制评估', None)
    card(s, 0.55, 1.85, 5.95, 2.55, '5,515 案例库 · 确定性检索',
         None, tsize=13,
         body_paras=[
             {'runs': [('来源：人民法院案例库真实判例', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
             {'runs': [('机制：确定性关键词检索（rag_retriever），命中即返回', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
             {'runs': [('价值：零幻觉、可复现、本地离线运行；每条纠正建议可挂接真实判例', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
         ])
    card(s, 0.55, 4.60, 5.95, 2.05, '三维规制评估器',
         None, tsize=13,
         body_paras=[
             {'runs': [('技术 T1-T5 / 教育 E1-E4 / 法律 L1-L4 逐项状态评估', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
             {'runs': [('输出：逐项状态 + 雷达图 + 改进路线图；适用 AI 法律工具合规自评与整改', 9.5, False, GRAY)], 'gap': 3, 'ls': 1.12},
         ])
    card(s, 8.35, 1.85, 4.43, 4.80, '报告面板（"数字案卷"式可视化）',
         None, tsize=13,
         body_paras=[
             {'runs': [('风险印章 · 失效模式 · 纠正建议 · 安全检查', 9.5, False, GRAY)], 'gap': 4, 'ls': 1.12},
             {'runs': [('四维评分 · 作业评估 · 提问优化', 9.5, False, GRAY)], 'gap': 4, 'ls': 1.12},
             {'runs': [('案例检索 · 三维规制全景视图', 9.5, False, GRAY)], 'gap': 4, 'ls': 1.12},
             {'runs': [('零依赖、离线可用；支持打印 / 导出 PDF', 9.5, False, GRAY)], 'gap': 4, 'ls': 1.12},
         ])
    footer(s, 15)


def s15_innov4(prs):
    s = new_slide(prs)
    top = header(s, '04 技术创新点', '知识库创新：数据-逻辑分离的 9 大 JSON 知识库', None)
    table(s, 0.55, 1.85, 8.35,
          ['知识库', '内容', '关键要点'],
          [
              ['failure_patterns.json', '24 大失效模式', '严重度 / 频次 / 现象 / 实证证据 / 纠正策略'],
              ['curriculum_requirements.json', '教育部课程要求', '八大领域 · 18 必授知识点'],
              ['test_baseline.json', '实证基线', 'DS 3.84 vs 千问 3.06'],
              ['correction_templates.json', '5 大提问模板', '含场景匹配规则'],
              ['safety_checklist.json', '8 项安全检查', 'C1-C8'],
              ['three_d_regulation.json', '三维规制路径', 'T1-T5 / E1-E4 / L1-L4'],
              ['question_type_rubrics.json', '8 题型评分标准', '差异化评分规则'],
              ['assignment_rubric.json', '五维评分标准', 'D1 法律依据 30%'],
              ['legal_knowledge_base.json', '法条 + 废止预警', '可直接编辑更新'],
          ],
          col_w=[2.55, 2.30, 3.50], row_h=0.40)
    band(s, 5.85, 1.05, '可插拔扩展机制',
         'candidate_patterns 字段一键注册新模式；知识库与脚本零耦合 —— 更新知识、增长能力无需修改引擎代码。')
    footer(s, 16)


def s16_scene_teach(prs):
    s = new_slide(prs)
    top = header(s, '05 教育应用场景', '场景一：智慧教学', None)
    scenes = [
        ('教学大纲 AI 合规审核', '上传大纲 → F24 检测 → 覆盖率（≥80%）+ 缺失知识点清单 + 修订建议',
         '输出：覆盖率报告 + 缺失清单 + 修订建议'),
        ('多模态作业智能批改', '8 题型评分 + 红线判定 + 错因归因 + 改进计划；法条准确性 30% 权重把控质量',
         '支持 .docx 一键导入与批量答案键验证'),
        ('智能考试全流程管理', '试题歧义（F19）/ 评分偏移（F20）/ 跨题一致（F22）检测 + 答案键验证',
         '输出：试题质量报告 + 评分一致性分析'),
    ]
    x = 0.55
    for t, d, e in scenes:
        card(s, x, 1.85, 3.98, 3.10, t, None, tsize=13, bsize=10,
             body_paras=[
                 {'runs': [(d, 10, False, TXT)], 'gap': 3, 'ls': 1.14},
                 {'runs': [(e, 9.5, False, GRAY)], 'gap': 0, 'ls': 1.12},
             ])
        x += 4.13
    band(s, 5.35, 1.55, '教师价值：从"经验判断"到"数据校准"',
         '备课减负：大纲合规一键核查；评分一致：红线规则统一尺度；标准可查：教育部必授知识点逐条对照 —— '
         '让 AI 批改、审核结果为教师所用，而非替代教师。')
    footer(s, 17)


def s17_scene_learn(prs):
    s = new_slide(prs)
    top = header(s, '05 教育应用场景', '场景二：智慧学习', None)
    scenes = [
        ('全天候 AI 学伴', '学生提问前先"体检"：审核 AI 回答（24 模式）+ 安全提示 + 引导纠正，24 小时可用',
         '覆盖法学生与非专业用户差异化风险响应'),
        ('提问优化训练', '5 大模板教学生"正确提问"，实证引导性提升 40%；失效模式识别训练融入日常练习',
         '24 种失效模式案例化，可嵌入法学课堂实验'),
        ('非专业用户防护', '醒目风险警示 + "不替代律师"角色边界 + 律师咨询引导 —— 差异化风险响应',
         '输出：安全等级 + 人工核实标注项（C6）'),
    ]
    x = 0.55
    for t, d, e in scenes:
        card(s, x, 1.85, 3.98, 3.10, t, None, tsize=13, bsize=10,
             body_paras=[
                 {'runs': [(d, 10, False, TXT)], 'gap': 3, 'ls': 1.14},
                 {'runs': [(e, 9.5, False, GRAY)], 'gap': 0, 'ls': 1.12},
             ])
        x += 4.13
    band(s, 5.35, 1.55, '学习价值：从"被动接受"到"主动验证"',
         '训练法律 AI 时代的核心素养：识别失效模式、验证法条现行性、交叉校验观点 —— 把风险教育转化为能力培养。')
    footer(s, 18)


def s18_scene_eval(prs):
    s = new_slide(prs)
    top = header(s, '05 教育应用场景', '场景三：智慧评价与智慧科研', None)
    scenes = [
        ('教学质量多维评价', '作业 + 考试 + 大纲多源数据；四维评分对照实证基线，评价有标尺',
         '为课程目标达成度与持续改进提供数据依据'),
        ('教学合规与标准审核', '课程大纲 / 课程标准 AI 合规审核（F24），课程目标达成度评估支撑',
         '对接教育部法学类国家标准（18 必授知识点）'),
        ('法律 AI 合规预审', '三维规制评估：AI 工具 / 系统合规性自查与伦理预审辅助',
         '输出：T/E/L 逐项状态 + 整改路线图'),
    ]
    x = 0.55
    for t, d, e in scenes:
        card(s, x, 1.85, 3.98, 3.10, t, None, tsize=13, bsize=10,
             body_paras=[
                 {'runs': [(d, 10, False, TXT)], 'gap': 3, 'ls': 1.14},
                 {'runs': [(e, 9.5, False, GRAY)], 'gap': 0, 'ls': 1.12},
             ])
        x += 4.13
    band(s, 5.35, 1.55, '评价价值：评价有标尺、教学有依据、合规有记录',
         '对接教信赛三类方向：智慧教学、智慧学习、智慧评价 —— 以同一套实证引擎贯通"教 - 学 - 评 - 规"。')
    footer(s, 19)


def s19_safety(prs):
    s = new_slide(prs)
    top = header(s, '03 技术实现', '安全与合规：8 项检查 + 红线规则 + 本地化运行', None)
    checks = [
        ('C1', '法条来源核对'), ('C2', '罪名反向思考'), ('C3', '量刑风险边界'), ('C4', '多平台交叉验证'),
        ('C5', '遗漏争点排查'), ('C6', '人工核实标注'), ('C7', '不替代律师'), ('C8', '计算一致性'),
    ]
    x0, y0 = 0.55, 1.90
    for i, (cid, cname) in enumerate(checks):
        cx = x0 + (i % 2) * 4.13
        cy = y0 + (i // 2) * 0.82
        rect(s, cx, cy, 3.98, 0.66, CARD, LINE, radius=0.10)
        text(s, cx + 0.18, cy + 0.15, 2.4, 0.4,
             [{'runs': [('', 10, True, GOLD)] + [(cid, 10, True, GOLD), ('  ' + cname, 11, True, NAVY)]}])
    card(s, 8.85, 1.90, 3.93, 2.90, '红线规则（统一口径）',
         None, tsize=13,
         body_paras=[
             {'runs': [('D1=0 → 作业总分归零', 10, False, TXT)], 'gap': 4, 'ls': 1.14},
             {'runs': [('F24 教学合规偏离 → 大纲审核不通过', 10, False, TXT)], 'gap': 4, 'ls': 1.14},
             {'runs': [('F1 虚构法条命中 → D1 归零', 10, False, TXT)], 'gap': 4, 'ls': 1.14},
         ])
    band(s, 6.30, 0.68, '角色边界（合规声明）',
         '本 Skill 不替代律师 / 教师，不做终局性法律判断；所有输出标注需人工核实项（C6）。', tsize=10.5)
    footer(s, 20)


def s20_effect1(prs):
    s = new_slide(prs)
    top = header(s, '06 实施效果与展望', '实施效果：性能实测与可靠性指标',
                 '数据来源：2026-08-05 基准测试与全量校准（Qwen3 基座）')
    table(s, 0.55, 2.15, 7.05,
          ['操作', '目标', '实测'],
          [
              ['失效模式检测', '≤5 秒', '≤3 秒'],
              ['纠正建议生成', '≤10 秒', '≤8 秒'],
              ['安全检查', '≤5 秒', '≤2 秒'],
              ['作业评估', '≤60 秒', '≤45 秒'],
              ['全流程审核链', '≤45 秒', '≤30 秒'],
              ['教学合规审核', '≤30 秒', '≤20 秒'],
          ],
          col_w=[2.95, 1.75, 2.35], row_h=0.46)
    cards = [
        ('可靠性', '题型识别 100%（16/16）· F1-F24 全覆盖 · 命中即纠正 100% · 评分偏差 ≤0.2 分'),
        ('工程质量', '全量冒烟测试 41 项 0 FAIL（2026-08-19）；综合校准评级 A（全量 26 项）；安装包 14MB → 0.16MB'),
    ]
    y = 2.15
    for t, d in cards:
        card(s, 8.15, y, 4.63, 1.72, t, d, tsize=13)
        y += 1.92
    band(s, 6.05, 0.90, '可复现性声明',
         '确定性规则引擎 + 本地知识库：同一输入、同一输出 —— 满足大赛"评分可复现、校准可对照"要求。')
    footer(s, 21)


def s21_effect2(prs):
    s = new_slide(prs)
    top = header(s, '06 实施效果与展望', '实施效果：四维实证对比 —— 从"能用"到"可信"', None)
    table(s, 0.55, 2.05, 8.35,
          ['维度', 'DS 基线', '千问基线', 'LG 目标', '提升'],
          [
              ['准确性', '4.03', '3.49', '≥4.5', '+0.47'],
              ['时效性', '4.69', '4.13', '≥4.5', '−0.19（保守）'],
              ['逻辑性', '3.66', '2.93', '≥4.0', '+0.34'],
              ['引导性', '2.96', '1.70', '≥3.0', '+0.04'],
              ['综合', '3.84', '3.06', '≥4.0', '+0.16'],
          ],
          col_w=[1.55, 1.55, 1.55, 1.55, 2.15], row_h=0.50)
    vals = [
        ('正确性', '虚构法条识别 0% → ≥95%（目标 100%）'),
        ('可复现性', '确定性规则，命题级可复现（偏差 ≤0.2 分）'),
        ('可用性', '报告面板零依赖即开即用，教师 / 教务直接上手'),
    ]
    y = 2.05
    for t, d in vals:
        card(s, 9.15, y, 3.63, 1.18, t, d, tsize=12.5, bsize=9.5)
        y += 1.36
    band(s, 5.95, 1.00, '价值总结：把"AI 法律输出风险"转化为"可量化、可干预、可改进"的教育质量资产',
         '五模块闭环覆盖 AI 法律工具全生命周期：事前（提问优化）· 事中（审核纠正）· 事后（作业评估 / 合规审核）。')
    footer(s, 22)


def s22_future(prs):
    s = new_slide(prs, NAVY)
    text(s, 0.9, 0.85, 10, 0.35, [{'runs': [('06 实施效果与展望', 11, True, GOLD)]}])
    text(s, 0.9, 1.25, 11.5, 0.7, [{'runs': [('未来展望', 30, True, WHITE)]}])
    shape(s, MSO_SHAPE.RECTANGLE, 0.95, 2.05, 1.6, 0.045, fill=GOLD)
    items = ['知识图谱自适应学习与推荐', '多模态作业批改（Qwen3-VL）', '学情画像与教学预警', '数字人微课与语音互动']
    x = 0.9
    for it in items:
        chip(s, x, 2.45, 2.75, 0.66, it, fill='25406F', color='E8ECF4', size=10.5, bold=False)
        x += 2.95
    text(s, 0.9, 3.45, 11.5, 1.0,
         [{'runs': [('依托 Qwen3 全系模型能力持续进化：Qwen3-VL 理解试卷与课件图像、Qwen3-ASR/TTS 支撑语音互动学伴、'
                     'Qwen3-Embedding + Reranker 扩展知识图谱自适应路径 —— 从"审核工具"成长为"教 · 学 · 评 · 规"一体的'
                     '智慧教育基础设施。', 11, False, 'C7D1E2')], 'ls': 1.3}])
    shape(s, MSO_SHAPE.RECTANGLE, 0, 5.05, 13.333, 0.045, fill=GOLD)
    text(s, 0.9, 5.40, 11.5, 0.9, [{'runs': [('谢谢聆听 · 恳请各位评委专家指正', 28, True, WHITE)]}])
    text(s, 0.9, 6.30, 11.5, 0.4,
         [{'runs': [('西南民族大学法学院参赛团队　|　LegalGuardian v4.3.0　|　AI 龙虾智能体平台',
                     12, False, 'A7B4C8')]}])
    footer(s, 23)


def main():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    for fn in [s01_cover, s02_toc, s03_pain, s04_versions, s05_users, s05_overview, s06_moduleA,
               s07_moduleB, s08_moduleC, s09_moduleDE, s10_arch, s11_tech, s12_innov1,
               s13_innov2, s14_innov3, s15_innov4, s16_scene_teach, s17_scene_learn,
               s18_scene_eval, s19_safety, s20_effect1, s21_effect2, s22_future]:
        fn(prs)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '06_作品演示PPT.pptx')
    prs.save(out)
    print('✓ 生成', out, '共', len(prs.slides.__iter__.__self__._sldIdLst), '页')


if __name__ == '__main__':
    import os
    main()
