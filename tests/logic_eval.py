#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逻辑体检的固定样本校准（合成 fixture，不是真人标注基准）

运行:
    python tests/logic_eval.py

输出:
    clean_fp_rate        干净样本误报率
    expected_recall      期望检查的召回率
    extra_issue_rate     正样本上的额外命中率（用于观察误报）
    major_error_free_rate 干净样本的逻辑重大错误自由率
    per_check            各检查的期望/命中数
"""

import json
import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'tests'))

import logic_linter as L  # noqa: E402
import logic_fixtures as F  # noqa: E402


def evaluate():
    tax, rub = L.load_taxonomy(), L.load_rubric()
    clean_total = clean_fp = 0
    expected_total = expected_hit = extra = detected_positive = 0
    major_free = 0
    per_check = {}
    rows = []
    for fixture in F.FIXTURES:
        result = L.lint_text(fixture['text'], tax, rub)
        detected = {i['check_id'] for i in result['issues']}
        expected = set(fixture.get('expected', []))
        if fixture.get('clean'):
            clean_total += 1
            if detected:
                clean_fp += 1
            if result['summary']['logic_major_error_free']:
                major_free += 1
        else:
            detected_positive += 1
            expected_total += len(expected)
            expected_hit += len(expected & detected)
            extra += len(detected - expected)
        for check_id in expected | detected:
            per_check.setdefault(check_id, {'expected': 0, 'hit': 0, 'extra': 0})
            if check_id in expected:
                per_check[check_id]['expected'] += 1
                if check_id in detected:
                    per_check[check_id]['hit'] += 1
            if check_id in detected and check_id not in expected:
                per_check[check_id]['extra'] += 1
        rows.append({
            'id': fixture['id'],
            'detected': sorted(detected),
            'expected': sorted(expected),
            'score': result['summary']['logic_score'],
        })
    return {
        'fixtures': len(F.FIXTURES),
        'clean_total': clean_total,
        'clean_false_positive_rate': round(clean_fp / clean_total, 3) if clean_total else None,
        'expected_recall': round(expected_hit / expected_total, 3) if expected_total else None,
        'extra_issue_rate': round(extra / detected_positive, 3) if detected_positive else None,
        'major_error_free_rate': round(major_free / clean_total, 3) if clean_total else None,
        'per_check': per_check,
        'rows': rows,
        'note': '合成 fixture 的校准结果，不代表真实分布；真实基准需 50–100 条双人标注。',
    }


def main():
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
