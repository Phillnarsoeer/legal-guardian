#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Failure Detector - 10 failure pattern detection engine.
Based on empirical research: multi-case x 2 rounds x 4 dimensions.
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
    """F1 法条幻视：接受虚构/废止法律为真实。

    v4.3.0 修复（评审缺陷#1）：嫌疑法条命中时先做"纠正文语境豁免"——
    若命中点邻近出现 已废止/已被取代/正式取代/不再具有法律效力 等纠正信号，
    说明 AI 已主动纠正，不视为违规（避免干净回答被误判 critical）。
    """
    kw = pat['detection_keywords']
    suspects = kw['suspect_laws']
    indicators = kw['suspect_indicators']
    validity_signals = kw.get('validity_signals', [])
    # 额外的中文纠正信号（validity_signals 之外的常见表达）
    extra_correction = ['正式取代', '不再具有法律效力', '已失去法律效力', '已被废除', '已不适用']
    correction_signals = tuple(validity_signals) + tuple(extra_correction)
    # 虚构法条的"证伪信号"：AI 指出该法不存在
    refute_signals = ['不存在', '并非真实', '无此法律', '未检索到', '没有这部法律', '虚构']
    dets = []

    def _is_corrected(name, refute=False):
        idx = text.find(name)
        if idx == -1:
            return False
        s = max(0, idx - 40)
        e = min(len(text), idx + len(name) + 80)
        window = text[s:e]
        return any(sig in window for sig in (refute_signals if refute else correction_signals))

    for law in suspects:
        if law in text and not _is_corrected(law):
            dets.append({'type': 'repealed_law', 'law_name': law,
                         'evidence_text': extract_context(text, law),
                         'recommendation': law + ' was replaced by Civil Code on 2021-01-01'})
    for ind in indicators:
        if ind in text and not _is_corrected(ind, refute=True):
            dets.append({'type': 'possible_fictional', 'law_name': ind,
                         'evidence_text': extract_context(text, ind),
                         'recommendation': 'Verify if ' + ind + ' actually exists'})
    cp = re.compile(r'(?:According to|under|pursuant to|per)\s*[《]([^》]+)[》]')
    cites = cp.findall(text)
    for c in cites:
        if c not in suspects and c not in indicators:
            has_v = any(v in text for v in validity_signals)
            if not has_v and c not in [d.get('law_name', '') for d in dets]:
                dets.append({'type': 'missing_validity', 'law_name': c,
                             'recommendation': 'Mark effective date when citing ' + c})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.3, 1.0),
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f2(text, pat):
    """F2 罪名定性降维：AI 倾向轻罪定性，回避争议性定性。

    v4.3.0 修复（评审缺陷#3）：rel 比对键由英文改为中文罪名，
    此前因中英键名不匹配该模式永不触发（死代码）。
    """
    kw = pat['detection_keywords']
    charges = kw['charge_indicators']
    found = [c for c in charges if c in text]
    has_alt = any(p in text for p in ['alternative', 'also', 'might constitute', 'prosecution perspective', 'defense perspective',
                                      '另一种', '也可能', '控方', '辩方', '替代罪名', '争议'])
    dets = []
    if len(found) == 1 and not has_alt:
        rel = {'故意伤害': '故意杀人', '聚众斗殴': '故意伤害',
               '抢夺': '抢劫', '盗窃': '抢劫'}
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
    """F6 引导性赤字：缺实务操作指导。

    v4.3.0 修复：要素关键词由纯英文扩展为 中英双语，
    此前中文回答几乎无法命中任何要素，长文本一律误报。
    """
    kw = pat['detection_keywords']
    missing = kw['missing_guidance_elements']
    elem_pats = {
        'evidence list': ['evidence', 'collect', 'proof', 'evidence list', 'prepare', 'notarize',
                          '证据', '举证', '收集', '公证', '借条', '合同', '转账记录', '证人'],
        'procedure steps': ['step', 'procedure', 'process', 'first', 'then', 'action',
                            '步骤', '程序', '流程', '起诉', '立案', '开庭', '申请', '时效'],
        'timeline': ['limitation', 'deadline', 'timeline', 'days', 'within', 'from the date',
                     '期限', '时间', '日期', '天数', '三年'],
        'risk warning': ['risk', 'caution', 'warning', 'disclaimer', 'does not constitute', 'for reference only',
                         '风险', '警示', '仅供参考', '不构成法律意见', '注意', '谨慎'],
        'alternatives': ['negotiate', 'mediation', 'arbitration', 'alternative', 'settlement',
                         '协商', '调解', '仲裁', '和解', '替代方案', '向法院起诉']
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
    """F10 用户差异化风险盲区：不区分法学生/非专业人士输出。

    v4.3.0 修复（评审缺陷#S3-误报）：逻辑由"无用户上下文即报"翻转为
    "已声明用户类型却未差异化输出才报"，避免对普通问答一律误伤。
    """
    kw = pat['detection_keywords']
    user_inds = kw['user_type_indicators']
    has_user_ctx = any(ind in text for ind in user_inds)
    has_diff = any(p in text for p in ['as a law student', 'as a lawyer', 'for non-professionals', 'if you are', 'for general readers',
                                       '针对法学生', '面向非专业人士', '通俗解释', '风险提示', '建议咨询律师', '不同用户'])
    dets = []
    if has_user_ctx and not has_diff:
        dets.append({'type': 'no_user_differentiation', 'user_type_declared': [u for u in user_inds if u in text],
                     'recommendation': 'Differentiate output by user background: law students get deep analysis; non-professionals get plain language + prominent risk warnings + lawyer referral'})
    return {'fired': len(dets) > 0, 'probability': 0.7 if dets else 0.2,
            'severity': 'critical', 'detections': dets if dets else None}


# =============================================================================
# v4.0.0: 题型特化失效模式检测 (F11-F18)
# =============================================================================

def detect_f11(text, pat):
    """F11: 选项混淆偏误 — 选择题中将相似法律概念混淆。

    v4.3.0 修复：v2 正则对（"可撤销.*无效"）与 v1 默认对合并解析；
    "应当/可以"等可合法共存的词对需附带混淆标记（等同/还是/或者等）才触发，
    避免对正常法律表述误报。
    """
    default_pairs = [
        ('可撤销', '无效', False, False),
        ('效力待定', '无效', False, False),
        ('解除', '撤销', False, False),
        ('终止', '中止', False, False),
        ('应当', '可以', True, True),
        ('从轻', '减轻', True, True),
    ]
    # 混淆标记词：出现时说明作者在概念间做取舍/等价判断，混淆风险高
    confusion_markers = ['等同', '等于', '等同于', '就是', '意味着', '还是', '或者', '应理解为']
    kw = pat.get('detection_keywords', {})
    raw_pairs = kw.get('confusion_pairs', default_pairs)
    # 解析：v2 正则串 "可撤销.*无效" → (term1, term2, ordered=True, need_marker=False)
    confusion_pairs = []
    if isinstance(raw_pairs, list):
        for item in raw_pairs:
            if isinstance(item, str):
                if '.*' in item:
                    parts = [x.strip() for x in item.split('.*') if x.strip()]
                    if len(parts) >= 2:
                        confusion_pairs.append((parts[0], parts[-1], True, False))
                else:
                    terms = re.split(r'\s*[、,，]\s*', item)
                    if len(terms) >= 2:
                        confusion_pairs.append((terms[0].strip(), terms[1].strip(), False, False))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                if isinstance(item[0], (list, tuple)):
                    confusion_pairs.append((item[0][0], item[0][1] if len(item[0]) > 1 else '', False, False))
                elif all(isinstance(x, str) for x in item):
                    confusion_pairs.append((item[0], item[1], False, False))
    # 合并 v1 默认对（去重：词对已存在则跳过）
    existing = {(p[0], p[1]) for p in confusion_pairs}
    for t1, t2, ordered, marker in default_pairs:
        if (t1, t2) not in existing:
            confusion_pairs.append((t1, t2, ordered, marker))
    dets = []
    for term1, term2, ordered, need_marker in confusion_pairs:
        # 检测两个混淆词出现且未明确区分（正则对要求按先后顺序出现）
        if term1 in text and term2 in text:
            if ordered:
                i1 = text.find(term1)
                i2 = text.find(term2)
                if i1 > i2:
                    continue
            if need_marker and not any(m in text for m in confusion_markers):
                continue
            # 检查是否有区分性表述
            has_clarification = any(w in text for w in ['不同于', '区别于', '不等于', '不是', '≠', '区分'])
            if not has_clarification:
                dets.append({
                    'type': 'concept_confusion',
                    'term1': term1,
                    'term2': term2,
                    'recommendation': f'注意区分「{term1}」与「{term2}」的实质差异。'
                })
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.35, 1.0),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f12(text, pat):
    """F12: 采分点遗漏 — 简答题遗漏关键采分点。

    v4.3.0 修复：增加简答题语境门控，避免对非简答文本一律误报。
    """
    kw = pat.get('detection_keywords', {})
    # 简答题语境门控（本模式目标题型 T5）
    short_answer_context = ['简答', '简述', '采分点', '要点', '答案']
    if not any(s in text for s in short_answer_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'high', 'detections': None}
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
    """F13: 定义要素缺失 — 名词解释缺少核心要素。

    v4.3.0 修复：增加名词解释语境门控（目标题型 T4），
    避免对任何未含定义要素词的文本一律误报。
    """
    kw = pat.get('detection_keywords', {})
    # 名词解释语境门控
    definition_context = ['名词解释', '是指', '指的是', '定义', '概念', '释义', '含义']
    if not any(s in text for s in definition_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'medium_high', 'detections': None}
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
    """F15: 法条解构不完整 — 缺少构成要件→法律后果映射。

    v4.3.0 修复：增加法条分析语境门控（目标题型 T7），
    避免对普通法律问答（仅引用法条）一律误报。
    """
    kw = pat.get('detection_keywords', {})
    # 法条分析语境门控
    analysis_context = ['法条分析', '条文', '规范结构', '构成要件', '法律后果',
                        '本法条', '该条', '请分析《', '请解析《', '解析《', '分析《', '规范解构']
    if not any(s in text for s in analysis_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'high', 'detections': None}
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
    """F17: 三段论结构缺失 — 案例分析缺少三段论推理。

    v4.3.0 修复（评审缺陷#2）：
    1) 显式标记豁免：出现"大前提/小前提/结论"字面标记视为结构完整；
    2) 语境门控：本模式目标题型为 T8 案例分析，非案例分析文本不触发。
    """
    kw = pat.get('detection_keywords', {})
    syll_elem = kw.get('syllogism_elements', {})
    major_words = syll_elem.get('major_premise', ['根据《', '依据《', '法律规定', '按照《', '法条规定'])
    minor_words = syll_elem.get('minor_premise', ['本案中', '本案', '案情', '事实', '证据显示', '本案的'])
    conclusion_words = syll_elem.get('conclusion', ['因此', '综上所述', '综上', '故', '应认定', '所以', '结论'])
    # 案例分析语境门控（目标题型 T8）
    case_analysis_context = ['案例分析', '案情', '本案中', '案件事实', '案例分析题', '法院认为',
                             '判决', '请分析', '分析侵权责任', '刑事责任', '侵权责任']
    if not any(s in text for s in case_analysis_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'high', 'detections': None,
                'syllogism_completeness': 'N/A'}
    # 显式三段论标记豁免
    explicit_markers = all(w in text for w in ['大前提', '小前提', '结论'])
    major = any(w in text for w in major_words) or explicit_markers
    minor = any(w in text for w in minor_words) or explicit_markers
    conclusion = any(w in text for w in conclusion_words) or explicit_markers
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
    """F21: 答案格式违规 — 答案格式不符合题目要求。

    v4.3.0 修复：论述语境门控（论述/论文类文本 + 要点列表 ≥3 项才触发），
    替代原先的固定长度阈值，短文本要点式作答也能命中。
    """
    kw = pat['detection_keywords']
    format_signals = kw.get('format_violation_signals', [])
    # 论述题要求段落式论证，若通篇使用要点列表则触发
    has_format_signals = sum(1 for s in format_signals if s in text)
    has_essay_prose = any(p in text for p in ['综上所述', '首先', '其次', '最后', '论证', '分析如下', '段落', '一方面', '另一方面'])
    essay_context = any(w in text for w in ['论述', '作文', '小论文', '论文', '评述', '阐述'])
    dets = []
    if has_format_signals >= 3 and not has_essay_prose and (essay_context or len(text) > 150):
        dets.append({
            'type': 'format_violation',
            'format_marker_count': has_format_signals,
            'recommendation': '答案以要点/列表为主，缺乏段落式论证展开。论述题应包含：问题界定→法理分析→结论论证的完整段落结构。'
        })
    return {'fired': len(dets) > 0, 'probability': min(has_format_signals * 0.15, 0.6),
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f22(text, pat):
    """F22: 跨题一致性破裂 — 同一概念在不同题目中矛盾。

    v4.3.0 修复：本模式需多题联合输入。单文本仅作基础信号，
    增加矛盾转折词门控（"却/但/矛盾/不一致"等），并移除
    "应当+可以"伪矛盾对（两者在法言法语中可合法共存）。
    """
    kw = pat['detection_keywords']
    contradiction_signals = kw.get('contradiction_signals', [])
    # 矛盾转折词门控：无转折/否定词时，对立概念共存属正常表述
    conflict_words = ['矛盾', '冲突', '不一致', '前后不一', '却又', '却写道', '但写道',
                      '但后面', '又说', '相反', '却称', '却答']
    if not any(w in text for w in conflict_words):
        return {'fired': False, 'probability': 0.1, 'severity': 'high', 'detections': None,
                'cross_question_analysis': False}
    # 检测同一文本中对立概念共存（需要多题联合输入，此处做基础检测）
    opposing_pairs = [('有效', '无效'), ('可撤销', '自始无效'),
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
    """F23: 采分点粒度失当 — 答案键采分点过粗或过细。

    v4.3.0 修复：增加答案键/采分点语境门控，
    避免普通文本中的编号列表（如小数 "3.2"）被误计为采分点。
    """
    kw = pat['detection_keywords']
    # 答案键语境门控（本模式评估对象为答案键/评分标准）
    answer_key_context = ['答案键', '采分点', '评分点', '评分标准', '参考答案']
    if not any(s in text for s in answer_key_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'medium_high', 'detections': None}
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


def _load_curriculum_knowledge_points():
    """加载教育部课程标准知识点（reference/curriculum_requirements.json，18项）。

    v4.3.0 修复（评审缺陷#7）：F24 数据源由硬编码 8 项改为
    curriculum_requirements.json 的 18 项核心知识点（含各知识点关键词）。
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, '..', 'reference', 'curriculum_requirements.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        kps = data.get('knowledge_points', [])
        if kps:
            return [
                {'name': kp.get('name', ''), 'keywords': kp.get('keywords', [])}
                for kp in kps if kp.get('name')
            ]
    except Exception:
        pass
    return []


def detect_f24(text, pat):
    """F24: 教学大纲合规偏离 — 教学内容未覆盖必授核心知识点。

    v4.3.0 修复：
    1) 大纲语境门控：仅对教学大纲/教案/课程内容类文本触发；
    2) 数据源改为 curriculum_requirements.json 的 18 项知识点
       （知识点名+关键词匹配），不再使用硬编码 8 项。
    """
    kw = pat['detection_keywords']
    threshold = kw.get('coverage_threshold', 0.8)
    # 大纲语境门控（本模式评估对象为教学大纲/教案/教学内容）
    syllabus_context = ['教学大纲', '课程大纲', '大纲', '教案', '课程标准',
                        '人才培养方案', '授课计划', '教学内容', '知识点覆盖']
    if not any(s in text for s in syllabus_context):
        return {'fired': False, 'probability': 0.1, 'severity': 'critical', 'detections': None}
    # 优先使用 curriculum_requirements.json 的 18 项知识点
    kps = _load_curriculum_knowledge_points()
    if not kps:
        # 兜底：文件缺失时退回 patterns 中的硬编码清单
        kps = [{'name': kp, 'keywords': []} for kp in kw.get('core_knowledge_points', [])]
    covered = []
    missing = []
    for kp in kps:
        terms = [kp['name']] + list(kp.get('keywords', []))
        if any(t and t in text for t in terms):
            covered.append(kp['name'])
        else:
            missing.append(kp['name'])
    ratio = len(covered) / len(kps) if kps else 1.0
    dets = []
    if ratio < threshold:
        dets.append({
            'type': 'syllabus_noncompliance',
            'coverage_ratio': round(ratio, 2),
            'covered_count': len(covered),
            'total_core_points': len(kps),
            'covered_knowledge_points': covered,
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
