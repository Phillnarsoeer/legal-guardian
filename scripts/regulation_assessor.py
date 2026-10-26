#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三维规制符合性评估器 (Regulation Assessor) — LegalGuardian v5.0.0

落地 SKILL.md 模块 D：对 AI 法律工具/Skill 做 技术(T1-T5)/教育(E1-E4)/
法律(L1-L4) 三维规制符合性评估，输出逐项状态 + 维度得分 + 改进路线图。

判定依据（确定性规则，竞赛铁律：可复现）:
    1) 联动失效模式检测：传入 --detections 时，条目 target_failures 中
       任一模式命中 ⇒ 该项直接判 FAIL（实证证据优先）；
    2) 关键词证据：工具描述文本命中条目关键词 ⇒ PASS；
    3) 均不满足 ⇒ PENDING（待人工核验）。

用法:
    python regulation_assessor.py --text "<AI法律工具功能描述>" [--name <工具名>]
    python regulation_assessor.py --text "<功能描述>" --detections <检测结果JSON>
    python regulation_assessor.py --list           # 列出全部条目与关键词

输出: JSON — 三维逐项评估 + 维度雷达数据 + 路线图
"""

import sys
import json
import os

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REGULATION_PATH = os.path.join(_SCRIPT_DIR, '..', 'reference', 'three_d_regulation.json')

# 各条目中文证据关键词（与英文条目名/评估标准对应）
EVIDENCE_KEYWORDS = {
    'T1': ['法条验证', '法律检索', '法规核查', '现行有效', '法条存在性', '检索验证', '法律法规数据库', '效力核验', '法条引用校验', '条文校验'],
    'T2': ['争议标注', '替代分析', '多罪名', '控方', '辩方', '另一种可能', '争议性定性', '替代罪名', '不同定性', '多角度'],
    'T3': ['置信度', '不确定性', '误差区间', '预测区间', '仅供参考', '量刑区间', '历史案例', '误差范围', '概率披露'],
    'T4': ['计算验证', '利息计算', 'LPR', '核算', '复算', '验算', '计算一致性', '多步验证'],
    'T5': ['用户类型', '法学生', '非专业人士', '通俗解释', '风险提示', '律师建议', '差异化输出', '分众'],
    'E1': ['AI素养', '素养课程', '人工智能教育', 'AI教育', '素养教育', '课程体系'],
    'E2': ['律师培训', '执业培训', '继续教育', '实务培训', '法律职业培训'],
    'E3': ['科普', '普法', '公众教育', '法治宣传', '公众科普'],
    'E4': ['模板', '标准化提问', '提问模板', '提示词模板', '标准模板'],
    'L1': ['认证', '分级认证', '备案', '准入', '资质'],
    'L2': ['透明', '披露', '公示', '可解释', '透明度', '说明义务'],
    'L3': ['伦理', '守则', '准则', '职业道德', '合规', '道德'],
    'L4': ['沙盒', '监管沙盒', '试点', '测试环境', '白名单', '监管'],
}


def load_regulation() -> dict:
    with open(_REGULATION_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_detections(path: str) -> dict:
    """加载失效模式检测结果 JSON；解析失败返回空（不阻断评估）"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def fired_patterns(detections: dict) -> set:
    """从检测结果提取命中的模式编号集合"""
    fired = set()
    if not detections:
        return fired
    for pid, detail in detections.get('detections', {}).items():
        if isinstance(detail, dict) and detail.get('fired'):
            fired.add(pid)
    # 兼容直接以 {F1: {...}} 作为 detections 的输入
    for pid, detail in detections.items():
        if isinstance(detail, dict) and detail.get('fired') and pid.startswith('F'):
            fired.add(pid)
    return fired


