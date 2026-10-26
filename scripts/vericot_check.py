#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VeriCoT 完整版 — 结构化法律论证的符号校验器
==========================================
流程：宿主模型把论证抽取为 premises/steps/conclusion + FOL formula →
      本脚本解析 FOL → 有限域接地 → DPLL 可满足性 → 蕴涵检查。

两种模式:
    - full：只要任一 premise/step 带 formula，自动进入完整版
    - lite：没有 formula 时退化为结构校验（前提/引用/步骤/结论闭环）

边界:
    - 本脚本**不负责 NL→FOL 抽取**（那一步由宿主模型按 --packet 生成）
    - 函数无关 FOL；不支持函数符号与等词（用 Same(x,y) 谓词代替）
    - 有限域接地；域为空时使用公式常量或 __d0；原子数超限返回 undecided

用法:
    python scripts/vericot_check.py argument.json
    python scripts/vericot_check.py argument.json --json --out result.json
    python scripts/vericot_check.py --packet [--text "<原文>"] > packet.json

输入结构:
{
  "case": "案件/问题名称",
  "text": "原文（可选，用于 evidence 落地校验）",
  "variables": ["x"],
  "domain": ["甲", "乙"],
  "premises": [
    {"id": "p1", "kind": "rule", "text": "...",
     "formula": "forall x (Stacks(x) -> Liable(x))",
     "grounded": true, "source": "《民法典》第1255条",
     "evidence": "原文逐字片段"}
  ],
  "steps": [
    {"id": "s1", "rule": "subsumption", "premises": ["p1", "p2"],
     "conclusion": "c1", "formula": "Liable(甲)",
     "conclusion_text": "甲应承担侵权责任"}
  ],
  "conclusion": "c1"
}

退出码:
    0 = 校验完成（无论 valid 与否）
    2 = 输入/配置错误
