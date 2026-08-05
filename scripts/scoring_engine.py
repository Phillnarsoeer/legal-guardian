#!/usr/bin/env python3
"""
四维评分引擎 (Scoring Engine)

按准确性/时效性/逻辑性/引导性四个维度对AI回复进行评分，
评分标准参照实证测试的1-5分制，输出与DeepSeek/千问baseline的对比。

用法:
    python scoring_engine.py <AI回复文本文件路径>
    python scoring_engine.py --text "AI回复文本"
    python failure_detector.py input.txt | python correction_engine.py --stdin | python scoring_engine.py --stdin-detection

输出: JSON格式的四维评分 + baseline对比
"""

import sys
import json
import os
import re

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def load_baseline() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_path = os.path.join(script_dir, '..', 'reference', 'test_baseline.json')
    if not os.path.exists(baseline_path):
        raise FileNotFoundError(f'基线文件不存在: {baseline_path}')
    try:
        with open(baseline_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f'基线文件解析失败: {baseline_path} ({e})') from e


def score_accuracy(text: str) -> dict:
    """评分维度：准确性 (1-5)"""
    score = 4.0  # 默认基准

    # 加分项
    bonuses = 0
    if any(phrase in text for phrase in ['根据《民法典》', '根据《中华人民共和国刑法》', '现行有效']):
        bonuses += 0.5
    if re.search(r'第[一二三四五六七八九十百千万0-9]+条', text):
        bonuses += 0.3
    if re.search(r'(?:生效|施行|修订).*(?:\d{4})', text):
        bonuses += 0.2

    # 扣分项
    penalties = 0
    if any(law in text for law in ['《民法通则》', '《经济合同法》', '《治安管理处罚条例》']):
        has_correction = any(phrase in text for phrase in ['已废止', '已被取代', '已失效'])
        if not has_correction:
            penalties += 2.0  # 未纠正已废止法律

    # 精确度调整
    score = max(1.0, min(5.0, score + bonuses - penalties))

    return {
        'score': round(score, 1),
        'bonuses': f'+{bonuses}',
        'penalties': f'-{penalties}' if penalties > 0 else '0',
        'assessment': (
            '优秀' if score >= 4.5 else
            '良好' if score >= 3.5 else
            '一般' if score >= 2.5 else
            '不足'
        )
    }


def score_timeliness(text: str) -> dict:
    """评分维度：时效性 (1-5)"""
    score = 4.0

    bonuses = 0
    has_latest_revision = any(phrase in text for phrase in
        ['最新修订', '最新版本', '最近修订', '现行有效', '2023', '2024', '2025', '2026'])
    has_validity_check = any(phrase in text for phrase in
        ['经查询', '经核实', '经检索', '经确认'])

    if has_latest_revision:
        bonuses += 0.5
    if has_validity_check:
        bonuses += 0.5

    penalties = 0
    if any(law in text for law in ['《民法通则》']):
        has_replacement_note = '民法典' in text
        if not has_replacement_note:
            penalties += 1.5

    score = max(1.0, min(5.0, score + bonuses - penalties))

    return {
        'score': round(score, 1),
        'bonuses': f'+{bonuses}',
        'penalties': f'-{penalties}' if penalties > 0 else '0',
        'assessment': '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '一般'
    }


def score_logic(text: str) -> dict:
    """评分维度：逻辑性 (1-5)"""
    score = 3.5

    bonuses = 0
    has_structure = any(phrase in text for phrase in ['首先', '其次', '再次', '最后'])
    has_syllogism = all(phrase in text for phrase in ['法律依据', '案情分析']) or \
                   all(phrase in text for phrase in ['大前提', '小前提', '结论'])
    has_multi_perspective = any(phrase in text for phrase in ['控方', '辩方', '角度', '替代', '也可能'])
    has_depth = any(phrase in text for phrase in ['法理', '学说', '争议', '例外', '特别规范'])

    if has_structure: bonuses += 0.3
    if has_syllogism: bonuses += 0.5
    if has_multi_perspective: bonuses += 0.5
    if has_depth: bonuses += 0.5

    penalties = 0
    if len(text) > 500:
        has_shallow_signal = any(s in text for s in ['综上所述', '因此答案是']) and not has_depth
        if has_shallow_signal:
            penalties += 1.0

    score = max(1.0, min(5.0, score + bonuses - penalties))

    return {
        'score': round(score, 1),
        'bonuses': f'+{bonuses}',
        'penalties': f'-{penalties}' if penalties > 0 else '0',
        'assessment': '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '一般' if score >= 2.5 else '不足'
    }


def score_guidance(text: str) -> dict:
    """评分维度：引导性 (1-5)"""
    score = 2.0  # 引导性是普遍弱点，从较低基准开始

    guidance_elements = {
        'evidence_list': ['证据', '收集', '举证', '证据清单', '需要准备', '公证'],
        'procedure_steps': ['步骤', '流程', '第一步', '先', '然后', '操作'],
        'timeline': ['时效', '期限', '时间节点', '天内', '日内', '之日起'],
        'risk_warning': ['风险', '警示', '注意', '免责', '不构成法律意见', '仅供参考'],
        'alternatives': ['协商', '调解', '仲裁', '替代', '和解', '其他途径'],
        'lawyer_referral': ['咨询律师', '持证律师', '法律意见', '专业人士']
    }

    found_count = 0
    for element, patterns in guidance_elements.items():
        if any(p in text for p in patterns):
            found_count += 1

    # 每找到一个引导性要素加0.5分
    score = min(5.0, 2.0 + found_count * 0.5)

    # 特殊加分：有完整的实务操作指引
    has_complete_guidance = found_count >= 5
    if has_complete_guidance:
        score = min(5.0, score + 0.5)

    return {
        'score': round(score, 1),
        'elements_found': found_count,
        'elements_total': 6,
        'assessment': (
            '优秀' if score >= 4.5 else
            '良好' if score >= 3.5 else
            '一般' if score >= 2.5 else
            '不足'
        ),
        'improvement_tip': (
            '引导性已达优秀水平' if score >= 4.5 else
            '建议补充风险提示和律师咨询建议' if score < 3.0 else
            '可进一步提升证据建议和替代方案的完整性'
        )
    }


