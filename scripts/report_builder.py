#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告构建器 (Report Builder) — LegalGuardian v5.0.0

一键串联全链路引擎（检测→纠正→安全→评分→作业评估→提问优化→案例检索→三维规制→逻辑体检），
输出统一结构的 JSON 报告，供 panel/report_panel.html 可视化展示（路演/评审用）。

用法:
    python scripts/report_builder.py <输入文本文件> [--name <工具名>] [--query "<检索词>"]
                                     [--question "<原始提问>"] [--modules a,b,c] [--out <路径>]
    python scripts/report_builder.py --text "<AI回答内容>" --query "民间借贷 利息" --out panel/demo_report.json

模块过滤: --modules detection,corrections,safety,scoring,assignment,templates,retrieval,regulation,logic

输出: JSON — {meta, input, modules:{...}}，各模块字段与对应脚本 CLI 输出一致。
"""

import sys
import json
import os
import datetime

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

ALL_MODULES = ['detection', 'corrections', 'safety', 'scoring',
               'assignment', 'templates', 'retrieval', 'regulation', 'logic']


def build_report(text: str, name: str = '', query: str = '', question: str = '',
                 modules: list = None) -> dict:
    """执行全链路检测并汇总为统一报告"""
    modules = modules or ALL_MODULES
    m = {}

    # 1. 失效模式检测
    if 'detection' in modules:
        from failure_detector import detect_all
        m['detection'] = detect_all(text)

    detection = m.get('detection')

    # 2. 纠正建议
    if 'corrections' in modules:
        from correction_engine import generate_all_corrections
        m['corrections'] = generate_all_corrections(detection or {})

    # 3. 安全检查
    if 'safety' in modules:
        from safety_checker import run_safety_checks
        m['safety'] = run_safety_checks(text, detection)

    # 4. 四维评分
    if 'scoring' in modules:
        from scoring_engine import score_all
        m['scoring'] = score_all(text, detection)

    # 5. 作业评估（8题型）
    if 'assignment' in modules:
        from law_assignment_evaluator_v2 import evaluate_assignment_v2
        m['assignment'] = evaluate_assignment_v2(text)

    # 6. 提问优化（用原始提问；未提供时退化为整段文本）
    if 'templates' in modules:
        from template_matcher import (load_templates, load_legal_knowledge,
                                      analyze_question, match_templates,
                                      generate_optimized_question)
        tpl_data = load_templates()
        legal_kb = load_legal_knowledge()
        q = question or text[:200]
        analysis = analyze_question(q, tpl_data, legal_kb)
        recs = match_templates(analysis, tpl_data)
        optimized = generate_optimized_question(q, analysis, recs, tpl_data, legal_kb)
        m['templates'] = {
            'question': q,
            'analysis': analysis,
            'recommended_template_ids': recs,
            'optimized': optimized,
        }

    # 7. 案例检索（5,515 案例库）
    if 'retrieval' in modules:
        from rag_retriever import retrieve
        q = query or question or text[:80]
        m['retrieval'] = retrieve(q, top_k=5, with_detail=True)

    # 8. 三维规制评估
    if 'regulation' in modules:
        from regulation_assessor import assess
        m['regulation'] = assess(text, name, detection)

    # 9. 逻辑体检（5×4 矩阵 + 8 项确定性筛查）
    if 'logic' in modules:
        from logic_linter import lint_text
        m['logic'] = lint_text(text)

    return {
        'meta': {
            'builder': 'report_builder v5.0.0',
            'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tool_name': name,
            'input_source': 'text',
            'text_length': len(text),
            'modules_included': sorted(m.keys()),
        },
        'input': {
            'text': text,
            'question': question,
            'query': query,
        },
        'modules': m,
    }


def read_input(path: str) -> str:
    """读取输入文件（.md/.txt/.json——JSON 取 ai_response 字段）"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if path.endswith('.json'):
        try:
            data = json.loads(content)
            if isinstance(data, dict) and data.get('ai_response'):
                return data['ai_response']
        except Exception:
            pass
    return content


def main():
    args = sys.argv[1:]
    text = None
    name = ''
    query = ''
    question = ''
    modules = None
    out = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--text' and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        elif arg == '--name' and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        elif arg == '--query' and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        elif arg == '--question' and i + 1 < len(args):
            question = args[i + 1]
            i += 2
        elif arg == '--modules' and i + 1 < len(args):
            modules = [x.strip() for x in args[i + 1].split(',') if x.strip()]
            i += 2
        elif arg == '--out' and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif arg.startswith('--'):
            i += 1
        elif text is None and os.path.exists(arg):
            text = read_input(arg)
            i += 1
        else:
            i += 1

    if not text:
        print(json.dumps({'error': '用法: report_builder.py <输入文件> | --text "<内容>" [--query ..] [--modules ..] [--out ..]'}, ensure_ascii=False))
        sys.exit(1)

    report = build_report(text, name, query, question, modules)
    if out:
        out_dir = os.path.dirname(os.path.abspath(out))
        os.makedirs(out_dir, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(json.dumps({'ok': True, 'output': os.path.abspath(out),
                          'modules': report['meta']['modules_included']}, ensure_ascii=False))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
