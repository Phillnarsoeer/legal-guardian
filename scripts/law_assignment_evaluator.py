#!/usr/bin/env python3
"""
法学作业评估与评分器 (Law Assignment Evaluator)

对法学作业（案例分析/论文/法律意见书等）进行五维结构化评估与百分制评分。
评估标准基于 reference/assignment_rubric.json，同时调用失效模式检测器
来识别作业中可能存在的24种失效模式（F1-F24）。

用法:
    python law_assignment_evaluator.py <作业文件路径> [--course <课程类型>]
    python law_assignment_evaluator.py --text "作业内容" --course case_analysis

支持格式: .md, .txt, .docx
"""

import sys
import json
import os
import re
import datetime
from functools import lru_cache

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


@lru_cache(maxsize=None)
def load_rubric() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rubric_path = os.path.join(script_dir, '..', 'reference', 'assignment_rubric.json')
    with open(rubric_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_assignment(filepath: str) -> str:
    """读取作业文件（支持.md/.txt/.docx）"""
    if filepath.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(filepath)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            # 缺少 python-docx 或文件损坏时返回 None，由调用方(main)输出明确的JSON错误
            return None
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()


def run_failure_detection(text: str) -> dict:
    """调用failure_detector.py检测作业中的失效模式（进程内调用，避免命令行长度限制与启动开销）"""
    try:
        from failure_detector import detect_all
        return detect_all(text)
    except Exception as e:
        print(f'[warning] 失效模式检测失败: {e}', file=sys.stderr)
        return {}


# 条款号正则（模块级复用，避免每次重复编译）
ARTICLE_PATTERN = re.compile(r'第[一二三四五六七八九十百千\d]+条')


def evaluate_dimension_1_accuracy(text: str, rubric: dict) -> dict:
    """评估维度1：法律依据准确性 (30%)"""
    dim = rubric['dimensions'][0]

    score = 3.0  # 默认及格线
    issues = []
    has_articles = False

    # 检查是否有法律引用
    law_pattern = re.compile(r'《([^》]+)》')
    laws_found = law_pattern.findall(text)

    if not laws_found:
        score = 2.0
        issues.append('作业中未发现任何法律引用')
    else:
        # 检查引用质量（子串包含匹配，完整标题如"中华人民共和国民法通则"也能命中）
        repealed_laws = ['民法通则', '经济合同法', '治安管理处罚条例']
        has_repealed = any(short in law_name for law_name in laws_found for short in repealed_laws)

        if has_repealed:
            # 红线：引用已废止法律，直接0分并跳过所有加分
            score = 0
            issues.append('🔴 红线触发：引用了已废止法律。直接0分')
            issues.append('由于引用已废止法律，该维度直接计0分。无论其他维度得分如何，总分将受到严重影响。')
            weighted = round(score * dim['weight'] / 5.0, 1)
            red_desc = rubric['grade_mapping']['不及格']['description']
            return {
                'score': 0,
                'weighted_contribution': f'{weighted}/{dim["weight"]}',
                'issues': issues,
                'laws_found': laws_found,
                'articles_found': False,
                'assessment': red_desc if len(red_desc) <= 30 else red_desc[:30] + '...'
            }

        # 检查是否有条款号
        has_articles = bool(ARTICLE_PATTERN.findall(text))

        if has_articles:
            score = min(5.0, score + 1.0)
        else:
            issues.append('法律引用未标注具体条款号')

        # 检查是否有现行有效性标注
        has_validity = any(phrase in text for phrase in ['现行有效', '生效日期', '修订', '施行'])
        if has_validity:
            score = min(5.0, score + 0.5)

        # 引用数量加分
        if len(laws_found) >= 3:
            score = min(5.0, score + 0.5)

    weighted = round(score * dim['weight'] / 5.0, 1)
    description = rubric['grade_mapping'][
        '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '中等' if score >= 2.5 else '不及格'
    ]['description']

    return {
        'score': max(0, score),
        'weighted_contribution': f'{weighted}/{dim["weight"]}',
        'issues': issues,
        'laws_found': laws_found,
        'articles_found': has_articles,
        'assessment': description if len(description) <= 30 else description[:30] + '...'
    }


def evaluate_dimension_2_logic(text: str, rubric: dict) -> dict:
    """评估维度2：论证逻辑严密性 (25%)"""
    dim = rubric['dimensions'][1]

    score = 3.0
    issues = []

    # 检查三段论结构
    has_major_premise = any(phrase in text for phrase in ['根据《', '依据《', '按照《', '法律规定'])
    has_minor_premise = any(phrase in text for phrase in ['本案', '本案中', '案情', '事实', '证据'])
    has_conclusion = any(phrase in text for phrase in ['因此', '综上所述', '综上', '故', '所以', '应认定'])

    syllogism_score = sum([has_major_premise, has_minor_premise, has_conclusion])

    if syllogism_score == 3:
        score = min(5.0, score + 1.5)
    elif syllogism_score == 2:
        score = min(5.0, score + 0.5)
    elif syllogism_score <= 1:
        score -= 1.0
        issues.append('缺少完整的三段论结构（大前提→小前提→结论）')

    # 检查多角度分析
    has_multi_perspective = any(phrase in text for phrase in ['替代', '另一种可能是', '也可能', '不同观点', '争议'])
    if has_multi_perspective:
        score = min(5.0, score + 0.5)
    else:
        issues.append('建议增加替代法律理论或不同角度的分析')

    # 检查因果分析深度
    has_deep_causal = any(phrase in text for phrase in ['多因', '共同', '先行行为', '不作为', '义务', '举证责任'])
    if has_deep_causal:
        score = min(5.0, score + 0.5)

    weighted = round(max(0, score) * dim['weight'] / 5.0, 1)

    return {
        'score': round(max(0, score), 1),
        'weighted_contribution': f'{weighted}/{dim["weight"]}',
        'issues': issues,
        'syllogism_completeness': f'{syllogism_score}/3',
        'assessment': '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '中等' if score >= 2.5 else '不足'
    }


def evaluate_dimension_3_depth(text: str, rubric: dict) -> dict:
    """评估维度3：法理深度 (20%)"""
    dim = rubric['dimensions'][2]

    score = 2.5
    issues = []

    depth_indicators = {
        'legislative_purpose': ['立法目的', '立法背景', '立法精神', '立法宗旨'],
        'academic_discussion': ['学说', '学界', '通说', '主流观点', '学者', '认为'],
        'comparative_law': ['比较法', '域外', '大陆法系', '英美法系', '国外', '国际'],
        'case_reference': ['案例', '判例', '指导性案例', '典型案例']
    }

    found = 0
    for category, patterns in depth_indicators.items():
        if any(p in text for p in patterns):
            found += 1

    score += found * 0.5

    if found == 0:
        issues.append('作业缺乏法理深度的探讨，建议增加学理分析、比较法参考或典型案例引用')
    elif found == 1:
        issues.append('法理分析较为浅显，建议增加更多维度的深度分析')

    score = min(5.0, score)
    weighted = round(score * dim['weight'] / 5.0, 1)

    return {
        'score': round(score, 1),
        'weighted_contribution': f'{weighted}/{dim["weight"]}',
        'depth_dimensions_covered': f'{found}/4',
        'issues': issues,
        'assessment': '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '中等' if score >= 2.5 else '不足'
    }


def evaluate_dimension_4_practicality(text: str, rubric: dict) -> dict:
    """评估维度4：实务操作性 (15%)"""
    dim = rubric['dimensions'][3]

    score = 2.0
    issues = []

    practical_elements = {
        'evidence': ['证据', '举证', '收集', '公证', '证人'],
        'procedure': ['步骤', '流程', '程序', '起诉', '立案', '开庭'],
        'timeline': ['时效', '期限', '时间', '天数', '日期'],
        'risk': ['风险', '警示', '注意', '最坏情况', '不利后果'],
        'alternative': ['协商', '调解', '仲裁', '和解', 'ADR', '替代方案']
    }

    found = 0
    for category, patterns in practical_elements.items():
        if any(p in text for p in patterns):
            found += 1

    score += found * 0.6

    if found <= 2:
        issues.append('实务操作性较弱，建议补充证据收集指引、操作步骤和风险提示')

    score = min(5.0, score)
    weighted = round(score * dim['weight'] / 5.0, 1)

    return {
        'score': round(score, 1),
        'weighted_contribution': f'{weighted}/{dim["weight"]}',
        'practical_elements_found': f'{found}/5',
        'issues': issues,
        'assessment': '优秀' if score >= 4.5 else '良好' if score >= 3.5 else '一般'
    }


def evaluate_dimension_5_academic_norms(text: str, rubric: dict) -> dict:
    """评估维度5：学术规范 (10%)"""
    dim = rubric['dimensions'][4]

    score = 3.5
    issues = []

    # 检查结构完整性
    has_structure = all(any(s in text for s in signals)
                       for signals in [['摘要', '引言', '背景'],
                                      ['正文', '分析', '论证'],
                                      ['结论', '综上', '总结']])

    has_references = any(phrase in text for phrase in ['参考文献', '引用', '参见', '转引自'])

    if not has_structure:
        score -= 1.0
        issues.append('作业结构不完整，建议包含摘要-引言-正文-结论-参考文献')

    if not has_references:
        score -= 0.5
        issues.append('缺少参考文献或引用来源标注')

    score = max(1.0, min(5.0, score))
    weighted = round(score * dim['weight'] / 5.0, 1)

    return {
        'score': round(score, 1),
        'weighted_contribution': f'{weighted}/{dim["weight"]}',
        'issues': issues,
        'assessment': '良好' if score >= 4.0 else '一般' if score >= 3.0 else '不足'
    }


def evaluate_assignment(text: str, course_type: str = 'general') -> dict:
    """对法学作业进行全面评估"""
    rubric = load_rubric()

    # 1. 运行失效模式检测
    failure_detection = run_failure_detection(text)

    # 2. 五维评分
    dimensions = {
        'D1_法律依据准确性': evaluate_dimension_1_accuracy(text, rubric),
        'D2_论证逻辑严密性': evaluate_dimension_2_logic(text, rubric),
        'D3_法理深度': evaluate_dimension_3_depth(text, rubric),
        'D4_实务操作性': evaluate_dimension_4_practicality(text, rubric),
        'D5_学术规范': evaluate_dimension_5_academic_norms(text, rubric)
    }

    # 2.1 红线统一（v4.3.0 修复，评审缺陷#5）：
    #     F1（法条幻视，含虚构法条/已废止法条）检测命中 ⇒ D1 直接归零，
    #     与 question_type_rubrics.json 的 red_lines 声明保持一致，
    #     不再仅依赖 D1 自身的硬编码废止法清单。
    f1_fired = bool(failure_detection and failure_detection.get('detections', {}).get('F1', {}).get('fired'))
    if f1_fired:
        dimensions['D1_法律依据准确性']['score'] = 0
        if '🔴 红线触发' not in dimensions['D1_法律依据准确性']['issues']:
            dimensions['D1_法律依据准确性']['issues'].insert(
                0, '🔴 红线触发：检测到 F1 法条幻视（引用已废止/虚构法律）。直接0分')

    # 3. 计算总分
    total_weighted = sum(
        float(d['weighted_contribution'].split('/')[0])
        for d in dimensions.values()
    )

    # 红线检查
    d1_score = dimensions['D1_法律依据准确性']['score']
    red_line_triggered = d1_score == 0

    if red_line_triggered:
        total_weighted = 0
        final_grade = '不及格（红线触发：法律依据根本性错误）'
    else:
        total_weighted = min(100, total_weighted * 100 / sum(
            d['weight'] for d in rubric['dimensions']
        ))
        final_grade = next(
            (g['description'] for g_name, g in rubric['grade_mapping'].items()
             if g['range'][0] <= total_weighted <= g['range'][1]),
            '未分类'
        )

    # 4. 失效模式分析
    fired_patterns = failure_detection.get('detections', {}) if failure_detection else {}
    failure_analysis = {}
    if fired_patterns:
        for pid, detail in fired_patterns.items():
            if detail.get('fired'):
                failure_analysis[pid] = {
                    'name': detail.get('failure_name', pid),
                    'probability': detail.get('probability', 0),
                    'severity': detail.get('severity', 'unknown')
                }

    # 5. 生成作业反馈
    feedback = []
    if red_line_triggered:
        feedback.append('🔴 关键问题：作业引用了已废止或虚构的法律，这是根本性错误。请先修正法律依据，然后重新提交评估。')
    else:
        for dim_name, dim_result in dimensions.items():
            if dim_result['score'] < 3.0:
                feedback.append(f'🟠 {dim_name}得分较低({dim_result["score"]}/5)，需要重点关注。')

        dims_sorted = sorted([(d['score'], name) for name, d in dimensions.items()], reverse=True)
        best_dim = dims_sorted[0][1]
        worst_dim = dims_sorted[-1][1]
        feedback.insert(0, f'✅ 表现最好的维度：{best_dim}')
        feedback.insert(1, f'⚠️ 最需改进的维度：{worst_dim}')

    return {
        'meta': {
            'text_length': len(text),
            'course_type': course_type,
            'evaluation_date': datetime.date.today().isoformat(),
            'scoring_system': '五维百分制，锚定于14案例实证基线'
        },
        'total_score': round(total_weighted, 1),
        'grade': final_grade,
        'red_line_triggered': red_line_triggered,
        'dimension_scores': {dim_name: {
            'raw_score': f"{d['score']}/5",
            'weighted': d['weighted_contribution'],
            'assessment': d['assessment'],
            'issues': d['issues']
        } for dim_name, d in dimensions.items()},
        'failure_pattern_analysis': {
            'fired_count': len(failure_analysis),
            'fired_patterns': failure_analysis,
            'overall_risk': failure_detection.get('meta', {}).get('overall_risk', 'unknown') if failure_detection else 'unknown'
        },
        'feedback': feedback,
        'improvement_plan': generate_improvement_plan(dimensions, failure_analysis)
    }


def generate_improvement_plan(dimensions: dict, failures: dict) -> list:
    """生成改进计划"""
    plan = []
    for dim_name, dim_result in dimensions.items():
        if dim_result['score'] < 3.5:
            short_name = dim_name.split('_', 1)[1] if '_' in dim_name else dim_name
            plan.append({
                'priority': 'high' if dim_result['score'] < 2.5 else 'medium',
                'dimension': short_name,
                'current_score': f"{dim_result['score']}/5",
                'target_score': '3.5/5',
                'action_items': dim_result['issues'] if dim_result['issues'] else ['需要整体提升该维度的质量']
            })

    if failures:
        for pid, detail in failures.items():
            plan.insert(0, {
                'priority': 'highest',
                'dimension': f'失效模式-{detail["name"]}',
                'current_score': f'检测概率{detail["probability"]:.0%}',
                'target_score': '不触发',
                'action_items': [f'修正{detail["name"]}相关的作业内容']
            })

    return plan[:8]


def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({'error': '用法: python law_assignment_evaluator.py <作业文件> [--course <类型>] | --text "内容"'}, ensure_ascii=False))
        sys.exit(1)

    text = None
    course_type = 'general'

    # 解析参数：跳过 flag 及其取值，第一个非 flag 参数作为位置参数（文件路径）
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--text':
            text = args[i + 1] if i + 1 < len(args) else None
            i += 2
        elif arg == '--course' and i + 1 < len(args):
            course_type = args[i + 1]
            i += 2
        elif arg.startswith('--'):
            i += 1  # 跳过未知 flag
        elif text is None:
            filepath = arg
            if os.path.exists(filepath):
                text = read_assignment(filepath)
                if text is None:
                    print(json.dumps({'error': f'读取失败: {filepath}。请确认文件有效且已安装 python-docx（pip install python-docx）。'}, ensure_ascii=False))
                    sys.exit(1)
            else:
                print(json.dumps({'error': f'文件不存在: {filepath}'}, ensure_ascii=False))
                sys.exit(1)
            i += 1
        else:
            i += 1  # 已设置 text，忽略多余位置参数

    if not text:
        print(json.dumps({'error': '未提供作业内容'}, ensure_ascii=False))
        sys.exit(1)

    results = evaluate_assignment(text, course_type)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