def score_all(text: str, failure_detection: dict = None) -> dict:
    """执行四维评分并生成对比报告"""
    baseline = load_baseline()

    dimensions = {
        '准确性': score_accuracy(text),
        '时效性': score_timeliness(text),
        '逻辑性': score_logic(text),
        '引导性': score_guidance(text)
    }

    # 如果有失效模式检测结果，对相应维度进行调降
    if failure_detection:
        dimension_mapping = {
            '准确性': ['F1', 'F2', 'F3', 'F7'],
            '时效性': ['F1', 'F5'],
            '逻辑性': ['F4', 'F7', 'F8'],
            '引导性': ['F6', 'F9', 'F10']
        }
        detections = failure_detection.get('detections', {})
        for dim, related_failures in dimension_mapping.items():
            fired_count = sum(1 for fid in related_failures if detections.get(fid, {}).get('fired'))
            if fired_count > 0:
                penalty = min(fired_count * 0.5, 2.0)
                final_score = max(1.0, dimensions[dim]['score'] - penalty)
                dimensions[dim]['score'] = final_score
                dimensions[dim]['failure_penalty'] = f'-{penalty} ({fired_count}个相关失效模式)'
                # 扣分后重新计算评估标签（与score_accuracy等保持一致阈值）
                dimensions[dim]['assessment'] = (
                    '优秀' if final_score >= 4.5 else
                    '良好' if final_score >= 3.5 else
                    '一般' if final_score >= 2.5 else
                    '不足'
                )

    # 计算总平均和评级
    scores = [d['score'] for d in dimensions.values()]
    overall = round(sum(scores) / len(scores), 2)
    overall_grade = 'A' if overall >= 4.0 else 'B' if overall >= 3.0 else 'C' if overall >= 2.0 else 'D'

    # 与baseline对比
    baseline_scores = baseline.get('baseline_scores', {})
    ds_baseline = baseline_scores.get('deepseek')
    qw_baseline = baseline_scores.get('qwen')
    if not isinstance(ds_baseline, dict) or not isinstance(qw_baseline, dict):
        raise ValueError('基线文件缺少 baseline_scores.deepseek/qwen 字段')

    comparison = {
        'vs_deepseek': {
            'accuracy_diff': round(dimensions['准确性']['score'] - ds_baseline['accuracy'], 1),
            'timeliness_diff': round(dimensions['时效性']['score'] - ds_baseline['timeliness'], 1),
            'logic_diff': round(dimensions['逻辑性']['score'] - ds_baseline['logic'], 1),
            'guidance_diff': round(dimensions['引导性']['score'] - ds_baseline['guidance'], 1),
            'overall_diff': round(overall - ds_baseline['overall'], 2),
            'ds_overall': ds_baseline['overall']
        },
        'vs_qwen': {
            'accuracy_diff': round(dimensions['准确性']['score'] - qw_baseline['accuracy'], 1),
            'timeliness_diff': round(dimensions['时效性']['score'] - qw_baseline['timeliness'], 1),
            'logic_diff': round(dimensions['逻辑性']['score'] - qw_baseline['logic'], 1),
            'guidance_diff': round(dimensions['引导性']['score'] - qw_baseline['guidance'], 1),
            'overall_diff': round(overall - qw_baseline['overall'], 2),
            'qw_overall': qw_baseline['overall']
        },
        'guidance_weakest_note': '引导性是AI法律工具中最薄弱维度（DS平均2.96, 千问平均1.70），R2角色扮演可提升40%'
    }

    return {
        'meta': {
            'text_length': len(text),
            'scoring_system': '四维1-5分制，锚定于14案例实证基线',
            'overall_score': overall,
            'overall_grade': overall_grade
        },
        'dimensions': dimensions,
        'comparison': comparison,
        'baseline_reference': f'DeepSeek综合{ds_baseline["overall"]}，千问综合{qw_baseline["overall"]}'
    }


def main():
    text = None
    failure_detection = None

    if len(sys.argv) >= 2:
        if sys.argv[1] == '--stdin-detection':
            data = json.loads(sys.stdin.read())
            if 'text' in data:
                text = data['text']
            if 'detections' in data or 'all_detections' in data:
                failure_detection = data
        elif sys.argv[1] == '--stdin':
            text = sys.stdin.read()
        elif sys.argv[1] == '--text' and len(sys.argv) >= 3:
            text = sys.argv[2]
        else:
            filepath = sys.argv[1]
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()

    if not text:
        print(json.dumps({'error': '未提供文本'}, ensure_ascii=False))
        sys.exit(1)

    try:
        results = score_all(text, failure_detection)
    except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(json.dumps({'error': f'评分失败: {e}'}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
