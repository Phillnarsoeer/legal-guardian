#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logic Linter — 逻辑体检（5×4 矩阵 + 8 项确定性筛查）
=====================================================
定位：只做“筛查与定位”，不替代评分、不替代人工判断。
  - 5 个阶段：争点 / 规范 / 事实 / 涵摄 / 边界
  - 4 种失效：缺失 / 错误 / 矛盾 / 溢出
  - 20 个矩阵单元，8 项 MVP 检查（L01–L08）
  - 输出：issue 列表（带 span/why/fix）、阶段×类型热力图、逻辑分、修复顺序
  - 支持单文件、批量目录、学生/AI 两种门控模式

用法:
    python scripts/logic_linter.py <文本文件>
    python scripts/logic_linter.py --text "本案争议焦点是……"
    python scripts/logic_linter.py <文件> --json
    python scripts/logic_linter.py <文件> --out logic.json
    python scripts/logic_linter.py <文件> --mode ai_audit
    python scripts/logic_linter.py --batch <目录> [--out results.jsonl]
    type x.txt | python scripts/logic_linter.py --stdin

退出码:
    0 = 完成（无论是否命中）
    2 = 输入/配置错误
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_PATH = os.path.join(BASE_DIR, 'reference', 'logic_taxonomy.json')
RUBRIC_PATH = os.path.join(BASE_DIR, 'reference', 'logic_rubric.json')
SEED_PATH = os.path.join(BASE_DIR, 'reference', 'statutes_seed.json')

SEVERITY_ORDER = {'critical': 0, 'major': 1, 'minor': 2, 'hint': 3}
SEVERITY_LABEL = {'critical': '致命', 'major': '重大', 'minor': '一般', 'hint': '提示'}


# ---------------------------------------------------------------- 加载配置

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_taxonomy(path=None):
    return load_json(path or TAXONOMY_PATH)


def normalize_law(name):
    s = (name or '').strip().strip('《》').strip()
    s = s.replace('中华人民共和国', '')
    s = re.sub(r'[\s\u3000·•]', '', s)
    return s


_CN_DIGITS = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_CN_UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10000}


def cn_number(text):
    if not text:
        return None
    total, section, number = 0, 0, 0
    for ch in text:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section = 0
            else:
                if number == 0:
                    number = 1
                section += number * unit
            number = 0
        else:
            return None
    return total + section + number


def parse_article(token):
    token = (token or '').strip()
    if not token:
        return None
    return int(token) if token.isdigit() else cn_number(token)


def load_rubric(path=None):
    return load_json(path or RUBRIC_PATH)


def cell_index(taxonomy):
    return {c['id']: c for c in taxonomy.get('cells', [])}


def check_index(taxonomy):
    return {c['id']: c for c in taxonomy.get('checks', [])}


def load_law_entries(seed_path=None):
    """返回 (repealed_entries, active_names, active_index)。

    每条 entry: {kind, names, repealed_date, replaced_by, note, correct_name}
    names 同时包含简称与全称；active_index 用于条文号越界检查。
    """
    seed = load_json(seed_path or SEED_PATH)
    entries = []
    active_names = set()
    active_index = {}
    for law in seed.get('laws', []):
        names = [n for n in [law.get('name'), law.get('full_name')] if n]
        names += list(law.get('aliases', []))
        for name in names:
            active_names.add(name)
            norm = normalize_law(name)
            if norm:
                active_index[norm] = law
    for law in seed.get('repealed', []):
        names = [n for n in [law.get('name'), law.get('full_name')] if n]
        names += list(law.get('aliases', []))
        entries.append({
            'kind': 'repealed',
            'names': names,
            'repealed_date': law.get('repealed_date'),
            'replaced_by': law.get('replaced_by'),
            'note': law.get('note', ''),
        })
    for law in seed.get('fictional', []):
        names = [n for n in [law.get('name'), law.get('full_name')] if n]
        names += list(law.get('aliases', []))
        entries.append({
            'kind': 'fictional',
            'names': names,
            'repealed_date': None,
            'replaced_by': None,
            'note': law.get('note', ''),
            'correct_name': law.get('correct_name'),
        })
    return entries, active_names, active_index


# ---------------------------------------------------------------- 文本工具

def first_marker(text, markers):
    """返回 (index, marker)，找不到返回 (-1, '')。"""
    best = (-1, '')
    for marker in markers:
        idx = text.find(marker)
        if idx != -1 and (best[0] == -1 or idx < best[0]):
            best = (idx, marker)
    return best


