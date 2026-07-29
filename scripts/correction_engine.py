#!/usr/bin/env python3
"""
纠正建议生成器 (Correction Engine)

基于失效模式检测结果，结合实证基线数据(test_baseline.json)，
生成具体的、有实证案例引用的纠正建议。

用法:
    python correction_engine.py <failure_detector输出JSON文件路径>
    python failure_detector.py input.txt | python correction_engine.py --stdin

输出: JSON格式的纠正建议清单
"""

import sys
import json
import os


def load_baseline() -> dict:
    """加载实证基线数据"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_path = os.path.join(script_dir, '..', 'reference', 'test_baseline.json')
    with open(baseline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_regulation() -> dict:
    """加载三维规制路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reg_path = os.path.join(script_dir, '..', 'reference', 'three_d_regulation.json')
    with open(reg_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_correction_for_f1(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F1法条幻视生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        law_name = d.get('law_name', '未知法律')
        d_type = d.get('type', '')

        if d_type == 'repealed_law':
            corrections.append({
                'failure_id': 'F1',
                'failure_name': '法条幻视',
                'severity': '🔴 关键',
                'original_issue': f'引用了已废止的《{law_name}》',
                'empirical_evidence': {
                    'test_case': '测试#1 法条冲突',
                    'finding': f'DS主动纠正已废止《民法通则》得5/5准确性，千问识别但计算矛盾得4/5',
                    'ds_score': 5.0,
                    'qw_score': 4.0
                },
                'correction_direction': f'将《{law_name}》替换为现行有效的《民法典》相关条款',
                'suggested_rewrite': f'《{law_name}》已于2021年1月1日被《中华人民共和国民法典》取代。根据现行《民法典》第XXX条...',
                'regulation_reference': f'对应技术规范T1：内置法律知识验证层。{regulation["dimensions"]["technology"]["items"]["T1"]["description"]}'
            })

        elif d_type == 'possible_fictional_law':
            corrections.append({
                'failure_id': 'F1',
                'failure_name': '法条幻视',
                'severity': '🔴 关键',
                'original_issue': f'引用了可能不存在的「{law_name}」',
                'empirical_evidence': {
                    'test_case': '虚构法条陷阱测试',
                    'finding': '千问接受「人格权侵害惩治条例」为真实法律，识别率0%',
                    'impact': '基于不存在法律的分析完全不具有法律效力'
                },
                'correction_direction': f'验证「{law_name}」是否真实存在。如果不存在，使用国家法律法规数据库检索正确的法律依据',
                'suggested_rewrite': f'经查询国家法律法规数据库(flk.npc.gov.cn)，未找到名为「{law_name}」的法律文件。建议核实法律名称后重新查询。',
                'regulation_reference': f'对应技术规范T1：虚构法条识别率应达到100%'
            })

        elif d_type == 'missing_validity_note':
            corrections.append({
                'failure_id': 'F1',
                'failure_name': '法条幻视',
                'severity': '🟡 中等',
                'original_issue': f'引用《{law_name}》但未标注现行有效性',
                'empirical_evidence': {
                    'test_case': '测试#1 法条冲突',
                    'finding': '未标注法律有效性的引用可能让用户误以为废止法律仍然有效'
                },
                'correction_direction': f'为《{law_name}》的引用添加生效日期和最近修订日期',
                'suggested_rewrite': f'根据《{law_name}》（[生效日期]起施行，最近修订于[修订日期]）第X条...',
                'regulation_reference': f'对应技术规范L2：强制透明度要求——每项法条引用须标注来源和生效日期'
            })

    # 如果没有具体检测项但模式触发了
    if not corrections:
        corrections.append({
            'failure_id': 'F1',
            'failure_name': '法条幻视',
            'severity': '🟡 预警',
            'original_issue': 'AI回答包含法律引用，建议逐条验证准确性',
            'empirical_evidence': {
                'test_case': '14案例实证测试',
                'finding': '千问对虚构法条识别率0%，DS为100%'
            },
            'correction_direction': '逐条验证所有法律引用在官方渠道的真实性和有效性',
            'suggested_rewrite': '建议使用国家法律法规数据库(flk.npc.gov.cn)逐条核对AI引用的法律条文'
        })

    return {
        'corrections': corrections,
        'priority': 'highest',
        'reason': 'F1是根本性错误——基于错误法律依据的所有后续分析都可能无效',
        'checklist_item': 'C1: 我确认了AI引用的每条法条都在官方渠道核对过'
    }


def generate_correction_for_f2(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F2罪名定性降维生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        found = d.get('found_charge', '当前罪名')
        missing = d.get('missing_alternative', '替代罪名')

        corrections.append({
            'failure_id': 'F2',
            'failure_name': '罪名定性降维',
            'severity': '🟠 高',
            'original_issue': f'AI仅分析了{found}，未讨论{missing}的可能性',
            'empirical_evidence': {
                'test_case': '量刑预测测试+案例2牟某虐待案',
                'finding': 'DS对「趁熟睡持刀捅刺胸部致重伤」仅分析故意伤害(234条)，未讨论故意杀人未遂(232条)',
                'ds_logic_score': 3.2,
                'qw_logic_score': 3.5
            },
            'correction_direction': f'增加{missing}的替代分析，从控方角度分析其成立可能性',
            'suggested_rewrite': f'本案同时可能涉及两种罪名定性：{found}（理由是...）和{missing}（理由是...）。以下分别从两个角度进行分析...',
            'regulation_reference': f'对应技术规范T2：争议性标注与替代分析。{regulation["dimensions"]["technology"]["items"]["T2"]["description"]}'
        })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '遗漏替代罪名可能导致辩护策略的系统性偏差',
        'checklist_item': 'C2: 我对AI的罪名定性进行了反向思考（有没有可能构成其他罪？）'
    }


def generate_correction_for_f3(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F3量刑乐观偏差生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d['type'] == 'sentencing_without_confidence':
            corrections.append({
                'failure_id': 'F3',
                'failure_name': '量刑乐观偏差',
                'severity': '🟠 高',
                'original_issue': 'AI做出了量刑预测但未披露置信度/不确定性',
                'empirical_evidence': {
                    'test_case': '案例3 许某某故意杀人案',
                    'finding': 'DS预测3.5年 vs 实际判决6年，误差71%',
                    'max_error': '71%',
                    'ds_accuracy_score': 2.5
                },
                'correction_direction': '量刑预测必须附带：法定刑范围+相似案例量刑分布+预测置信度+误差提示',
                'suggested_rewrite': '⚠️ 量刑预测仅供参考，不可作为决策依据。实证数据显示AI量刑预测误差可达71%。法定刑范围为...，近年相似案件中量刑分布在X-Y年之间。',
                'regulation_reference': f'对应技术规范T3：量刑置信度披露。{regulation["dimensions"]["technology"]["items"]["T3"]["description"]}'
            })
        elif d['type'] == 'optimism_without_aggravation':
            corrections.append({
                'failure_id': 'F3',
                'failure_name': '量刑乐观偏差',
                'severity': '🟠 高',
                'original_issue': 'AI偏重分析了从轻情节但未充分评估加重情节',
                'empirical_evidence': {
                    'test_case': '案例3 许某某故意杀人案+家暴反杀量刑测试',
                    'finding': 'AI系统性地对从轻情节（自首、谅解）加权过重，对加重情节（预谋、要害部位）加权不足'
                },
                'correction_direction': '量刑分析应均衡考量从轻与加重情节，标注各方权重依据',
                'suggested_rewrite': '在分析从轻情节的同时，也应评估以下加重因素：[列出具体加重情节]。两者平衡后的量刑预期区间为...'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '量刑预测的实证误差达71%，可能使当事人产生严重不切实际的预期',
        'checklist_item': 'C3: 我不用AI做量刑预测作为决策依据'
    }


def generate_correction_for_f4(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F4浅度正确生成纠正建议"""
    corrections = [{
        'failure_id': 'F4',
        'failure_name': '浅度正确',
        'severity': '🟠 高',
        'original_issue': 'AI结论正确但缺乏深度法理分析和替代法律理论探讨',
        'empirical_evidence': {
            'test_case': '测试#2 堆放物致害+案例6任某强奸案',
            'finding': 'DS结论正确但分析深度不足——堆放物案未深入1255条特别规范，任某案「判因太浅」',
            'ds_accuracy_score': 4.5,
            'note': '"判因太浅"是AI法律分析的普遍问题'
        },
        'correction_direction': '在正确结论的基础上增加：1）特别法与一般法关系分析；2）替代法律理论探讨；3）法理争议和学术观点引用',
        'suggested_rewrite': '[原有正确结论的基础上] 此外，本案还涉及以下需要深入分析的维度：1）特别规范vs一般原则的适用关系... 2）学理上对此存在不同观点...',
        'regulation_reference': f'对应教育引导E1：法学院AI素养课程。{regulation["dimensions"]["education"]["items"]["E1"]["description"]}'
    }]
    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '浅度正确可能使法学生形成肤浅法律思维习惯',
        'checklist_item': 'C5: 我问了自己：AI有没有遗漏关键事实或法律争点？'
    }


def generate_correction_for_f5(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F5前提验证盲区生成纠正建议"""
    corrections = [{
        'failure_id': 'F5',
        'failure_name': '前提验证盲区',
        'severity': '🔴 关键',
        'original_issue': 'AI未验证用户问题中的前提条件是否成立，直接基于可能错误的前提进行分析',
        'empirical_evidence': {
            'test_case': '测试#1 R1 千问',
            'finding': '千问接受《民法通则》陷阱→追问细节信息而非发现法律已废止。展示了「律师般的谨慎」但恰恰在最根本的问题上失守',
            'qw_accuracy_score': 4.0,
            'note': '前提验证盲区是AI最根本性的缺陷之一'
        },
        'correction_direction': '回答任何法律问题前，必须先执行三步前提验证：1）法律存在性检查；2）法律现行有效性检查；3）前提条件适用性检查',
        'suggested_rewrite': '在回答您的问题之前，请允许我先确认几个前提：首先，您提到的《XX法》...经查询...其次，您所述的事实是否...',
        'regulation_reference': f'对应技术规范T1+T5：法律知识验证层+用户画像感知。使用T4模板（前提挑战型）可从源头规避此问题'
    }]
    return {
        'corrections': corrections,
        'priority': 'highest',
        'reason': '前提错误会使所有后续分析建立在不稳固的基础上',
        'checklist_item': 'C6: 我标注了AI回答中需要人工核实的部分'
    }


def generate_correction_for_f6(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F6引导性赤字生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = [{
        'failure_id': 'F6',
        'failure_name': '引导性赤字',
        'severity': '🟠 高',
        'original_issue': 'AI提供了法律分析但缺乏完整的实务操作指导',
        'empirical_evidence': {
            'test_case': '6个历史案例汇总',
            'finding': 'DS引导性平均2.96/5，千问引导性平均1.70/5。R2角色扮演可提升约40%。引导性是四维中最薄弱维度',
            'ds_guidance_avg': 2.96,
            'qw_guidance_avg': 1.70,
            'improvement': 'R2角色扮演提升40%'
        },
        'correction_direction': '补充五项实务操作内容：证据清单+操作步骤+时间节点+风险提示+替代方案',
        'suggested_rewrite': '[补充到原有分析之后]\n\n## 实务操作指引\n### 1. 证据收集清单\n### 2. 分步操作指南\n### 3. 关键时间节点\n### 4. 风险提示\n### 5. 替代性纠纷解决途径',
        'regulation_reference': f'对应教育引导E2：律师AI技能培训。使用T5模板（实操指引型）可从源头改善引导性',
        'template_recommendation': 'T5'
    }]
    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '缺乏引导性是AI法律工具最普遍的问题——告诉用户「问题在哪」但不告诉「怎么解决」',
        'checklist_item': 'C7: 我没有让AI替代律师出具正式法律意见'
    }


def generate_correction_for_f7(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F7计算推理不一致生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = [{
        'failure_id': 'F7',
        'failure_name': '计算推理不一致',
        'severity': '🟡 中高',
        'original_issue': 'AI回答中涉及数值计算的结论与内部示例存在不一致',
        'empirical_evidence': {
            'test_case': '测试#1 R1+R2 LPR争议',
            'finding': '千问R1：结论说LPR×4但示例按24%；R2LPR基准选择分歧：DS选起诉时(~13%)，千问选合同成立时(~17%)，差30%+',
            'qw_accuracy_score': 4.0,
            'discrepancy': '30%+'
        },
        'correction_direction': '统一LPR基准选择，标注理由，确保结论与计算示例完全一致',
        'suggested_rewrite': '计算验证：LPR基准选择为[合同成立时/起诉时]的一年期LPR([具体数值]%)。四倍上限=[计算结果]。以下分步验证...',
        'regulation_reference': f'对应技术规范T4：计算验证与一致性检查。{regulation["dimensions"]["technology"]["items"]["T4"]["description"]}'
    }]
    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '金额计算错误可直接导致经济损失',
        'checklist_item': 'C8: 我确认回答中的计算与结论一致，无内部矛盾'
    }


def generate_correction_for_f8(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F8因果关系过度简化生成纠正建议"""
    corrections = [{
        'failure_id': 'F8',
        'failure_name': '因果关系过度简化',
        'severity': '🟠 高',
        'original_issue': 'AI将复杂多因一果的事实简化为线性因果关系',
        'empirical_evidence': {
            'test_case': '案例2牟某虐待案+案例4鲁某保护案',
            'finding': '牟某案忽略「先行行为引起的保证人地位」不作为维度(DS逻辑3.2/千问3.5)；鲁某案忽略联动机制复杂性(千问逻辑2.2)',
            'ds_logic_score': 3.2,
            'qw_logic_score': 2.2
        },
        'correction_direction': '因果关系分析应包含：作为侵权+不作为义务+先行行为+多因一果+共同行为',
        'suggested_rewrite': '本案的因果关系分析需要从以下多个维度展开：1）行为人的作为行为与损害后果之间的因果关系... 2）行为人是否存在先行行为引起的作为义务... 3）多因素共同作用分析...',
        'regulation_reference': f'对应教育引导E1：培养学生对复杂因果关系的分析能力'
    }]
    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '因果关系简化可能导致遗漏关键的归责要素',
        'checklist_item': 'C5: 我问了自己：AI有没有遗漏关键事实或法律争点？'
    }


def generate_correction_for_f9(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F9国际法视野缺失生成纠正建议"""
    corrections = [{
        'failure_id': 'F9',
        'failure_name': '国际法视野缺失',
        'severity': '🟡 中等',
        'original_issue': '涉及基本人权的法律分析仅局限于国内法，未引用国际公约或比较法',
        'empirical_evidence': {
            'test_case': '国际法+比较法测试',
            'finding': '历史案例均未提及CEDAW（消除对妇女歧视公约）。R2中DS有改善但仍为个别现象',
            'improvement': 'R2显著改善但未系统化'
        },
        'correction_direction': '对涉及基本人权的案件，增加国际公约和比较法的参考维度',
        'suggested_rewrite': '## 国际法与比较法参考\n本案涉及的基本权利在国际法层面有以下相关依据：1）[相关国际公约]... 2）比较法视角：在[其他国家/地区]的类似案件中...',
        'regulation_reference': '使用T5模板（实操指引型）时可追加国际法维度'
    }]
    return {
        'corrections': corrections,
        'priority': 'low',
        'reason': '国际法视野的缺失主要影响学术研究深度，对实务影响相对较小',
        'checklist_item': None
    }


def generate_correction_for_f10(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F10用户差异化风险盲区生成纠正建议"""
    corrections = [{
        'failure_id': 'F10',
        'failure_name': '用户差异化风险盲区',
        'severity': '🔴 关键',
        'original_issue': 'AI未识别用户背景（法学生/非专业人士），输出未做差异化处理',
        'empirical_evidence': {
            'test_case': '项目核心研究主题',
            'finding': '法学生与非专业人士对AI错误的识别能力存在显著差异。非专业人士可能完全采信AI错误输出，风险比法学生高数倍',
            'ds_overall': 3.84,
            'qw_overall': 3.06
        },
        'correction_direction': '区分用户背景（法学生/非专业人士），前者追加深度法理分析，后者追加通俗解释+醒目风险警示+律师咨询建议',
        'suggested_rewrite': '**[法学生版本]**：...（深度法理分析）\n**[非专业版本]**：⚠️ 重要提示：以下内容仅供参考，不是正式法律意见。如需做出法律决策，必须咨询持证律师。...（通俗解释+风险警示）',
        'regulation_reference': f'对应技术规范T5：用户画像感知。{regulation["dimensions"]["technology"]["items"]["T5"]["description"]}'
    }]
    return {
        'corrections': corrections,
        'priority': 'highest',
        'reason': '同一错误对不同用户的风险差异可达数倍，非专业人士需要更强的风险保护',
        'checklist_item': 'C6+C7: 标注核实部分+不替代律师'
    }


# 纠正函数映射
CORRECTION_GENERATORS = {
    'F1': generate_correction_for_f1,
    'F2': generate_correction_for_f2,
    'F3': generate_correction_for_f3,
    'F4': generate_correction_for_f4,
    'F5': generate_correction_for_f5,
    'F6': generate_correction_for_f6,
    'F7': generate_correction_for_f7,
    'F8': generate_correction_for_f8,
    'F9': generate_correction_for_f9,
    'F10': generate_correction_for_f10,
}


def generate_all_corrections(detection_results: dict) -> dict:
    """为所有检测到的失效模式生成纠正建议"""
    baseline = load_baseline()
    regulation = load_regulation()

    corrections = {}
    checklist_items = []
    critical_count = 0
    high_count = 0

    detections = detection_results.get('detections', {})
    all_detections = detection_results.get('all_detections', {})

    for pid, result in all_detections.items():
        if result.get('fired'):
            generator = CORRECTION_GENERATORS.get(pid)
            if generator:
                correction = generator(result, baseline, regulation)
                corrections[pid] = correction

                if correction.get('checklist_item'):
                    checklist_items.append(correction['checklist_item'])

                priority = correction.get('priority', 'medium')
                if priority == 'highest':
                    critical_count += 1
                elif priority == 'high':
                    high_count += 1

    # 去重checklist items
    checklist_items = list(dict.fromkeys(checklist_items))

    return {
        'summary': {
            'total_corrections': len(corrections),
            'critical_corrections': critical_count,
            'high_corrections': high_count,
            'checklist_items_required': checklist_items
        },
        'corrections': corrections,
        'baseline_reference': {
            'ds_overall': baseline['baseline_scores']['deepseek']['overall'],
            'qw_overall': baseline['baseline_scores']['qwen']['overall'],
            'key_findings': [
                f"{k}: {v['finding']}"
                for k, v in baseline['key_findings'].items()
            ]
        }
    }


def main():
    detection_results = None

    if len(sys.argv) >= 2:
        if sys.argv[1] == '--stdin':
            detection_results = json.loads(sys.stdin.read())
        else:
            filepath = sys.argv[1]
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    detection_results = json.load(f)
            else:
                print(json.dumps({'error': f'文件不存在: {filepath}'}, ensure_ascii=False))
                sys.exit(1)

    if not detection_results:
        print(json.dumps({'error': '未提供检测结果。用法: python correction_engine.py <检测结果JSON文件> | --stdin'}, ensure_ascii=False))
        sys.exit(1)

    corrections = generate_all_corrections(detection_results)
    print(json.dumps(corrections, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