def assess_item(item_id: str, item: dict, text: str, fired: set) -> dict:
    """单条目评估：实证证据优先，其次关键词证据，均无则待核"""
    target = item.get('target_failures', []) or []
    fired_hits = [f for f in target if f in fired]
    if fired_hits:
        return {
            'id': item_id,
            'name': item.get('name', ''),
            'status': 'FAIL',
            'basis': '实证证据',
            'evidence': f'失效模式 {", ".join(fired_hits)} 命中（工具存在对应风险）',
            'evaluation_criteria': item.get('evaluation_criteria') or '',
        }
    keywords = EVIDENCE_KEYWORDS.get(item_id, [])
    hits = [k for k in keywords if k in text]
    if hits:
        return {
            'id': item_id,
            'name': item.get('name', ''),
            'status': 'PASS',
            'basis': '关键词证据',
            'evidence': f'命中关键词: {", ".join(hits)}',
            'evaluation_criteria': item.get('evaluation_criteria') or '',
        }
    return {
        'id': item_id,
        'name': item.get('name', ''),
        'status': 'PENDING',
        'basis': '无证据',
        'evidence': '描述中未检索到对应证据，需人工核验',
        'evaluation_criteria': item.get('evaluation_criteria') or '',
    }


def assess(text: str, tool_name: str = '', detections: dict = None) -> dict:
    regulation = load_regulation()
    fired = fired_patterns(detections or {})
    dimensions = regulation['dimensions']

    dim_results = {}
    for dim_key, dim_data in dimensions.items():
        items = dim_data.get('items', {})
        assessed = [assess_item(iid, it, text, fired) for iid, it in items.items()]
        passed = sum(1 for a in assessed if a['status'] == 'PASS')
        failed = sum(1 for a in assessed if a['status'] == 'FAIL')
        dim_results[dim_key] = {
            'name': dim_data.get('name', dim_key),
            'total': len(assessed),
            'pass': passed,
            'fail': failed,
            'pending': len(assessed) - passed - failed,
            'score': round(passed / len(assessed), 2) if assessed else 0.0,
            'items': assessed,
        }

    total_items = sum(d['total'] for d in dim_results.values())
    total_pass = sum(d['pass'] for d in dim_results.values())
    total_fail = sum(d['fail'] for d in dim_results.values())
    overall = round(total_pass / total_items, 2) if total_items else 0.0
    if overall >= 0.8 and total_fail == 0:
        grade = 'A (高合规)'
    elif overall >= 0.6:
        grade = 'B (基本合规)'
    elif overall >= 0.4:
        grade = 'C (需改进)'
    else:
        grade = 'D (低合规)'

    return {
        'meta': {
            'assessor_version': '5.0.0',
            'tool_name': tool_name,
            'regulation_source': regulation.get('meta', {}).get('source', ''),
            'detections_loaded': bool(detections),
            'fired_patterns': sorted(fired),
            'deterministic': True,
        },
        'dimensions': dim_results,
        'radar': {k: {'score': v['score'], 'pass': v['pass'], 'total': v['total']} for k, v in dim_results.items()},
        'overall': {
            'score': overall,
            'pass': total_pass,
            'fail': total_fail,
            'pending': total_items - total_pass - total_fail,
            'total': total_items,
            'grade': grade,
        },
        'roadmap': regulation.get('roadmap', {}),
    }


def main():
    args = sys.argv[1:]
    text = None
    tool_name = ''
    detections_path = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--text' and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        elif arg == '--name' and i + 1 < len(args):
            tool_name = args[i + 1]
            i += 2
        elif arg == '--detections' and i + 1 < len(args):
            detections_path = args[i + 1]
            i += 2
        elif arg == '--list':
            regulation = load_regulation()
            listing = {}
            for dim_key, dim_data in regulation['dimensions'].items():
                listing[dim_key] = {
                    'items': {iid: {
                        'name': it.get('name', ''),
                        'target_failures': it.get('target_failures', []),
                        'evidence_keywords': EVIDENCE_KEYWORDS.get(iid, []),
                    } for iid, it in dim_data.get('items', {}).items()}
                }
            print(json.dumps({'meta': {'assessor_version': '5.0.0'}, 'dimensions': listing}, ensure_ascii=False, indent=2))
            sys.exit(0)
        else:
            i += 1

    if not text:
        print(json.dumps({
            'error': '用法: python regulation_assessor.py --text "<AI法律工具功能描述>" [--name <工具名>] [--detections <检测JSON>] | --list'
        }, ensure_ascii=False))
        sys.exit(1)

    detections = load_detections(detections_path) if detections_path else None
    result = assess(text, tool_name, detections)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