def excerpt(text, start, end, width=80):
    s = max(0, start - width // 2)
    e = min(len(text), end + width // 2)
    return re.sub(r'\s+', ' ', text[s:e]).strip()


def sentence_at(text, idx):
    """取 idx 所在句子的大致范围。"""
    if idx < 0:
        return 0, min(len(text), 80)
    left = max(text.rfind('。', 0, idx), text.rfind('\n', 0, idx), text.rfind('；', 0, idx))
    right_candidates = [x for x in (text.find('。', idx), text.find('\n', idx)) if x != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return max(0, left + 1), min(len(text), right + 1)


def make_issue(check, cell, text, start, end, why, fix=None, confidence=None,
               derived_from=None, score_dimension=None):
    start = max(0, start)
    end = max(start, min(len(text), end))
    return {
        'id': '%s-%d' % (check['id'], start),
        'check_id': check['id'],
        'cell': cell['id'],
        'name': check['name'],
        'stage': cell['stage'],
        'failure_type': cell['failure_type'],
        'severity': check['severity'],
        'score_dimension': score_dimension or 'logic',
        'span': {
            'start': start,
            'end': end,
            'excerpt': excerpt(text, start, end),
        },
        'why': why,
        'fix': fix or check.get('fix', ''),
        'confidence': round(confidence if confidence is not None else check.get('confidence', 0.5), 2),
        'derived_from': derived_from,
    }


# ---------------------------------------------------------------- 8 项检查

def check_l01_issue_missing(text, ctx):
    """M11 争点缺失：无争点标记，直接给结论。"""
    if len(text) < 120:
        return []
    issue_markers = ['争议焦点', '核心问题', '争点', '问题在于', '关键在于',
                     '是否构成', '能否', '如何认定', '需要判断', '本案需要解决']
    conclusion_markers = ['综上所述', '综上', '因此', '所以', '结论是', '答案是', '应认定']
    if any(m in text for m in issue_markers):
        return []
    idx, marker = first_marker(text, conclusion_markers)
    if idx == -1:
        return []
    if not any(m in text for m in ['根据《', '依据《', '第', '法', '责任', '构成']):
        return []
    start, end = sentence_at(text, idx)
    return [make_issue(
        ctx['checks']['L01'], ctx['cells']['M11'], text, start, end,
        why='全文未出现争点句（争议焦点/是否构成/如何认定等），却直接给出结论“%s”。' % marker,
        confidence=0.55,
    )]


_CITE_RE = re.compile(r'《([^》]{2,60})》[^。；\n]{0,25}?第\s*([0-9零〇一二两三四五六七八九十百千万]+)\s*条')


def extract_citations(text):
    for m in _CITE_RE.finditer(text):
        yield m.group(1), m.group(2), m.start(), m.end()


def _law_occurrences(text, entries, active_names):
    """找出法名出现位置，优先长名，避免“劳动合同法”被“合同法”误伤。"""
    all_names = set(active_names)
    for entry in entries:
        all_names.update(entry['names'])
    all_occ = []
    for name in all_names:
        if not name:
            continue
        for m in re.finditer(re.escape(name), text):
            all_occ.append((m.start(), m.end(), name))

    candidates = []
    for entry in entries:
        for name in entry['names']:
            for m in re.finditer(re.escape(name), text):
                candidates.append((m.start(), m.end(), name, entry))
    candidates.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    selected, last_end = [], -1
    for start, end, name, entry in candidates:
        if start < last_end:
            continue
        # 若被更长的已知法名覆盖（如“劳动合同法”里的“合同法”），跳过
        covered = any(s <= start and e >= end and (e - s) > (end - start)
                      for s, e, _ in all_occ)
        if covered:
            continue
        selected.append((start, end, name, entry))
        last_end = end
    return selected


def check_l02_repealed_law(text, ctx):
    """M22 规范失效：引用废止/虚构法律且未纠正。"""
    correction = ['已废止', '已被取代', '不再有效', '失效', '已经废止',
                  '被《', '废止', '不适用', '尚未生效']
    issues = []
    for start, end, name, entry in _law_occurrences(text, ctx['repealed'], ctx['active_names']):
        window = text[max(0, start - 80):min(len(text), end + 80)]
        if any(sig in window for sig in correction):
            continue
        if entry['kind'] == 'fictional':
            correct = entry.get('correct_name')
            why = '“%s”被种子库标记为不存在/名称有误。%s' % (name, entry.get('note', ''))
            if correct:
                why += '正确名称应为“%s”。' % correct
            fix = '删除该虚构依据；如为名称错误，改用“%s”。' % correct if correct else '删除该虚构依据，改用真实有效的法律。'
        else:
            why = '“%s”已于 %s 废止，由《%s》取代；文本仍将其作为现行依据。' % (
                name, entry.get('repealed_date') or '未知日期',
                entry.get('replaced_by') or '未知法律')
            fix = '改用《%s》，并注明旧法废止日期。' % (entry.get('replaced_by') or '现行有效法律')
        issues.append(make_issue(
            ctx['checks']['L02'], ctx['cells']['M22'], text, start, end,
            why=why, fix=fix, confidence=0.9, score_dimension='accuracy',
        ))
        if len(issues) >= 5:
            break

    # 补充：现行法的条文号越界（虚构条文的常见形态）
    for law_name, token, cstart, cend in extract_citations(text):
        law = (ctx.get('active_index') or {}).get(normalize_law(law_name))
        if not law or not law.get('article_count'):
            continue
        number = parse_article(token)
        if number and number > law['article_count']:
            issues.append(make_issue(
                ctx['checks']['L02'], ctx['cells']['M22'], text, cstart, cend,
                why='《%s》第 %d 条超出该法条文总数 %d 条，疑似虚构条文号。' % (
                    law.get('full_name') or law_name, number, law['article_count']),
                fix='核对条文号；若为记忆错误，改为实际条文；若不存在，删除该引用。',
                confidence=0.85, score_dimension='accuracy',
            ))
            if len(issues) >= 5:
                break
    return issues


def check_l03_missing_facts(text, ctx):
    """M31 要件事实缺失：有案件指代与结论，但无事实/证据。"""
    if len(text) < 120:
        return []
    if not any(m in text for m in ['本案', '该案', '本案中']):
        return []
    conclusion = ['构成', '应认定', '应当承担', '判处', '支持', '驳回', '成立', '无效', '有效']
    facts = ['经查', '查明', '证据', '事实', '供述', '陈述', '合同', '借条', '转账',
             '监控', '鉴定', '证人', '聊天记录', '发票', '收据', '签订', '约定',
             '催告', '起诉', '报警', '交付', '支付', '受伤', '住院', '滑倒', '骨折',
             '塌落', '死亡', '损失', '损害']
    if not any(m in text for m in conclusion) or any(m in text for m in facts):
        return []
    idx, marker = first_marker(text, ['本案', '该案'])
    start, end = sentence_at(text, idx)
    return [make_issue(
        ctx['checks']['L03'], ctx['cells']['M31'], text, start, end,
        why='出现“%s”与法律结论，但全文没有事实/证据表述，要件事实未经认定。' % marker,
        confidence=0.5,
    )]


def check_l04_syllogism(text, ctx):
    """M41 推理缺环：规范/事实/结论三类标记不足。"""
    if len(text) < 120:
        return []
    if all(m in text for m in ['大前提', '小前提', '结论']):
        return []
    has_rule = bool(re.search(r'(根据|依据|按照|适用|参照)\s*《[^》]+》', text)) or \
        bool(re.search(r'第\s*[0-9零〇一二两三四五六七八九十百千]+\s*条', text)) or \
        ('法律规定' in text)
    has_fact = any(m in text for m in ['本案', '案情', '经查', '查明', '事实', '证据'])
    has_conclusion = any(m in text for m in ['因此', '综上', '应认定', '结论', '所以'])
    found = sum([has_rule, has_fact, has_conclusion])
    if found >= 3:
        return []
    missing = []
    if not has_rule:
        missing.append('大前提（规范）')
    if not has_fact:
        missing.append('小前提（要件事实）')
    if not has_conclusion:
        missing.append('结论')
    idx, marker = first_marker(text, ['因此', '综上', '应认定', '结论', '所以'])
    if idx == -1:
        idx, marker = first_marker(text, ['根据《', '依据《', '本案', '经查'])
    start, end = sentence_at(text, idx)
    return [make_issue(
        ctx['checks']['L04'], ctx['cells']['M41'], text, start, end,
        why='三段论三类标记只出现 %d 类，缺少：%s。' % (found, '、'.join(missing)),
        confidence=0.6,
    )]


def check_l05_conclusion_first(text, ctx):
    """M44 结论先行：强结论词出现在规范/事实之前。"""
    if len(text) < 120:
        return []
    strong = ['因此', '所以', '可见', '综上']
    rule_fact = ['根据《', '依据《', '本案', '经查', '查明', '证据']
    c_idx, c_marker = first_marker(text, strong)
    rf_idx, rf_marker = first_marker(text, rule_fact)
    if rf_idx == -1:
        m = re.search(r'第\s*[0-9零〇一二两三四五六七八九十百千]+\s*条', text)
        if m:
            rf_idx, rf_marker = m.start(), m.group(0)
    if c_idx == -1:
        return []
    if rf_idx == -1 or c_idx < rf_idx - 50:
        start, end = sentence_at(text, c_idx)
        return [make_issue(
            ctx['checks']['L05'], ctx['cells']['M44'], text, start, end,
            why='结论词“%s”出现在规范/事实之前（规范事实起点 %s），有结论先行/倒置论证之嫌。'
                % (c_marker, ('“%s”' % rf_marker) if rf_marker else '未出现'),
            confidence=0.5,
        )]
    return []


def check_l06_contradiction(text, ctx):
    """M43 文内矛盾：互斥结论对并存，且无对比/条件信号。"""
    pairs = [
        ('有效', '无效'), ('成立', '不成立'), ('有罪', '无罪'),
        ('应当', '不应当'), ('可以', '不可以'), ('支持', '不支持'),
        ('驳回', '不驳回'),
    ]
    contrast = ['区别', '而非', '不是', '而是', '反之', '若', '如果', '分别',
                '对比', '不同', 'vs', 'VS', '撤销前', '撤销后', '更正', '并非']
    issues = []
    for pos, neg in pairs:
        neg_matches = list(re.finditer(re.escape(neg), text))
        if not neg_matches:
            continue
        pos_re = re.compile(r'(?<![不无未])' + re.escape(pos))
        pos_matches = list(pos_re.finditer(text))
        if not pos_matches:
            continue
        for nm in neg_matches:
            window = text[max(0, nm.start() - 80):min(len(text), nm.end() + 80)]
            if not pos_re.search(window):
                continue
            if any(sig in window for sig in contrast):
                continue
            start, end = sentence_at(text, nm.start())
            issues.append(make_issue(
                ctx['checks']['L06'], ctx['cells']['M43'], text, start, end,
                why='同一窗口内同时出现“%s”与“%s”，且无对比/条件/更正信号。' % (pos, neg),
                confidence=0.55,
            ))
            break
    return issues[:3]


def _num(s):
    return float(s.replace(',', ''))


def check_l07_numeric(text, ctx):
    """M43 数值不一致：显式算式算错。"""
    issues = []
    eq_re = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s*([×xX*+\-÷/])\s*(\d[\d,]*(?:\.\d+)?)\s*=\s*(\d[\d,]*(?:\.\d+)?)')
    for m in eq_re.finditer(text):
        a, op, b, c = _num(m.group(1)), m.group(2), _num(m.group(3)), _num(m.group(4))
        try:
            if op in ('×', 'x', 'X', '*'):
                expected = a * b
            elif op == '+':
                expected = a + b
            elif op == '-':
                expected = a - b
            elif op == '/':
                expected = a / b if b else None
            else:
                expected = a / b if b else None
        except Exception:
            expected = None
        if expected is None:
            continue
        if abs(expected - c) > 0.01:
            issues.append(make_issue(
                ctx['checks']['L07'], ctx['cells']['M43'], text, m.start(), m.end(),
                why='算式 %s 按 %s 计算应为 %s，文中写 %s。' % (
                    m.group(0), op, ('%.4f' % expected).rstrip('0').rstrip('.'), m.group(4)),
                confidence=0.95,
            ))
    cn_re = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s*(乘以|加上|减去)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:等于|为)\s*(\d[\d,]*(?:\.\d+)?)')
    for m in cn_re.finditer(text):
        a, op, b, c = _num(m.group(1)), m.group(2), _num(m.group(3)), _num(m.group(4))
        expected = a * b if op == '乘以' else (a + b if op == '加上' else a - b)
        if abs(expected - c) > 0.01:
            issues.append(make_issue(
                ctx['checks']['L07'], ctx['cells']['M43'], text, m.start(), m.end(),
                why='算式“%s”按%s计算应为 %s，文中写 %s。' % (
                    m.group(0), op, ('%.4f' % expected).rstrip('0').rstrip('.'), m.group(4)),
                confidence=0.95,
            ))
    return issues[:3]


def check_l08_exception_missing(text, ctx):
    """M51 例外遗漏：绝对表述但无例外/但书。"""
    if len(text) < 100:
        return []
    absolute = ['一律', '任何情况下', '必须', '均须', '均应']
    exception = ['例外', '但书', '除外', '特殊情形', '不适用', '另有规定',
                 '除…外', '除...外', '除非']
    if any(m in text for m in exception) or re.search(r'除[^。；]{0,20}外', text):
        return []
    idx, marker = first_marker(text, absolute)
    if idx == -1:
        return []
    if not any(m in text for m in ['责任', '构成', '应当', '赔偿', '处罚', '无效', '有效', '支持']):
        return []
    start, end = sentence_at(text, idx)
    return [make_issue(
        ctx['checks']['L08'], ctx['cells']['M51'], text, start, end,
        why='出现绝对表述“%s”，但全文未说明例外、但书或除外情形。' % marker,
        confidence=0.5,
    )]


CHECKS = {
    'L01': check_l01_issue_missing,
    'L02': check_l02_repealed_law,
    'L03': check_l03_missing_facts,
    'L04': check_l04_syllogism,
    'L05': check_l05_conclusion_first,
    'L06': check_l06_contradiction,
    'L07': check_l07_numeric,
    'L08': check_l08_exception_missing,
}


# ---------------------------------------------------------------- 根因去重

def apply_dedup(issues, rubric):
    """按 rubric.dedup.dependencies 标记“后果”，避免一案双罚。"""
    deps = rubric.get('dedup', {}).get('dependencies', [])
    for dep in deps:
        sources = [i for i in issues if i['check_id'] == dep.get('from')]
        targets = [i for i in issues if i['check_id'] == dep.get('to')]
        if not sources or not targets:
            continue
        window = dep.get('window', 300)
        for target in targets:
            if target.get('derived_from'):
                continue
            for source in sources:
                if abs(target['span']['start'] - source['span']['start']) <= window:
                    target['derived_from'] = source['id']
                    target['derived_reason'] = dep.get('reason', '')
                    break


# ---------------------------------------------------------------- 汇总与评分

def build_context(taxonomy, rubric, seed_path=None):
    entries, active_names, active_index = load_law_entries(seed_path)
    return {
        'taxonomy': taxonomy,
        'rubric': rubric,
        'cells': cell_index(taxonomy),
        'checks': check_index(taxonomy),
        'repealed': entries,
        'active_names': active_names,
        'active_index': active_index,
    }


def lint_text(text, taxonomy=None, rubric=None, seed_path=None, min_severity='hint',
              mode='student', extra_issues=None, queue_threshold=0.6):
    taxonomy = taxonomy or load_taxonomy()
    rubric = rubric or load_rubric()
    ctx = build_context(taxonomy, rubric, seed_path)
    issues = []
    for check_id in taxonomy.get('mvp_checks', []):
        fn = CHECKS.get(check_id)
        if not fn:
            continue
        issues.extend(fn(text, ctx))
    issues.extend(extra_issues or [])

    # 去重：同一检查、同一起点只保留一条
    seen, uniq = set(), []
    for issue in issues:
        key = (issue['check_id'], issue['span']['start'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(issue)

    uniq.sort(key=lambda x: (SEVERITY_ORDER.get(x['severity'], 9), x['span']['start']))
    cell_dimensions = rubric.get('cell_score_dimension', {})
    for issue in uniq:
        issue['score_dimension'] = cell_dimensions.get(issue['cell'], issue['score_dimension'])
    apply_dedup(uniq, rubric)
    all_issues = uniq
    visible = [i for i in all_issues if SEVERITY_ORDER.get(i['severity'], 9) <= SEVERITY_ORDER.get(min_severity, 3)]

    logic_issues = [i for i in all_issues
                    if i['score_dimension'] == 'logic' and not i.get('derived_from')]
    derived = [i for i in all_issues if i.get('derived_from')]
    red_flags = [i for i in all_issues
                 if i['score_dimension'] != 'logic' and i['severity'] in ('critical', 'major')]

    weights = rubric.get('severity_weights', {'critical': 2.0, 'major': 0.8, 'minor': 0.3, 'hint': 0.1})
    score = float(rubric.get('formula', {}).get('start', 5.0))
    for issue in logic_issues:
        score -= float(weights.get(issue['severity'], 0))
    if any(i['severity'] == 'critical' for i in logic_issues):
        score = min(score, 2.0)
    if any(i['cell'] == 'M43' for i in logic_issues):
        score = min(score, 2.5)
    floor = float(rubric.get('formula', {}).get('floor', 1.0))
    score = max(floor, min(5.0, score))

    heatmap = {s['id']: {t['id']: 0 for t in taxonomy.get('failure_types', [])}
               for s in taxonomy.get('stages', [])}
    for issue in all_issues:
        heatmap.setdefault(issue['stage'], {}).setdefault(issue['failure_type'], 0)
        heatmap[issue['stage']][issue['failure_type']] += 1

    by_severity = Counter(i['severity'] for i in all_issues)
    by_stage = Counter(i['stage'] for i in all_issues)
    by_cell = Counter(i['cell'] for i in all_issues)

    logic_major = any(i['severity'] in ('critical', 'major') for i in logic_issues)
    gate = gate_advice(by_stage, mode)
    human_queue = [i for i in all_issues if i['confidence'] < queue_threshold]
    return {
        'meta': {
            'tool': 'logic_linter',
            'version': '1.0.0',
            'checked_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'taxonomy_version': taxonomy.get('meta', {}).get('version'),
            'rubric_version': rubric.get('meta', {}).get('version'),
            'text_length': len(text),
            'min_severity': min_severity,
            'mode': mode,
        },
        'summary': {
            'total_issues': len(all_issues),
            'visible_issues': len(visible),
            'by_severity': dict(by_severity),
            'by_stage': dict(by_stage),
            'by_cell': dict(by_cell),
            'logic_score': round(score, 1),
            'logic_major_error_free': not logic_major,
            'red_flag_count': len(red_flags),
            'derived_count': len(derived),
            'low_confidence_count': len(human_queue),
            'queue_threshold': queue_threshold,
            'gate_advice': gate,
            'mode': mode,
            'note': '筛查级结果，不构成最终法律判断；critical 项须人工复核。',
        },
        'matrix': heatmap,
        'issues': visible,
        'red_flags': red_flags,
        'human_queue': human_queue,
        'config': {
            'taxonomy': taxonomy.get('meta', {}).get('version'),
            'rubric': rubric.get('meta', {}).get('version'),
            'checks': taxonomy.get('mvp_checks', []),
        },
    }


def build_semantic_packet(text, taxonomy, question=''):
    """生成“语义四格”复核包，交给宿主模型或人工填写。"""
    tasks = []
    for check in taxonomy.get('semantic_checks', []):
        tasks.append({
            'cell': check['cell'],
            'check_id': check['id'],
            'name': check['name'],
            'severity_if_fail': check['severity'],
            'question': check['question'],
            'pass': check['pass'],
            'fail': check['fail'],
            'evidence_required': check['evidence'],
            'fix': check['fix'],
        })
    return {
        'meta': {
            'tool': 'logic_linter.semantic_packet',
            'version': '1.0.0',
            'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'text_length': len(text),
        },
        'question': question or '',
        'text_excerpt': text[:3000],
        'tasks': tasks,
        'response_schema': {
            'reviews': [
                {
                    'cell': 'M12 | M32 | M42 | M52',
                    'verdict': 'pass | fail | unclear',
                    'evidence': '原文片段（尽量逐字引用）',
                    'why': '判断理由',
                    'fix': '修正建议',
                    'confidence': '0.0–1.0',
                }
            ]
        },
        'instructions': ('逐格判断；pass 不产生 issue；fail 产生 major issue；unclear 进入低置信度人工队列。'
                         'evidence 必须逐字引用原文，便于脚本定位 span。'),
    }


def render_semantic_packet(packet):
    lines = ['=' * 68, '语义四格复核包（交给宿主模型/人工填写）', '=' * 68,
             '文本长度: %d 字' % packet['meta']['text_length']]
    if packet.get('question'):
        lines.append('题目/请求: %s' % packet['question'])
    lines.append('-' * 68)
    for i, task in enumerate(packet['tasks'], 1):
        lines.append('%d. %s %s · %s' % (i, task['cell'], task['name'], task['severity_if_fail']))
        lines.append('   问: %s' % task['question'])
        lines.append('   通过: %s' % task['pass'])
        lines.append('   失败: %s' % task['fail'])
        lines.append('   证据: %s' % task['evidence_required'])
        lines.append('')
    lines.append('填写后运行:')
    lines.append('  python scripts/logic_linter.py <文本> --semantic-input review.json --json')
    lines.append('=' * 68)
    return '\n'.join(lines)


def semantic_issues_from_review(text, review, taxonomy, rubric):
    """把语义复核结果转成 issue；只接受 pass/fail/unclear。"""
    cells = cell_index(taxonomy)
    by_cell = {s['cell']: s for s in taxonomy.get('semantic_checks', [])}
    issues = []
    applied = 0
    for item in (review or {}).get('reviews', []):
        cell_id = item.get('cell')
        check = by_cell.get(cell_id)
        verdict = item.get('verdict')
        if not check or verdict not in ('pass', 'fail', 'unclear'):
            continue
        applied += 1
        if verdict == 'pass':
            continue
        evidence = (item.get('evidence') or '').strip()
        if evidence:
            start = text.find(evidence)
            end = start + len(evidence) if start >= 0 else min(len(text), 1)
            if start < 0:
                start = 0
        else:
            start, end = 0, min(len(text), 1)
        try:
            confidence = float(item.get('confidence', 0.7))
        except (TypeError, ValueError):
            confidence = 0.7
        confidence = max(0.0, min(1.0, confidence))
        severity = check['severity'] if verdict == 'fail' else 'hint'
        issue = make_issue(
            {
                'id': check['id'],
                'name': check['name'],
                'severity': severity,
                'fix': item.get('fix') or check.get('fix', ''),
                'confidence': confidence,
            },
            cells[cell_id], text, start, end,
            why=item.get('why') or ('语义复核判定为%s：%s' % (
                '失败' if verdict == 'fail' else '待定', check.get('fail', ''))),
            fix=item.get('fix') or check.get('fix', ''),
            confidence=confidence,
            score_dimension=rubric.get('cell_score_dimension', {}).get(cell_id, 'logic'),
        )
        issues.append(issue)
    return issues, applied


def gate_advice(by_stage, mode='student'):
    orders = {
        'student': ['S1', 'S2', 'S3', 'S4', 'S5'],
        'ai_audit': ['S2', 'S3', 'S4', 'S1', 'S5'],
    }
    order = orders.get(mode, orders['student'])
    messages = {
        'S1': '先修争点层：争点缺失/错位会让后续论证全部偏航。',
        'S2': '先修规范层：先确认法条存在、现行有效、与争点对应。',
        'S3': '先修事实层：补齐要件事实与证据对应，再谈涵摄。',
        'S4': '先修涵摄层：补齐三段论，处理概念、因果与数值一致性。',
        'S5': '先修边界层：补例外/但书、举证责任与结论射程。',
    }
    for stage in order:
        if by_stage.get(stage):
            return messages[stage]
    return '未发现明显逻辑断点；仍建议人工复核关键结论。'
    orders = {
        'student': ['S1', 'S2', 'S3', 'S4', 'S5'],
        'ai_audit': ['S2', 'S3', 'S4', 'S1', 'S5'],
    }
    order = orders.get(mode, orders['student'])
    messages = {
        'S1': '先修争点层：争点缺失/错位会让后续论证全部偏航。',
        'S2': '先修规范层：先确认法条存在、现行有效、与争点对应。',
        'S3': '先修事实层：补齐要件事实与证据对应，再谈涵摄。',
        'S4': '先修涵摄层：补齐三段论，处理概念、因果与数值一致性。',
        'S5': '先修边界层：补例外/但书、举证责任与结论射程。',
    }
    for stage in order:
        if by_stage.get(stage):
            return messages[stage]
    return '未发现明显逻辑断点；仍建议人工复核关键结论。'


# ---------------------------------------------------------------- 输出

def render_text(result):
    meta = result['meta']
    summary = result['summary']
    lines = []
    width = 68
    lines.append('=' * width)
    lines.append('逻辑体检 · 5×4 矩阵（筛查级）')
    lines.append('=' * width)
    lines.append('文本长度: %d 字    检查时间: %s' % (meta['text_length'], meta['checked_at']))
    mode_label = {'student': '学生作业', 'ai_audit': 'AI 输出审核'}.get(meta.get('mode'), meta.get('mode') or '通用')
    lines.append('模式: %s    派生（不重复扣分）: %d 项' % (mode_label, summary.get('derived_count', 0)))
    lines.append('低置信度: %d 项（阈值 %.2f，建议人工复核）' % (
        summary.get('low_confidence_count', 0), summary.get('queue_threshold', 0.6)))
    lines.append('命中: %d 项（致命 %d / 重大 %d / 一般 %d / 提示 %d）' % (
        summary['total_issues'],
        summary['by_severity'].get('critical', 0),
        summary['by_severity'].get('major', 0),
        summary['by_severity'].get('minor', 0),
        summary['by_severity'].get('hint', 0),
    ))
    lines.append('逻辑分: %.1f / 5.0（仅 logic 维度）    逻辑维度重大错误: %s    跨维度红旗: %d' % (
        summary['logic_score'],
        '无' if summary['logic_major_error_free'] else '有',
        summary['red_flag_count'],
    ))
    lines.append('修复顺序: ' + summary['gate_advice'])
    lines.append('-' * width)
    lines.append('矩阵（行=阶段，列=失效类型；数字=命中数，含跨维度红旗）')

    stages = ['S1', 'S2', 'S3', 'S4', 'S5']
    stage_names = {'S1': '争点', 'S2': '规范', 'S3': '事实', 'S4': '涵摄', 'S5': '边界'}
    types = ['T1', 'T2', 'T3', 'T4']
    type_names = {'T1': '缺失', 'T2': '错误', 'T3': '矛盾', 'T4': '溢出'}
    lines.append('        ' + '  '.join('%-4s' % type_names[t] for t in types))
    for s in stages:
        row = result['matrix'].get(s, {})
        lines.append('%-6s  ' % stage_names[s] + '  '.join('%-4d' % row.get(t, 0) for t in types))
    lines.append('-' * width)

    if not result['issues']:
        lines.append('未发现明显逻辑断点。注意：筛查通过 ≠ 人工复核通过。')
    else:
        lines.append('问题清单（按严重度排序）')
        for issue in result['issues']:
            suffix = ''
            if issue.get('derived_from'):
                suffix = '（后果，derived_from=%s，不重复扣分）' % issue['derived_from']
            lines.append('[%s] %s %s · %s/%s%s' % (
                SEVERITY_LABEL.get(issue['severity'], issue['severity']),
                issue['cell'], issue['name'],
                stage_names.get(issue['stage'], issue['stage']),
                type_names.get(issue['failure_type'], issue['failure_type']),
                suffix,
            ))
            lines.append('  位置: %s' % issue['span']['excerpt'])
            lines.append('  原因: %s' % issue['why'])
            lines.append('  修正: %s' % issue['fix'])
            lines.append('  置信度: %.2f' % issue['confidence'])
            lines.append('')

    if result['red_flags']:
        lines.append('-' * width)
        lines.append('跨维度红旗（不计入逻辑分，须在准确性/时效性维度处理）')
        for issue in result['red_flags']:
            lines.append('- [%s] %s %s：%s' % (
                SEVERITY_LABEL.get(issue['severity'], issue['severity']),
                issue['cell'], issue['name'], issue['why']))
    if result.get('human_queue'):
        lines.append('-' * width)
        lines.append('低置信度待复核（confidence < %.2f）' % result['summary'].get('queue_threshold', 0.6))
        for issue in result['human_queue']:
            lines.append('- [%s] %s %s（%.2f）：%s' % (
                SEVERITY_LABEL.get(issue['severity'], issue['severity']),
                issue['cell'], issue['name'], issue['confidence'], issue['why'][:80]))
    lines.append('=' * width)
    return '\n'.join(lines)


def read_text_file(path):
    """读取单文件；.json 优先取 ai_response/text/content。"""
    if path.lower().endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key in ('ai_response', 'text', 'content'):
            if isinstance(data, dict) and isinstance(data.get(key), str):
                return data[key]
        return json.dumps(data, ensure_ascii=False)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def read_input(args):
    if args.text:
        return args.text
    if args.stdin:
        return sys.stdin.read()
    if args.file:
        return read_text_file(args.file)
    return ''


def iter_batch_files(directory):
    exts = {'.txt', '.md', '.json'}
    for root, dirs, names in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for name in sorted(names):
            if name.startswith('.'):
                continue
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(root, name)


def batch_lint(directory, taxonomy, rubric, seed_path=None, min_severity='hint', mode='student',
               queue_threshold=0.6):
    records = []
    queue = []
    for path in iter_batch_files(directory):
        rel = os.path.relpath(path, directory).replace('\\', '/')
        try:
            text = read_text_file(path)
            result = lint_text(text, taxonomy=taxonomy, rubric=rubric,
                               seed_path=seed_path, min_severity=min_severity, mode=mode,
                               queue_threshold=queue_threshold)
            records.append({'file': rel, 'result': result})
            for issue in result.get('human_queue', []):
                queue.append({'file': rel, 'issue': issue})
        except Exception as exc:
            records.append({'file': rel, 'error': str(exc)})

    by_severity, by_stage, by_cell = Counter(), Counter(), Counter()
    total_issues = clean_files = major_free_files = derived = low_confidence = 0
    scores = []
    for rec in records:
        result = rec.get('result')
        if not result:
            continue
        summary = result['summary']
        total_issues += summary['total_issues']
        if summary['total_issues'] == 0:
            clean_files += 1
        if summary['logic_major_error_free']:
            major_free_files += 1
        derived += summary.get('derived_count', 0)
        low_confidence += summary.get('low_confidence_count', 0)
        scores.append(summary['logic_score'])
        by_severity.update(summary.get('by_severity', {}))
        by_stage.update(summary.get('by_stage', {}))
        by_cell.update(summary.get('by_cell', {}))
    aggregate = {
        'files': len(records),
        'clean_files': clean_files,
        'files_with_major_error': len(records) - major_free_files,
        'total_issues': total_issues,
        'derived_count': derived,
        'low_confidence_count': low_confidence,
        'avg_logic_score': round(sum(scores) / len(scores), 2) if scores else None,
        'by_severity': dict(by_severity),
        'by_stage': dict(by_stage),
        'by_cell': dict(by_cell),
        'top_cells': by_cell.most_common(5),
    }
    return {
        'meta': {
            'tool': 'logic_linter',
            'version': '1.0.0',
            'mode': 'batch',
            'checked_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'directory': os.path.abspath(directory),
            'mode_setting': mode,
            'min_severity': min_severity,
        },
        'aggregate': aggregate,
        'records': records,
        'queue': queue,
    }


def render_batch_text(batch):
    agg = batch['aggregate']
    lines = ['=' * 68, '批量逻辑体检', '=' * 68,
             '目录: %s' % batch['meta']['directory'],
             '模式: %s    文件: %d    干净: %d    重大错误文件: %d' % (
                 {'student': '学生作业', 'ai_audit': 'AI 输出审核'}.get(batch['meta']['mode_setting'],
                                                                        batch['meta']['mode_setting']),
                 agg['files'], agg['clean_files'], agg['files_with_major_error']),
             '命中: %d 项（派生不重复扣分: %d）    平均逻辑分: %s' % (
                 agg['total_issues'], agg['derived_count'],
                 ('%.2f' % agg['avg_logic_score']) if agg['avg_logic_score'] is not None else '—'),
             '低置信度: %d 项（建议人工复核）' % agg.get('low_confidence_count', 0),
             '严重度: 致命 %d / 重大 %d / 一般 %d / 提示 %d' % (
                 agg['by_severity'].get('critical', 0), agg['by_severity'].get('major', 0),
                 agg['by_severity'].get('minor', 0), agg['by_severity'].get('hint', 0)),
             '阶段: ' + '  '.join('%s=%d' % (k, v) for k, v in sorted(agg['by_stage'].items())) if agg['by_stage'] else '阶段: —',
             '高频断点: ' + ('  '.join('%s(%d)' % (c, n) for c, n in agg['top_cells']) if agg['top_cells'] else '—'),
             '-' * 68]
    for rec in batch['records']:
        if rec.get('error'):
            lines.append('- %-40s  读取失败：%s' % (rec['file'], rec['error']))
        else:
            s = rec['result']['summary']
            lines.append('- %-40s  逻辑分 %.1f  命中 %d  红旗 %d' % (
                rec['file'], s['logic_score'], s['total_issues'], s['red_flag_count']))
    lines.append('=' * 68)
    return '\n'.join(lines)


def write_queue(path, issues, file_label=''):
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for issue in issues:
            f.write(json.dumps({'file': file_label, 'issue': issue}, ensure_ascii=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='逻辑体检：5×4 矩阵 + 8 项确定性筛查（只定位，不替代人工）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python scripts/logic_linter.py case.md\n'
               '  python scripts/logic_linter.py --text "本案争议焦点是……"\n'
               '  python scripts/logic_linter.py case.md --json --out logic.json\n'
               '  type case.txt | python scripts/logic_linter.py --stdin',
    )
    parser.add_argument('file', nargs='?', help='输入文本文件（.txt/.md/.json）')
    parser.add_argument('--text', help='直接传入文本')
    parser.add_argument('--stdin', action='store_true', help='从标准输入读取')
    parser.add_argument('--batch', help='批量处理目录（.txt/.md/.json）')
    parser.add_argument('--mode', default='student', choices=['student', 'ai_audit'],
                        help='门控模式：学生作业（S1→S5）或 AI 审核（S2→S1）')
    parser.add_argument('--question', help='题目/请求（用于语义四格判断）')
    parser.add_argument('--semantic', action='store_true', help='输出语义四格复核包')
    parser.add_argument('--semantic-input', help='语义四格复核结果 JSON')
    parser.add_argument('--queue-threshold', type=float, default=0.6,
                        help='低置信度阈值（默认 0.6）')
    parser.add_argument('--queue-out', help='低置信度问题写入 JSONL')
    parser.add_argument('--json', action='store_true', dest='as_json', help='输出 JSON')
    parser.add_argument('--out', help='单文件写 JSON；批量写 JSONL')
    parser.add_argument('--min-severity', default='hint',
                        choices=['critical', 'major', 'minor', 'hint'],
                        help='问题清单最低显示级别（默认 hint）')
    parser.add_argument('--taxonomy', help='逻辑矩阵路径（默认 reference/logic_taxonomy.json）')
    parser.add_argument('--rubric', help='评分规则路径（默认 reference/logic_rubric.json）')
    parser.add_argument('--seed', help='法条种子库路径（默认 reference/statutes_seed.json）')
    args = parser.parse_args(argv)

    try:
        taxonomy = load_taxonomy(args.taxonomy)
        rubric = load_rubric(args.rubric)
    except Exception as exc:
        msg = '错误：无法加载配置（%s）' % exc
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    if args.batch:
        if not os.path.isdir(args.batch):
            msg = '错误：--batch 目录不存在：%s' % args.batch
            if args.as_json:
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
            else:
                print(msg, file=sys.stderr)
            return 2
        batch = batch_lint(args.batch, taxonomy, rubric, seed_path=args.seed,
                           min_severity=args.min_severity, mode=args.mode,
                           queue_threshold=args.queue_threshold)
        if args.queue_out:
            out_dir = os.path.dirname(os.path.abspath(args.queue_out))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.queue_out, 'w', encoding='utf-8') as f:
                for item in batch.get('queue', []):
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            if not args.as_json:
                print('低置信度队列已写入: %s' % args.queue_out)
        if args.out:
            out_dir = os.path.dirname(os.path.abspath(args.out))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.out, 'w', encoding='utf-8') as f:
                for rec in batch['records']:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            if not args.as_json:
                print('批量 JSONL 已写入: %s' % args.out)
        if args.as_json:
            print(json.dumps({'meta': batch['meta'], 'aggregate': batch['aggregate']},
                             ensure_ascii=False, indent=2))
        else:
            print(render_batch_text(batch))
        return 0

    try:
        text = read_input(args)
    except Exception as exc:
        msg = '错误：无法读取输入（%s）' % exc
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    if not text or not text.strip():
        msg = '错误：未提供文本。请传文件、--text 或 --stdin。'
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    if args.semantic:
        packet = build_semantic_packet(text, taxonomy, args.question or '')
        if args.as_json:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
        else:
            print(render_semantic_packet(packet))
        return 0

    extra_issues = None
    applied = 0
    if args.semantic_input:
        try:
            with open(args.semantic_input, 'r', encoding='utf-8') as f:
                review = json.load(f)
        except Exception as exc:
            msg = '错误：无法读取语义复核结果（%s）' % exc
            if args.as_json:
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
            else:
                print(msg, file=sys.stderr)
            return 2
        extra_issues, applied = semantic_issues_from_review(text, review, taxonomy, rubric)
        if applied == 0:
            msg = '错误：语义复核结果中没有有效的 reviews（cell 必须是 M12/M32/M42/M52）。'
            if args.as_json:
                print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
            else:
                print(msg, file=sys.stderr)
            return 2

    result = lint_text(text, taxonomy=taxonomy, rubric=rubric,
                       seed_path=args.seed, min_severity=args.min_severity, mode=args.mode,
                       extra_issues=extra_issues, queue_threshold=args.queue_threshold)
    if applied:
        result['meta']['semantic_input'] = os.path.abspath(args.semantic_input)
        result['summary']['semantic_reviews'] = applied

    if args.queue_out:
        write_queue(args.queue_out, result.get('human_queue', []), args.file or '')
        if not args.as_json:
            print('低置信度队列已写入: %s' % args.queue_out)

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if not args.as_json:
            print('JSON 已写入: %s' % args.out)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
