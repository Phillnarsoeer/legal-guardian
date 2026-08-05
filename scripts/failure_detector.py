#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Failure Detector - 10 failure pattern detection engine.
Based on empirical research: 14 cases x 2 rounds x 4 dimensions.
Usage: python failure_detector.py <file> | --text "text" | --stdin
"""

import sys, json, re, os

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


_FAILURE_PATTERNS_CACHE = None


def load_failure_patterns():
    global _FAILURE_PATTERNS_CACHE
    if _FAILURE_PATTERNS_CACHE is not None:
        return _FAILURE_PATTERNS_CACHE
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, '..', 'reference', 'failure_patterns.json')
    with open(path, 'r', encoding='utf-8') as f:
        _FAILURE_PATTERNS_CACHE = json.load(f)
    return _FAILURE_PATTERNS_CACHE


def extract_context(text, keyword, ctx=80):
    idx = text.find(keyword)
    if idx == -1:
        return 'Contains: ' + keyword
    s = max(0, idx - ctx // 2)
    e = min(len(text), idx + len(keyword) + ctx // 2)
    c = text[s:e].strip()
    return ('...' if s > 0 else '') + c + ('...' if e < len(text) else '')


def detect_f1(text, pat):
    kw = pat['detection_keywords']
    suspects = kw['suspect_laws']
    indicators = kw['suspect_indicators']
    dets = []
    for law in suspects:
        if law in text:
            dets.append({'type': 'repealed_law', 'law_name': law,
                         'evidence_text': extract_context(text, law),
                         'recommendation': law + ' was replaced by Civil Code on 2021-01-01'})
    for ind in indicators:
        if ind in text:
            dets.append({'type': 'possible_fictional', 'law_name': ind,
                         'evidence_text': extract_context(text, ind),
                         'recommendation': 'Verify if ' + ind + ' actually exists'})
    cp = re.compile(r'(?:According to|under|pursuant to|per)\s*[《]([^》]+)[》]')
    cites = cp.findall(text)
    for c in cites:
        if c not in suspects and c not in indicators:
            has_v = any(v in text for v in kw['validity_signals'])
            if not has_v and c not in [d.get('law_name', '') for d in dets]:
                dets.append({'type': 'missing_validity', 'law_name': c,
                             'recommendation': 'Mark effective date when citing ' + c})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.3, 1.0),
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f2(text, pat):
    kw = pat['detection_keywords']
    charges = kw['charge_indicators']
    found = [c for c in charges if c in text]
    has_alt = any(p in text for p in ['alternative', 'also', 'might constitute', 'prosecution perspective', 'defense perspective'])
    dets = []
    if len(found) == 1 and not has_alt:
        rel = {'intentional injury': 'attempted murder', 'affray': 'intentional injury',
               'snatch': 'robbery', 'theft': 'robbery'}
        sc = found[0]
        if sc in rel:
            dets.append({'type': 'single_charge', 'found_charge': sc,
                         'missing_alternative': rel[sc],
                         'recommendation': 'Also analyze ' + rel[sc] + ' from prosecution perspective'})
    return {'fired': len(dets) > 0, 'probability': min(len(found) * 0.15 + len(dets) * 0.3, 1.0) if found else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f3(text, pat):
    kw = pat['detection_keywords']
    ss = kw['sentencing_signals']
    sent_matches = [s for s in ss if s in text]
    dets = []
    if sent_matches:
        has_conf = any(p in text for p in ['for reference only', 'uncertainty', 'actual sentence may', 'error margin', 'confidence'])
        if not has_conf:
            dets.append({'type': 'no_confidence', 'recommendation': 'Disclose uncertainty; empirical error can reach 71% (Xu case: predicted 3.5y vs actual 6y)'})
    return {'fired': len(dets) > 0, 'probability': min(len(sent_matches) * 0.25, 1.0),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f4(text, pat):
    kw = pat['detection_keywords']
    shallow = kw['shallow_signals']
    depth_inds = ['alternative theory', 'exception', 'legal dispute', 'academic view', 'different opinion',
                  'might also be', 'comparative law', 'extraterritorial']
    has_shallow = any(s in text for s in shallow)
    has_depth = any(d in text for d in depth_inds)
    dets = []
    if has_shallow and not has_depth and len(text) > 500:
        dets.append({'type': 'shallow_conclusion', 'recommendation': 'Add depth: alternative theories, exceptions, academic disputes'})
    return {'fired': len(dets) > 0, 'probability': 0.5 if dets else 0.2,
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f5(text, pat):
    kw = pat['detection_keywords']
    traps = kw['user_input_traps']
    if isinstance(traps, dict):
        trap_items = []
        for g in traps.values():
            trap_items.extend(g if isinstance(g, list) else [str(g)])
    else:
        trap_items = traps if isinstance(traps, list) else []
    dets = []
    has_corr = any(p in text for p in ['repealed', 'replaced', 'does not exist', 'not found', 'please verify', 'needs verification'])
    for trap in trap_items:
        if trap in text and not has_corr:
            dets.append({'type': 'trap_accepted', 'evidence_text': 'AI accepted potentially problematic premise: ' + trap,
                         'recommendation': 'First verify if ' + trap + ' is real and valid'})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.4, 1.0),
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f6(text, pat):
    kw = pat['detection_keywords']
    missing = kw['missing_guidance_elements']
    elem_pats = {
        'evidence list': ['evidence', 'collect', 'proof', 'evidence list', 'prepare', 'notarize'],
        'procedure steps': ['step', 'procedure', 'process', 'first', 'then', 'action'],
        'timeline': ['limitation', 'deadline', 'timeline', 'days', 'within', 'from the date'],
        'risk warning': ['risk', 'caution', 'warning', 'disclaimer', 'does not constitute', 'for reference only'],
        'alternatives': ['negotiate', 'mediation', 'arbitration', 'alternative', 'settlement']
    }
    found = [e for e, pats in elem_pats.items() if any(p in text for p in pats)]
    dets = []
    if len(found) < 3 and len(text) > 300:
        dets.append({'type': 'insufficient_guidance', 'found_elements': found,
                     'recommendation': 'Add: evidence checklist + procedure steps + timeline + risk warnings + alternatives. Baseline: DS guidance avg 2.96/5, Qwen 1.70/5. T5 template recommended.'})
    return {'fired': len(dets) > 0, 'probability': 1 - (len(found) / 5),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f7(text, pat):
    kw = pat['detection_keywords']
    calc_sigs = kw['calculation_signals']
    has_calc = any(s in text for s in calc_sigs)
    dets = []
    if has_calc:
        pcts = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        lprs = re.findall(r'LPR[^\d]*(\d+(?:\.\d+)?)', text)
        if len(pcts) >= 2:
            pv = [float(p) for p in pcts]
            if max(pv) - min(pv) > 5:
                dets.append({'type': 'percentage_discrepancy', 'recommendation': 'Verify calculation logic and consistency'})
        if len(lprs) >= 2:
            lv = [float(l) for l in lprs]
            if max(lv) - min(lv) > 2:
                dets.append({'type': 'lpr_benchmark_inconsistency',
                             'recommendation': 'LPR benchmark choice (contract date vs filing date) can cause 30%+ difference. DS uses filing date (~13%), Qwen uses contract date (~17%).'})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.35, 1.0),
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f8(text, pat):
    kw = pat['detection_keywords']
    simpl = kw['causal_simplification_signals']
    missing_f = kw['missing_factors']
    has_simpl = any(s in text for s in simpl)
    has_complex = any(f in text for f in missing_f)
    dets = []
    if has_simpl and not has_complex:
        dets.append({'type': 'causal_simplification', 'recommendation': 'Consider multi-cause analysis, omission liability, prior-act obligations'})
    return {'fired': len(dets) > 0, 'probability': 0.4 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f9(text, pat):
    kw = pat['detection_keywords']
    missing_intl = kw['missing_international']
    hr_kw = ['personal rights', 'personality rights', 'women', 'children', 'domestic violence', 'abuse', 'fundamental rights', 'human rights']
    has_hr = any(h in text for h in hr_kw)
    has_intl = any(i in text for i in missing_intl)
    dets = []
    if has_hr and not has_intl:
        dets.append({'type': 'intl_law_gap', 'recommendation': 'Consider referencing relevant international conventions (e.g. CEDAW, ICCPR) for fundamental rights cases'})
    return {'fired': len(dets) > 0, 'probability': 0.5 if dets else 0.1,
            'severity': 'medium', 'detections': dets if dets else None}


def detect_f10(text, pat):
    kw = pat['detection_keywords']
    user_inds = kw['user_type_indicators']
    has_user_ctx = any(ind in text for ind in user_inds)
    has_diff = any(p in text for p in ['as a law student', 'as a lawyer', 'for non-professionals', 'if you are', 'for general readers'])
    dets = []
    if not has_user_ctx and not has_diff and len(text) > 300:
        dets.append({'type': 'no_user_differentiation', 'recommendation': 'Differentiate output by user background: law students get deep analysis; non-professionals get plain language + prominent risk warnings + lawyer referral'})
    return {'fired': len(dets) > 0, 'probability': 0.7 if dets else 0.2,
            'severity': 'critical', 'detections': dets if dets else None}


# =============================================================================
# v4.0.0: 题型特化失效模式检测 (F11-F18)
# =============================================================================

def detect_f11(text, pat):
    """F11: 选项混淆偏误 — 选择题中将相似法律概念混淆"""
    default_pairs = [
        (['可撤销', '无效'], '可撤销≠无效。可撤销行为在被撤销前有效；无效行为自始无效。'),
        (['效力待定', '无效'], '效力待定≠无效。效力待定经追认可有效；无效不可追认。'),
        (['解除', '撤销'], '解除≠撤销。解除面向将来；撤销溯及既往。'),
        (['终止', '中止'], '终止=永久结束；中止=暂时停止。'),
        (['应当', '可以'], '应当=强制性义务；可以=授权性权利。'),
        (['从轻', '减轻'], '从轻=在法定刑幅度内偏轻；减轻=突破法定刑下限。'),
    ]
    kw = pat.get('detection_keywords', {})
    raw_pairs = kw.get('confusion_pairs', default_pairs)
    # patterns_v2 中 confusion_pairs 为 "可撤销.*无效" 正则字符串格式，统一转成 [(term1, term2), explanation]
    confusion_pairs = []
    if isinstance(raw_pairs, list):
        for item in raw_pairs:
            if isinstance(item, str):
                terms = re.split(r'\s*[.．]\*\s*|\s*[、,，]\s*', item)
                if len(terms) >= 2:
                    confusion_pairs.append(([terms[0].strip(), terms[1].strip()], ''))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                if isinstance(item[0], (list, tuple)):
                    confusion_pairs.append((list(item[0]), item[1] if len(item) > 1 else ''))
                elif all(isinstance(x, str) for x in item):
                    confusion_pairs.append(([item[0], item[1]], ''))
    if not confusion_pairs:
        confusion_pairs = default_pairs
    dets = []
    for (term1, term2), explanation in confusion_pairs:
        # 检测两个混淆词同时出现且未明确区分
        if term1 in text and term2 in text:
            # 检查是否有区分性表述
            has_clarification = any(w in text for w in ['不同于', '区别于', '不等于', '不是', '≠', '区分'])
            if not has_clarification:
                dets.append({
                    'type': 'concept_confusion',
                    'term1': term1,
                    'term2': term2,
                    'recommendation': explanation or f'注意区分「{term1}」与「{term2}」的实质差异。'
                })
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.35, 1.0),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f12(text, pat):
    """F12: 采分点遗漏 — 简答题遗漏关键采分点"""
    # 此检测需要答案键配合，独立检测只能标记潜在遗漏
    kw = pat.get('detection_keywords', {})
    omission_signals = kw.get('omission_signals', ['此外', '另外', '还有', '不仅如此', '值得注意的是'])
    has_omission_marker = any(s in text for s in omission_signals)
    dets = []
    if has_omission_marker:
        dets.append({
            'type': 'potential_omission',
            'recommendation': '检测到补充性过渡词，可能存在采分点遗漏。建议与答案键的scoring_points进行覆盖对比。'
        })
    # 检查文本长度是否过短（可能遗漏）
    if len(text) < 100:
        dets.append({
            'type': 'answer_too_short',
            'recommendation': '简答题答案过短(<100字)，大概率遗漏采分点。建议对照答案键逐点覆盖。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.6 if len(dets) >= 2 else 0.3 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f13(text, pat):
    """F13: 定义要素缺失 — 名词解释缺少核心要素"""
    kw = pat.get('detection_keywords', {})
    required_elements = kw.get('required_elements',
                               ['主体', '客体', '内容', '目的', '构成要件', '法律特征', '适用范围',
                                '是指', '指的是', '即', '又称'])
    found = []
    for e in required_elements:
        if len(e) <= 1:
            # 单字要素需独立成词，避免 即使/立即 等误报
            if re.search(r'(?<![一-鿿])' + re.escape(e) + r'(?![一-鿿])', text):
                found.append(e)
        elif e in text:
            found.append(e)
    dets = []
    if len(text) < 30 and len(text) > 0:
        dets.append({
            'type': 'definition_too_short',
            'recommendation': '定义过于简短(<30字)，大概率缺少构成要件要素。完整的名词解释应包含核心概念+构成要件+法律来源。',
            'found_elements': found
        })
    elif len(found) < 3 and len(text) > 0:
        dets.append({
            'type': 'definition_elements_missing',
            'recommendation': f'定义中检测到的要素信号较少(仅{len(found)}个)。建议补充：主体/客体/内容/目的/构成要件等要素。',
            'found_elements': found
        })
    return {'fired': len(dets) > 0, 'probability': 0.5 if dets else 0.15,
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f14(text, pat):
    """F14: 判对错但不给理由 — 判断题缺法律依据"""
    # 检测纯判断词（正确/错误）且无法律引用
    kw = pat.get('detection_keywords', {})
    judgment_words = kw.get('judgment_words',
                            ['正确', '错误', '对', '错', '✓', '✗', '✅', '❌', '√', '×'])
    has_judgment = False
    for w in judgment_words:
        if len(w) <= 1:
            # 单字判断词需独立成词，避免 针对/对立 等误报
            if re.search(r'(?<![一-鿿])' + re.escape(w) + r'(?![一-鿿])', text):
                has_judgment = True
                break
        elif w in text:
            has_judgment = True
            break
    has_legal_ref = bool(re.search(r'《[^》]+》', text)) or any(
        w in text for w in ['根据', '依据', '因为', '由于', '理由是'])
    dets = []
    if has_judgment and not has_legal_ref and len(text) < 30:
        dets.append({
            'type': 'bare_judgment',
            'recommendation': '仅给出判断结果但未附法律依据。如果题目要求说明理由，应扣分。正确的理由应引用具体法条号。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.8 if dets else 0.1,
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f15(text, pat):
    """F15: 法条解构不完整 — 缺少构成要件→法律后果映射"""
    kw = pat.get('detection_keywords', {})
    structure_signals = kw.get('required_structure', ['构成要件', '法律后果', '适用范围', '规范结构', '立法目的'])
    law_refs = re.findall(r'《([^》]+)》', text)
    has_structure = any(w in text for w in structure_signals)
    dets = []
    if len(law_refs) >= 1 and not has_structure:
        dets.append({
            'type': 'incomplete_deconstruction',
            'laws_referenced': law_refs,
            'recommendation': f'引用了{len(law_refs)}部法律但未进行规范结构解构。法条分析应包含：条文定位→构成要件→法律后果→适用范围→与相关法条的关系。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.55 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f16(text, pat):
    """F16: 论述偏离题眼 — 论述题未紧扣核心争点"""
    # 检测大量使用偏离性过渡词
    kw = pat.get('detection_keywords', {})
    off_topic_signals = kw.get('off_topic_signals', ['此外', '顺便提到', '另外值得注意', '值得一提的是'])
    off_topic_count = sum(1 for s in off_topic_signals if s in text)
    dets = []
    if off_topic_count >= 2 and len(text) > 500:
        dets.append({
            'type': 'potential_off_topic',
            'off_topic_marker_count': off_topic_count,
            'recommendation': f'检测到{off_topic_count}个偏离性过渡词，可能存在论述偏题。建议检查核心关键词与题干争议焦点的重叠率。'
        })
    return {'fired': len(dets) > 0, 'probability': min(off_topic_count * 0.25, 0.8),
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f17(text, pat):
    """F17: 三段论结构缺失 — 案例分析缺少三段论推理"""
    kw = pat.get('detection_keywords', {})
    syll_elem = kw.get('syllogism_elements', {})
    major_words = syll_elem.get('major_premise', ['根据《', '依据《', '法律规定', '按照《', '法条规定'])
    minor_words = syll_elem.get('minor_premise', ['本案中', '本案', '案情', '事实', '证据显示', '本案的'])
    conclusion_words = syll_elem.get('conclusion', ['因此', '综上所述', '综上', '故', '应认定', '所以'])
    major = any(w in text for w in major_words)
    minor = any(w in text for w in minor_words)
    conclusion = any(w in text for w in conclusion_words)
    syllogism = sum([major, minor, conclusion])
    dets = []
    if syllogism < 3 and len(text) > 100:
        missing = []
        if not major: missing.append('大前提(法律规则)')
        if not minor: missing.append('小前提(案件事实)')
        if not conclusion: missing.append('结论')
        dets.append({
            'type': 'syllogism_gap',
            'completeness': f'{syllogism}/3',
            'missing_elements': missing,
            'recommendation': f'三段论结构不完整({syllogism}/3)，缺少: {", ".join(missing)}。完整的案例分析应展示：大前提(法律规则)→小前提(案件事实)→结论的推理链条。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.7 if syllogism == 2 else 0.9 if syllogism <= 1 else 0.1,
            'severity': 'high', 'detections': dets if dets else None,
            'syllogism_completeness': f'{syllogism}/3'}


def detect_f18(text, pat):
    """F18: 要件事实识别错误 — 混淆关键/非关键事实"""
    kw = pat.get('detection_keywords', {})
    fact_words = kw.get('fact_misidentification', ['关键', '重要', '决定性', '核心', '次要', '无关'])
    fact_re = r'(' + '|'.join(re.escape(w) for w in fact_words) + r').{0,10}(事实|情节|情况|因素)'
    fact_emphasis = re.findall(fact_re, text)
    dets = []
    if len(fact_emphasis) >= 2:
        dets.append({
            'type': 'potential_misidentification',
            'fact_emphasis_count': len(fact_emphasis),
            'recommendation': f'检测到{len(fact_emphasis)}处事实重要性的标注。需人工核查：被标注为关键的事实确实是法律要件事实，而非不必要的背景信息。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.4 if dets else 0.1,
            'severity': 'critical', 'detections': dets if dets else None}


# =============================================================================
# v4.1.0: 教信赛场景特化失效模式检测 (F19-F24)
# =============================================================================

def detect_f19(text, pat):
    """F19: 试题歧义偏差 — 试题表述可能产生歧义"""
    kw = pat['detection_keywords']
    ambiguity_signals = kw.get('ambiguity_signals', [])
    found = [s for s in ambiguity_signals if s in text]
    dets = []
    if len(found) >= 3:
        dets.append({
            'type': 'question_ambiguity',
            'ambiguity_markers': found,
            'recommendation': f'题目包含{len(found)}个歧义信号词。建议增加限定条件（时间/法域/范围），确保所有考生对题意的理解一致。'
        })
    return {'fired': len(dets) > 0, 'probability': min(len(found) * 0.2, 0.8),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f20(text, pat):
    """F20: 评分尺度偏移 — 评分系统性地偏严或偏松"""
    kw = pat['detection_keywords']
    grade_anchors = kw.get('grade_anchors', [])
    inconsistency = kw.get('inconsistency_signals', [])
    has_grade = any(g in text for g in grade_anchors)
    has_inconsistency = any(i in text for i in inconsistency)
    dets = []
    if has_grade and has_inconsistency:
        dets.append({
            'type': 'scoring_drift',
            'recommendation': '检测到评分尺度偏移信号。建议引入评分锚定机制：对每个维度设置明确的锚点样例（DS最佳5.0/DS平均3.84/千问最弱1.70），并使用基准测试集校准评分者。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.7 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f21(text, pat):
    """F21: 答案格式违规 — 答案格式不符合题目要求"""
    kw = pat['detection_keywords']
    format_signals = kw.get('format_violation_signals', [])
    # 论述题要求段落式论证，若通篇使用要点列表则触发
    has_format_signals = sum(1 for s in format_signals if s in text)
    has_essay_prose = any(p in text for p in ['综上所述', '首先', '其次', '最后', '论证', '分析如下'])
    dets = []
    if has_format_signals >= 3 and not has_essay_prose and len(text) > 150:
        dets.append({
            'type': 'format_violation',
            'format_marker_count': has_format_signals,
            'recommendation': '答案以要点/列表为主，缺乏段落式论证展开。论述题应包含：问题界定→法理分析→结论论证的完整段落结构。'
        })
    return {'fired': len(dets) > 0, 'probability': min(has_format_signals * 0.15, 0.6),
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f22(text, pat):
    """F22: 跨题一致性破裂 — 同一概念在不同题目中矛盾"""
    kw = pat['detection_keywords']
    contradiction_signals = kw.get('contradiction_signals', [])
    # 检测同一文本中对立概念共存（需要多题联合输入，此处做基础检测）
    opposing_pairs = [('有效', '无效'), ('可撤销', '自始无效'), ('应当', '可以'),
                      ('有罪', '无罪'), ('合法', '违法')]
    dets = []
    for (a, b) in opposing_pairs:
        if a in text and b in text:
            dets.append({
                'type': 'cross_question_contradiction',
                'term_pair': f'{a} vs {b}',
                'recommendation': f'检测到「{a}」与「{b}」对立表述共存。若属于同一学生的多题答案，可能存在跨题一致性破裂：同一法律原则在不同题目中应保持一致的判断。'
            })
            break
    return {'fired': len(dets) > 0, 'probability': 0.6 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None,
            'cross_question_analysis': len(dets) > 0}


def detect_f23(text, pat):
    """F23: 采分点粒度失当 — 答案键采分点过粗或过细"""
    kw = pat['detection_keywords']
    # 检测采分点数量（以"采分点""评分点"后的数字或列表项数量判断）
    point_refs = re.findall(r'[分点采分点评分点].{0,5}?(\d{1,2})', text)
    bullet_count = len(re.findall(r'(?:1[\.、）]|2[\.、）]|3[\.、）]|4[\.、）]|5[\.、）]|6[\.、）]|7[\.、）]|8[\.、）]|9[\.、）]|10[\.、）])', text))
    total_points = max(len(point_refs), bullet_count)
    dets = []
    if 0 < total_points < 3:
        dets.append({
            'type': 'too_few_points',
            'point_count': total_points,
            'recommendation': f'答案键采分点仅{total_points}个，粒度过粗导致区分度不足。建议扩充至3-8个，每个采分点对应一个明确考点。'
        })
    elif total_points > 10:
        dets.append({
            'type': 'too_many_points',
            'point_count': total_points,
            'recommendation': f'答案键采分点多达{total_points}个，粒度过细导致低分泛滥。建议合并至3-8个，与题目分值匹配。'
        })
    return {'fired': len(dets) > 0, 'probability': 0.6 if dets else 0.1,
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f24(text, pat):
    """F24: 教学大纲合规偏离 — 教学内容未覆盖必授核心知识点"""
    kw = pat['detection_keywords']
    core_kps = kw.get('core_knowledge_points', [])
    threshold = kw.get('coverage_threshold', 0.8)
    covered = [kp for kp in core_kps if kp in text]
    ratio = len(covered) / len(core_kps) if core_kps else 1.0
    dets = []
    if ratio < threshold:
        missing = [kp for kp in core_kps if kp not in text]
        dets.append({
            'type': 'syllabus_noncompliance',
            'coverage_ratio': round(ratio, 2),
            'covered_count': len(covered),
            'total_core_points': len(core_kps),
            'missing_knowledge_points': missing,
            'recommendation': f'教学内容对核心知识点的覆盖率仅{round(ratio*100)}%（要求{int(threshold*100)}%以上）。缺失知识点: {", ".join(missing)}。建议对照教育部法学类教学质量国家标准补充。'
        })
    return {'fired': len(dets) > 0, 'probability': round(1 - ratio, 2),
            'severity': 'critical', 'detections': dets if dets else None}


DETECTORS = {
    'F1': detect_f1, 'F2': detect_f2, 'F3': detect_f3, 'F4': detect_f4, 'F5': detect_f5,
    'F6': detect_f6, 'F7': detect_f7, 'F8': detect_f8, 'F9': detect_f9, 'F10': detect_f10,
    'F11': detect_f11, 'F12': detect_f12, 'F13': detect_f13, 'F14': detect_f14,
    'F15': detect_f15, 'F16': detect_f16, 'F17': detect_f17, 'F18': detect_f18,
    'F19': detect_f19, 'F20': detect_f20, 'F21': detect_f21, 'F22': detect_f22,
    'F23': detect_f23, 'F24': detect_f24,
}


def detect_all(text):
    pd = load_failure_patterns()
    patterns = pd['patterns']
    # v4.0.0: 加载F11-F18题型特化模式
    patterns_v2 = pd.get('patterns_v2', [])
    all_patterns = patterns + patterns_v2
    results = {}
    for p in all_patterns:
        pid = p['id']
        detector = DETECTORS.get(pid)
        results[pid] = detector(text, p) if detector else {'fired': False, 'probability': 0, 'severity': 'unknown', 'detections': None}
    fired = 0
    critical = 0
    high = 0
    medium_high = 0
    medium = 0
    for r in results.values():
        if not r['fired']:
            continue
        fired += 1
        sev = r['severity']
        if sev == 'critical':
            critical += 1
        elif sev == 'high':
            high += 1
        elif sev == 'medium_high':
            medium_high += 1
        elif sev == 'medium':
            medium += 1
    dm = pd.get('dimension_mapping_v2', pd.get('dimension_mapping', {}))
    dim_scores = {}
    for dim, related in dm.items():
        if isinstance(related, list):
            rf = [pid for pid in related if results.get(pid, {}).get('fired')]
            dim_scores[dim] = round(5 * (1 - len(rf) / len(related)), 1) if related else 5.0
    total_patterns = len(all_patterns)
    if critical > 0:
        overall_risk = 'critical'
    elif high > 0:
        overall_risk = 'high'
    elif medium_high > 0:
        overall_risk = 'medium'   # 词汇表仅含 low/medium/high/critical，medium_high 档归入 medium
    elif medium > 0:
        overall_risk = 'medium'
    else:
        overall_risk = 'low'
    return {'meta': {'text_length': len(text), 'total_patterns': total_patterns, 'fired_patterns': fired,
                     'critical_fired': critical, 'high_fired': high,
                     'overall_risk': overall_risk},
            'dimension_scores': dim_scores,
            'detections': {pid: r for pid, r in results.items() if r['fired']},
            'all_detections': results}


def main():
    text = None
    if len(sys.argv) >= 2:
        if sys.argv[1] == '--stdin':
            text = sys.stdin.read()
        elif sys.argv[1] == '--text' and len(sys.argv) >= 3:
            text = sys.argv[2]
        else:
            fp = sys.argv[1]
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                print(json.dumps({'error': 'File not found: ' + fp}, ensure_ascii=False))
                sys.exit(1)
    if not text:
        print(json.dumps({'error': 'No input. Usage: failure_detector.py <file> | --text "text" | --stdin'}, ensure_ascii=False))
        sys.exit(1)
    results = detect_all(text)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
