#!/usr/bin/env python3
"""
提问模板匹配推荐器 (Template Matcher)

分析用户原始法律问题，识别潜在陷阱，匹配最佳标准化提问模板，
输出优化后的问题表述。

用法:
    python template_matcher.py "用户原始问题文本"
    echo "用户问题" | python template_matcher.py --stdin

输出: JSON格式的模板推荐结果
"""

import sys
import json
import os
import re


def load_templates() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(script_dir, '..', 'reference', 'correction_templates.json')
    with open(templates_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_legal_knowledge() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(script_dir, '..', 'reference', 'legal_knowledge_base.json')
    with open(kb_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_question(question: str, templates_data: dict, legal_kb: dict) -> dict:
    """分析用户问题中的潜在陷阱和特征"""

    analysis = {
        'has_legal_name': False,
        'has_specific_article': False,
        'has_sentencing_inquiry': False,
        'has_crime_question': False,
        'has_practical_need': False,
        'has_repealed_law_risk': False,
        'has_unverified_premise': False,
        'detected_laws': [],
        'detected_articles': [],
        'traps': [],
        'complexity': 'simple'
    }

    # 检测具体法律名称
    repealed_laws = legal_kb.get('civil_law', {}).get('民法典', {}).get('repealed_laws_warning', {})
    common_traps = legal_kb.get('common_traps', {})

    # 检测法律引用
    law_pattern = re.compile(r'《([^》]+)》')
    laws_found = law_pattern.findall(question)
    for law in laws_found:
        analysis['detected_laws'].append(law)
        analysis['has_legal_name'] = True

        # 检查是否为已废止法律
        if law in repealed_laws:
            analysis['has_repealed_law_risk'] = True
            analysis['traps'].append({
                'type': 'repealed_law',
                'detail': f'《{law}》{repealed_laws[law]}',
                'risk': 'high'
            })

        # 检查是否可能为虚构法律
        fictional = common_traps.get('fictional_laws', {})
        if law in fictional:
            analysis['has_repealed_law_risk'] = True
            analysis['traps'].append({
                'type': 'fictional_law',
                'detail': fictional[law].get('note', '可能不存在'),
                'risk': 'critical'
            })

    # 检测条款号
    article_pattern = re.compile(r'第[一二三四五六七八九十百千\d]+条')
    articles_found = article_pattern.findall(question)
    if articles_found:
        analysis['detected_articles'] = articles_found
        analysis['has_specific_article'] = True

    # 检测量刑相关
    sentencing_keywords = ['判几年', '刑期', '量刑', '判刑', '坐牢', '会判', '缓刑',
                          '有期徒刑', '无期徒刑', '死刑', '刑拘', '可能判']
    if any(kw in question for kw in sentencing_keywords):
        analysis['has_sentencing_inquiry'] = True

    # 检测罪名相关
    crime_keywords = ['罪', '故意伤害', '故意杀人', '强奸', '盗窃', '抢劫', '诈骗',
                      '虐待', '正当防卫', '防卫过当', '过失', '交通肇事']
    if any(kw in question for kw in crime_keywords):
        analysis['has_crime_question'] = True

    # 检测实务需求
    practical_keywords = ['怎么办', '怎么处理', '怎么告', '怎么起诉', '证据', '赔偿',
                         '起诉', '打官司', '维权', '协议', '合同', '借条', '欠条',
                         '怎么收集', '需要什么']
    if any(kw in question for kw in practical_keywords):
        analysis['has_practical_need'] = True

    # 检测未经验证的前提
    premise_signals = ['听说', '据我所知', '我认为', '按照XX', '根据规定',
                       '网上说', '朋友说', '有人告诉我']
    if any(signal in question for signal in premise_signals):
        analysis['has_unverified_premise'] = True
        analysis['traps'].append({
            'type': 'unverified_premise',
            'detail': '问题中包含可能未经验证的前提假设',
            'risk': 'medium'
        })

    # 判断复杂度
    if len(analysis['detected_laws']) >= 2 or \
       (analysis['has_crime_question'] and analysis['has_sentencing_inquiry']) or \
       len(question) > 500:
        analysis['complexity'] = 'complex'
    elif len(analysis['traps']) > 0 or analysis['has_repealed_law_risk']:
        analysis['complexity'] = 'medium'

    return analysis


def match_templates(analysis: dict, templates_data: dict) -> list:
    """根据问题分析结果匹配最佳模板"""
    matching_rules = templates_data['matching_rules']
    templates = templates_data['templates']

    scores = {t['id']: 0 for t in templates}

    # 规则1: 有法律名称引用 → T1+T4优先
    if analysis['has_legal_name']:
        scores['T1'] += 30
        scores['T4'] += 30

    # 规则2: 有特定条款号 → T1优先
    if analysis['has_specific_article']:
        scores['T1'] += 25

    # 规则3: 涉及量刑 → T2+T3优先
    if analysis['has_sentencing_inquiry']:
        scores['T2'] += 35
        scores['T3'] += 20

    # 规则4: 涉及罪名定性 → T3优先
    if analysis['has_crime_question']:
        scores['T3'] += 30

    # 规则5: 实务需求 → T5优先
    if analysis['has_practical_need']:
        scores['T5'] += 35

    # 规则6: 未经验证的前提 → T4优先
    if analysis['has_unverified_premise']:
        scores['T4'] += 25

    # 规则7: 涉及已废止法律 → T4+T1最高优先
    if analysis['has_repealed_law_risk']:
        scores['T4'] += 40
        scores['T1'] += 20

    # 规则8: 复杂问题 → 多模板推荐
    if analysis['complexity'] == 'complex':
        scores['T3'] += 15
        scores['T5'] += 10

    # 排序取前3
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_templates = [t for t, score in ranked if score > 0][:3]

    if not top_templates:
        top_templates = ['T4', 'T1']  # 默认推荐前提验证+法条验证

    return top_templates


def generate_optimized_question(question: str, analysis: dict, recommended_templates: list,
                                 templates_data: dict, legal_kb: dict) -> dict:
    """基于原始问题和推荐模板生成优化后的提问"""

    templates = {t['id']: t for t in templates_data['templates']}
    primary_template = templates.get(recommended_templates[0]) if recommended_templates else None

    modifications = []

    # 检测已废止法律并生成替换
    repealed_laws = legal_kb.get('civil_law', {}).get('民法典', {}).get('repealed_laws_warning', {})
    for law in analysis['detected_laws']:
        if law in repealed_laws:
            modifications.append({
                'type': 'replace_repealed_law',
                'original': f'《{law}》',
                'replacement': '《中华人民共和国民法典》',
                'reason': f'{repealed_laws[law]}'
            })

    # 检测需添加验证步骤
    if analysis['has_unverified_premise'] or analysis['has_repealed_law_risk']:
        modifications.append({
            'type': 'add_verification_step',
            'description': '在问题前添加前提验证步骤',
            'suggested_prefix': '在我继续之前，请先完成以下验证步骤：1）确认我引用的法律是否现行有效...'
        })

    # 检测量刑预测需求
    if analysis['has_sentencing_inquiry']:
        modifications.append({
            'type': 'add_sentencing_warning',
            'description': '添加量刑预测的置信度要求和相似案例检索要求',
            'suggested_addition': '请同时检索最近5年内相似案件的量刑数据。注意：量刑预测仅供学术参考，实证数据表明AI量刑预测误差可达71%。'
        })

    # 检测实务需求
    if analysis['has_practical_need']:
        modifications.append({
            'type': 'add_practical_guidance',
            'description': '添加实务操作指引要求',
            'suggested_addition': '除法律分析外，请提供：证据收集清单、操作步骤、时间节点、风险提示和替代方案。'
        })

    # 构建优化后的问题
    optimized_parts = []

    # 添加前提验证（如需要）
    if any(m['type'] == 'add_verification_step' for m in modifications):
        optimized_parts.append('【验证步骤】请先确认以下前提是否成立：')

    # 添加T4模板前缀（如果需要前提挑战）
    if 'T4' in recommended_templates:
        for law in analysis['detected_laws']:
            if law in repealed_laws:
                optimized_parts.append(f'我原来以为根据《{law}》可以...但请先帮我确认《{law}》是否仍然有效。如果已废止，请用现行法律分析。')

    if not any('原来以为' in p for p in optimized_parts):
        optimized_parts.append(question)

    # 添加模板补充要求
    if primary_template:
        optimized_parts.append(f'\n【回答格式要求】请按以下方式组织回答：{primary_template["template"][:100]}...')

    # 添加检测到的修改建议
    for mod in modifications:
        if mod['type'] not in ['add_verification_step'] and 'suggested_addition' in mod:
            optimized_parts.append(mod['suggested_addition'])

    return {
        'original_question': question,
        'optimized_question': '\n\n'.join(optimized_parts),
        'modifications': modifications,
        'primary_template': primary_template['name'] if primary_template else None
    }


def main():
    question = None

    if len(sys.argv) >= 2:
        if sys.argv[1] == '--stdin':
            question = sys.stdin.read().strip()
        else:
            question = sys.argv[1]

    if not question:
        print(json.dumps({'error': '未提供问题文本。用法: python template_matcher.py "用户问题" | --stdin'}, ensure_ascii=False))
        sys.exit(1)

    templates_data = load_templates()
    legal_kb = load_legal_knowledge()

    analysis = analyze_question(question, templates_data, legal_kb)
    recommended = match_templates(analysis, templates_data)
    optimized = generate_optimized_question(question, analysis, recommended, templates_data, legal_kb)

    templates = {t['id']: t for t in templates_data['templates']}
    result = {
        'analysis': analysis,
        'recommended_templates': [
            {
                'id': tid,
                'name': templates[tid]['name'],
                'icon': templates[tid]['icon'],
                'template_summary': templates[tid]['template'][:120] + '...',
                'target_failures': templates[tid]['target_failures'],
                'empirical_basis': templates[tid]['empirical_basis'][:100] + '...'
            }
            for tid in recommended if tid in templates
        ],
        'optimized_question': optimized,
        'usage_tips': [
            '将优化后的问题直接复制到AI对话中使用',
            '如回答质量仍不理想，尝试切换模板（如从T1→T4或T3→T5）',
            'R2角色扮演（以"你是一位资深律师"开头）可进一步提升回答质量约40%'
        ]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