"""

import argparse
import json
import os
import sys

import fol_engine as FOL

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SEVERITY_ORDER = {'critical': 0, 'major': 1, 'minor': 2, 'hint': 3}
SEVERITY_WEIGHT = {'critical': 2.0, 'major': 0.8, 'minor': 0.3, 'hint': 0.1}
SEVERITY_LABEL = {'critical': '致命', 'major': '重大', 'minor': '一般', 'hint': '提示'}
VALID_RULES = ('subsumption', 'modus_ponens', 'definition', 'analogy', 'causal')


def issue(code, severity, message, where='', fix='', **extra):
    item = {'code': code, 'severity': severity, 'message': message,
            'where': where, 'fix': fix}
    item.update(extra)
    return item


def _has_formulas(premises, steps):
    return any((p.get('formula') or '').strip() for p in premises) or \
        any((s.get('formula') or '').strip() for s in steps)


def _validate_fol(data, premises, steps, premise_ids):
    """完整版：解析 FOL、接地、DPLL 蕴涵检查。"""
    issues = []
    variables = data.get('variables') or []
    domain = data.get('domain') or []
    text = data.get('text') or ''
    formula_by_premise = {}
    formula_by_step = {}
    formula_by_conclusion = {}
    step_index = {}
    step_conclusion = {}
    trace = {'steps': [], 'consistency': None, 'final': None}

    for index, premise in enumerate(premises):
        pid = premise.get('id')
        where = 'premises[%d]' % index
        ftext = (premise.get('formula') or '').strip()
        if not ftext:
            issues.append(issue('V11', 'major', '前提缺少 formula，完整版无法校验',
                                where, '补 formula，或改用 lite 模式'))
            continue
        try:
            ast = FOL.parse_formula(ftext, variables)
            FOL.predicate_arities(ast)
        except Exception as exc:
            issues.append(issue('V10', 'critical', '公式解析失败：%s' % exc, where,
                                '检查 FOL 语法（谓词/括号/量词）'))
            continue
        if pid:
            formula_by_premise[pid] = ast
        evidence = (premise.get('evidence') or '').strip()
        if text and evidence and evidence not in text:
            issues.append(issue('V2', 'major',
                                '前提 evidence 未在原文中找到：%s' % evidence,
                                where, '改为逐字引用原文，或标为待证'))

    for index, step in enumerate(steps):
        sid = step.get('id') or ('s%d' % (index + 1))
        step_index[sid] = index
        where = 'steps[%d]' % index
        ftext = (step.get('formula') or '').strip()
        if not ftext:
            issues.append(issue('V11', 'major', '推理步骤缺少 formula，完整版无法校验',
                                where, '补 formula，或改用 lite 模式'))
            continue
        try:
            ast = FOL.parse_formula(ftext, variables)
            FOL.predicate_arities(ast)
        except Exception as exc:
            issues.append(issue('V10', 'critical', '公式解析失败：%s' % exc, where))
            continue
        formula_by_step[sid] = ast
        if step.get('conclusion'):
            formula_by_conclusion[step['conclusion']] = ast
            step_conclusion[sid] = step['conclusion']

    for index, step in enumerate(steps):
        sid = step.get('id') or ('s%d' % (index + 1))
        where = 'steps[%d]' % index
        refs = step.get('premises') or []
        cited = []
        for ref in refs:
            if ref in formula_by_premise:
                cited.append(formula_by_premise[ref])
            elif ref in formula_by_step:
                if step_index.get(ref, 10 ** 9) >= index:
                    issues.append(issue('V17', 'major',
                                        '推理步骤引用了尚未推出的步骤：%s' % ref, where,
                                        '调整步骤顺序，避免循环/前向引用'))
                else:
                    cited.append(formula_by_step[ref])
        conclusion = formula_by_step.get(sid)
        if conclusion is None or not cited:
            trace['steps'].append({'id': sid, 'status': 'skipped', 'cited': refs})
            continue
        try:
            result = FOL.entails(cited, conclusion, domain)
        except Exception as exc:
            issues.append(issue('V10', 'critical', '求解失败：%s' % exc, where))
            trace['steps'].append({'id': sid, 'status': 'error', 'cited': refs})
            continue
        trace['steps'].append({
            'id': sid, 'status': result['status'], 'cited': refs,
            'countermodel': FOL.format_model(result.get('countermodel', {}))
            if result['status'] == 'not_entailed' else None,
        })
        if result['status'] == 'not_entailed':
            issues.append(issue('V15', 'major',
                                '该步骤的结论不能由所引前提推出',
                                where, '补前提、改结论，或说明缺省推理',
                                countermodel=FOL.format_model(result.get('countermodel', {}))))
        elif result['status'] == 'undecided':
            issues.append(issue('V13', 'hint',
                                '求解未完成：%s' % result.get('reason', ''),
                                where, '缩小域/减少谓词，或人工复核'))

    # 前提一致性
    all_premises = list(formula_by_premise.values())
    if all_premises:
        try:
            sat = FOL.satisfiable(all_premises, domain)
            trace['consistency'] = sat['status']
            if sat['status'] == 'unsat':
                issues.append(issue('V14', 'critical', '前提集合不一致（无模型）',
                                    'premises', '检查规范/事实是否互相矛盾'))
            elif sat['status'] == 'undecided':
                issues.append(issue('V13', 'hint', '一致性检查未完成：%s' % sat.get('reason', ''),
                                    'premises'))
        except Exception as exc:
            issues.append(issue('V10', 'critical', '一致性求解失败：%s' % exc, 'premises'))

    # 最终结论：所有前提 + 步骤结论 是否蕴涵最终步骤公式
    final = data.get('conclusion')
    if final and final in formula_by_conclusion:
        final_sid = next((sid for sid, cid in step_conclusion.items() if cid == final), None)
        other_steps = [f for sid, f in formula_by_step.items() if sid != final_sid]
        all_formulas = list(formula_by_premise.values()) + other_steps
        try:
            result = FOL.entails(all_formulas, formula_by_conclusion[final], domain)
        except Exception as exc:
            issues.append(issue('V10', 'critical', '最终结论求解失败：%s' % exc, 'conclusion'))
            trace['final'] = {'id': final, 'status': 'error'}
        else:
            trace['final'] = {'id': final, 'status': result['status']}
            if result['status'] == 'not_entailed':
                issues.append(issue('V16', 'critical',
                                    '最终结论不能由全部前提与步骤推出',
                                    'conclusion', '补漏前提或修正结论',
                                    countermodel=FOL.format_model(result.get('countermodel', {}))))
            elif result['status'] == 'undecided':
                issues.append(issue('V13', 'hint',
                                    '最终结论求解未完成：%s' % result.get('reason', ''),
                                    'conclusion'))
    return issues, trace


def validate(data):
    premises = data.get('premises') or []
    steps = data.get('steps') or []
    issues = []
    premise_ids = {}

    if not isinstance(premises, list) or not isinstance(steps, list):
        return {
            'meta': {'tool': 'vericot_check', 'version': '0.1.0'},
            'valid': False,
            'score': 1.0,
            'issues': [issue('V0', 'critical', 'premises/steps 必须是数组')],
            'summary': {'critical': 1, 'major': 0, 'minor': 0},
        }

    for index, premise in enumerate(premises):
        where = 'premises[%d]' % index
        pid = premise.get('id')
        if not pid:
            issues.append(issue('V1', 'major', '前提缺少 id，后续步骤无法引用', where))
        elif pid in premise_ids:
            issues.append(issue('V1', 'major', '前提 id 重复：%s' % pid, where))
        else:
            premise_ids[pid] = premise
        if not (premise.get('text') or '').strip():
            issues.append(issue('V8', 'minor', '前提 text 为空', where))
        kind = premise.get('kind')
        if kind in ('rule', 'fact') and premise.get('grounded') is not True:
            issues.append(issue('V2', 'major',
                                '前提未落地（grounded 不为 true）：%s' % (pid or where),
                                where, '补法条/证据来源，或标为待证'))
        if kind not in ('rule', 'fact', 'definition'):
            issues.append(issue('V9', 'minor', '未知前提类型：%s' % kind, where))

    if not premises:
        issues.append(issue('V1', 'critical', '没有任何前提，论证无法成立', 'premises'))

    conclusion_ids = set()
    step_ids = {step.get('id') or ('s%d' % (index + 1)) for index, step in enumerate(steps)}
    for index, step in enumerate(steps):
        where = 'steps[%d]' % index
        sid = step.get('id') or ('s%d' % (index + 1))
        rule = step.get('rule')
        refs = step.get('premises') or []
        if rule not in VALID_RULES:
            issues.append(issue('V7', 'minor', '未知推理规则：%s' % rule, where))
        if not refs:
            issues.append(issue('V4', 'major', '推理步骤没有引用任何前提', where))
        for ref in refs:
            if ref not in premise_ids and ref not in step_ids:
                issues.append(issue('V3', 'critical',
                                    '推理步骤引用了不存在的前提：%s' % ref, where,
                                    '补该前提，或修正引用 id'))
        if rule in ('subsumption', 'modus_ponens') and len(refs) < 2:
            issues.append(issue('V4', 'major',
                                '%s 至少需要 2 个前提，当前只有 %d 个' % (rule, len(refs)),
                                where))
        cid = step.get('conclusion')
        if not cid:
            issues.append(issue('V5', 'major', '推理步骤没有 conclusion id', where))
        else:
            conclusion_ids.add(cid)
        if not (step.get('conclusion_text') or '').strip():
            issues.append(issue('V8', 'minor', '结论 text 为空', where))

    final = data.get('conclusion')
    if not final:
        issues.append(issue('V5', 'critical', '缺少最终 conclusion', 'conclusion'))
    elif final not in conclusion_ids:
        issues.append(issue('V5', 'critical',
                            '最终结论 %s 没有被任何推理步骤推出' % final, 'conclusion'))

    # 简单矛盾检查：最终结论/结论文本中的互斥对
    texts = []
    for step in steps:
        if step.get('conclusion_text'):
            texts.append(str(step['conclusion_text']))
    if final:
        texts.append(str(final))
    pairs = [('有效', '无效'), ('成立', '不成立'), ('有罪', '无罪'),
             ('应当', '不应当'), ('支持', '不支持')]
    joined = '\n'.join(texts)
    for pos, neg in pairs:
        if pos in joined and neg in joined:
            issues.append(issue('V6', 'major',
                                '结论中同时出现互斥表述：%s / %s' % (pos, neg),
                                'steps/conclusion', '统一结论口径，或用条件句分开'))

    mode = 'full' if _has_formulas(premises, steps) else 'lite'
    fol_trace = None
    if mode == 'full':
        fol_issues, fol_trace = _validate_fol(data, premises, steps, premise_ids)
        issues.extend(fol_issues)

    by_severity = {'critical': 0, 'major': 0, 'minor': 0, 'hint': 0}
    for item in issues:
        by_severity[item['severity']] += 1
    score = 5.0
    for item in issues:
        score -= SEVERITY_WEIGHT[item['severity']]
    if by_severity['critical']:
        score = min(score, 2.0)
    score = max(1.0, min(5.0, score))
    valid = by_severity['critical'] == 0 and by_severity['major'] == 0
    result = {
        'meta': {'tool': 'vericot_check', 'version': '1.0.0', 'mode': mode,
                 'premises': len(premises), 'steps': len(steps)},
        'valid': valid,
        'score': round(score, 1),
        'issues': sorted(issues, key=lambda x: SEVERITY_ORDER.get(x['severity'], 9)),
        'summary': by_severity,
        'note': ('完整版：FOL 解析 → 有限域接地 → DPLL 蕴涵检查。'
                 if mode == 'full' else
                 'lite 模式：只做结构校验；补 formula 后自动进入完整版。')
                + ' NL→FOL 抽取由宿主模型按 --packet 完成，不在本脚本内。',
    }
    if fol_trace is not None:
        result['fol'] = fol_trace
    return result


def build_packet(text=''):
    template = {
        'case': '',
        'text': text[:3000],
        'variables': ['x'],
        'domain': ['甲', '乙'],
        'premises': [
            {'id': 'p1', 'kind': 'rule', 'text': '规范内容',
             'formula': 'forall x (Stacks(x) -> Liable(x))',
             'grounded': True, 'source': '《民法典》第1255条',
             'evidence': '原文中支撑该规范/事实的逐字片段'},
            {'id': 'p2', 'kind': 'fact', 'text': '要件事实',
             'formula': 'Stacks(甲)',
             'grounded': True, 'source': '证据名称/编号',
             'evidence': '原文中的事实片段'},
        ],
        'steps': [
            {'id': 's1', 'rule': 'subsumption', 'premises': ['p1', 'p2'],
             'conclusion': 'c1', 'formula': 'Liable(甲)',
             'conclusion_text': '因此，甲应承担侵权责任'},
        ],
        'conclusion': 'c1',
    }
    return {
        'meta': {'tool': 'vericot_check.packet', 'version': '0.1.0'},
        'instructions': ('把原文论证拆成 premises（规范/事实/定义）与 steps（推理步骤）。'
                         '每条 rule/fact 必须 grounded=true 并给 source；能写 formula 就写，'
                         '脚本会自动进入完整版（FOL 解析 + 接地 + DPLL）；不写 formula 则只做 lite 结构校验。'
                         'formula 支持 P(a)、~、&、|、->、<->、forall x (...)、exists x (...)；'
                         '不支持函数符号与等词。conclusion 指向最终步骤 id。'),
        'text_excerpt': text[:3000],
        'template': template,
    }


def render_text(result):
    mode = result['meta'].get('mode', 'lite')
    lines = ['=' * 66, 'VeriCoT 结构化论证校验（%s）' % ('完整版' if mode == 'full' else 'lite'), '=' * 66,
             'valid: %s    逻辑分: %.1f / 5.0' % ('是' if result['valid'] else '否', result['score']),
             '前提: %d    步骤: %d' % (result['meta'].get('premises', 0), result['meta'].get('steps', 0)),
             '问题: 致命 %d / 重大 %d / 一般 %d' % (
                 result['summary']['critical'], result['summary']['major'], result['summary']['minor']),
             '-' * 66]
    if not result['issues']:
        lines.append('未发现结构化论证缺陷。')
    for item in result['issues']:
        lines.append('[%s] %s %s' % (SEVERITY_LABEL.get(item['severity'], item['severity']),
                                     item['code'], item['message']))
        if item.get('where'):
            lines.append('  位置: %s' % item['where'])
        if item.get('countermodel'):
            lines.append('  反例模型: %s' % item['countermodel'])
        if item.get('fix'):
            lines.append('  修正: %s' % item['fix'])
    fol = result.get('fol')
    if fol:
        lines.append('-' * 66)
        lines.append('步骤校验：')
        for step in fol.get('steps', []):
            extra = ('  反例: %s' % step['countermodel']) if step.get('countermodel') else ''
            lines.append('  %-8s %-10s 引用 %s%s' % (
                step.get('id', '?'), step.get('status', '?'),
                ','.join(step.get('cited', [])), extra))
        if fol.get('consistency'):
            lines.append('  前提一致性: %s' % fol['consistency'])
        if fol.get('final'):
            lines.append('  最终结论: %s (%s)' % (fol['final'].get('id'), fol['final'].get('status')))
    lines.append('=' * 66)
    lines.append(result.get('note', ''))
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='VeriCoT：结构化法律论证的符号校验（FOL + 有限域 DPLL；不做 NL→FOL 抽取）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python scripts/vericot_check.py argument.json\n'
               '  python scripts/vericot_check.py argument.json --json --out result.json\n'
               '  python scripts/vericot_check.py --packet --text "本案中……"',
    )
    parser.add_argument('file', nargs='?', help='结构化论证 JSON')
    parser.add_argument('--packet', action='store_true', help='输出抽取模板（交给宿主模型）')
    parser.add_argument('--text', help='原文（仅用于 packet 展示）')
    parser.add_argument('--json', action='store_true', dest='as_json', help='输出 JSON')
    parser.add_argument('--out', help='写入 JSON 文件')
    args = parser.parse_args(argv)

    if args.packet:
        packet = build_packet(args.text or '')
        if args.as_json:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
        return 0

    if not args.file:
        print('错误：请提供结构化论证 JSON，或使用 --packet。', file=sys.stderr)
        return 2
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as exc:
        msg = '错误：无法读取/解析 JSON（%s）' % exc
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    result = validate(data)
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
