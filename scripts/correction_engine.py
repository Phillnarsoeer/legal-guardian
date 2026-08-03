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

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


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


# =============================================================================
# v4.1.0: 题型特化失效模式纠正生成器 (F11-F18)
# =============================================================================

def generate_correction_for_f11(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F11选项混淆偏误生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'concept_confusion':
            term1 = d.get('term1', '概念A')
            term2 = d.get('term2', '概念B')
            corrections.append({
                'failure_id': 'F11',
                'failure_name': '选项混淆偏误',
                'severity': '🟠 高',
                'original_issue': f'混淆了「{term1}」与「{term2}」两个相似但本质不同的法律概念',
                'empirical_evidence': {
                    'test_case': '法考真题校准',
                    'finding': f'2022-2025法考客观题中「{term1}vs{term2}」是高频混淆对，民法选择题约40%涉及此类区分',
                    'source': '2022-2025年法考客观题真题分析'
                },
                'correction_direction': f'在选择题分析中明确区分「{term1}」与「{term2}」：标注两者的成立要件差异、法律效果差异和适用场景',
                'suggested_rewrite': f'「{term1}」与「{term2}」的核心区别在于：{term1}（[要件/效果描述]），而{term2}（[要件/效果描述]）。本选项属于[正确答案]',
                'teaching_tip': '推荐使用对比表格展示混淆概念的核心差异'
            })
        elif d.get('type') == 'ambiguity_signal':
            corrections.append({
                'failure_id': 'F11',
                'failure_name': '选项混淆偏误',
                'severity': '🟠 高',
                'original_issue': '分析中使用模糊表述（可能/也许/不确定）替代明确法律判断',
                'empirical_evidence': {
                    'test_case': '法考真题校准',
                    'finding': '模糊表述降低了选择题分析的确定性，导致学生难以确定正确选项'
                },
                'correction_direction': '用明确的法律要件对比替代模糊表述',
                'suggested_rewrite': '根据[法条]第[X]条，本案应定性为[明确结论]。理由：[要件]均满足/不满足。'
            })

    if not corrections:
        corrections.append({
            'failure_id': 'F11',
            'failure_name': '选项混淆偏误',
            'severity': '🟡 预警',
            'original_issue': '检测到选择题中存在相似法律概念的混淆风险',
            'empirical_evidence': {
                'test_case': '法考真题校准',
                'finding': '相似概念混淆是客观题失分的主要原因之一'
            },
            'correction_direction': '对每个选项核验其对应的法律概念定义与成立要件',
            'suggested_rewrite': '请逐项核验：1）每个选项对应的法律概念定义；2）概念间区分标准；3）与题干事实的匹配'
        })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '概念混淆直接影响客观题得分，且反映学生对核心法律概念的掌握不足',
        'checklist_item': 'C2: 我对AI的罪名定性进行了反向思考（有没有可能构成其他罪？）'
    }


def generate_correction_for_f12(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F12采分点遗漏生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'potential_omission':
            corrections.append({
                'failure_id': 'F12',
                'failure_name': '采分点遗漏',
                'severity': '🟠 高',
                'original_issue': '简答题答案存在潜在采分点遗漏（检测到补充性过渡词）',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '采分点覆盖不足是简答题失分的首要原因，答案键中的每个采分点都有对应分值'
                },
                'correction_direction': '对照答案键的scoring_points逐点覆盖，使用「首先/其次/再次/最后」结构明确列出各采分点',
                'suggested_rewrite': '答案应包含以下采分点：1）[采分点1]... 2）[采分点2]... 3）[采分点3]...'
            })
        elif d.get('type') == 'answer_too_short':
            corrections.append({
                'failure_id': 'F12',
                'failure_name': '采分点遗漏',
                'severity': '🟠 高',
                'original_issue': '简答题答案过短(<100字)，大概率遗漏关键采分点',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '字数与采分点覆盖呈正相关，过短答案通常遗漏2个以上采分点'
                },
                'correction_direction': '按答案键逐点补充回答，确保每个采分点都有对应论述',
                'suggested_rewrite': '建议扩充答案，覆盖：[列出答案键缺失的采分点]'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '采分点遗漏直接损失分值，是简答题提分的关键突破口',
        'checklist_item': 'C5: 我问了自己：AI有没有遗漏关键事实或法律争点？'
    }


def generate_correction_for_f13(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F13定义要素缺失生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        found = d.get('found_elements', [])
        if d.get('type') == 'definition_too_short':
            corrections.append({
                'failure_id': 'F13',
                'failure_name': '定义要素缺失',
                'severity': '🟡 中高',
                'original_issue': '名词解释过于简短(<30字)，缺少构成要件要素',
                'empirical_evidence': {
                    'test_case': '法考客观题校准',
                    'finding': '完整的名词解释应包含核心概念+构成要件+法律来源，过短定义无法获得要素维度分值'
                },
                'correction_direction': '补充完整的名词解释三要素：核心概念+构成要件+法律来源',
                'suggested_rewrite': f'「[概念]」是指[核心概念定义]。其构成要件包括：1）主体... 2）客体... 3）内容...。法律依据见[法条]'
            })
        elif d.get('type') == 'definition_elements_missing':
            corrections.append({
                'failure_id': 'F13',
                'failure_name': '定义要素缺失',
                'severity': '🟡 中高',
                'original_issue': f'定义中检测到的要素信号较少(仅{len(found)}个)',
                'empirical_evidence': {
                    'test_case': '法考客观题校准',
                    'finding': '名词解释评分按三维关键词覆盖：核心概念50%+要素完整30%+法律来源20%'
                },
                'correction_direction': '补充主体/客体/内容/目的/构成要件等定义要素',
                'suggested_rewrite': f'已检测到要素: {", ".join(found) if found else "无"}。建议补充：[缺失要素]'
            })

    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '定义要素缺失反映学生对概念本质的理解不足',
        'checklist_item': None
    }


def generate_correction_for_f14(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F14判对错不给理由生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'bare_judgment':
            corrections.append({
                'failure_id': 'F14',
                'failure_name': '判对错不给理由',
                'severity': '🟡 中高',
                'original_issue': '判断题仅给出判断结果(对/错)但未附法律依据',
                'empirical_evidence': {
                    'test_case': '法考客观题校准',
                    'finding': '要求说明理由的判断题若未附依据应扣分，正确理由应引用具体法条号'
                },
                'correction_direction': '补充法律依据：引用具体法条号+解释判断逻辑',
                'suggested_rewrite': '本题答案为[正确/错误]。依据《[法律名称]》第[X]条，[法条内容]。因此，[判断逻辑推理]。'
            })

    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '判断题不给理由无法检验学生的法律推理能力',
        'checklist_item': None
    }


def generate_correction_for_f15(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F15法条解构不完整生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'incomplete_deconstruction':
            laws = d.get('laws_referenced', [])
            corrections.append({
                'failure_id': 'F15',
                'failure_name': '法条解构不完整',
                'severity': '🟠 高',
                'original_issue': f'引用了{len(laws)}部法律但未进行规范结构解构',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '法条分析题评分要求四维结构化：条文定位→构成要件→法律后果→适用范围'
                },
                'correction_direction': '按规范结构完整解构：条文定位→构成要件→法律后果→适用范围→与相关法条关系',
                'suggested_rewrite': f'对《{"》《".join(laws)}》的解构：1）条文定位... 2）构成要件... 3）法律后果... 4）适用范围...'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '法条解构不完整无法体现学生对法条规范结构的深入理解',
        'checklist_item': None
    }


def generate_correction_for_f16(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F16论述偏离题眼生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'potential_off_topic':
            count = d.get('off_topic_marker_count', 0)
            corrections.append({
                'failure_id': 'F16',
                'failure_name': '论述偏离题眼',
                'severity': '🟡 中高',
                'original_issue': f'论述题检测到{count}个偏离性过渡词，可能存在偏题风险',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '论述题评分注重围绕核心争点展开，偏离题眼会导致论证密度不足'
                },
                'correction_direction': '紧扣题干核心争点展开，检查核心关键词与题干争议焦点的重叠率',
                'suggested_rewrite': '论述结构应聚焦：[题干核心争点]。1）问题界定... 2）法理分析... 3）现实意义...'
            })

    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '论述偏离题眼会显著降低论证深度评分',
        'checklist_item': None
    }


def generate_correction_for_f17(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F17三段论结构缺失生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'syllogism_gap':
            missing = d.get('missing_elements', [])
            completeness = d.get('completeness', '?/3')
            corrections.append({
                'failure_id': 'F17',
                'failure_name': '三段论结构缺失',
                'severity': '🟠 高',
                'original_issue': f'三段论结构不完整({completeness})，缺少: {", ".join(missing)}',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '案例分析题评分要求完整三段论：大前提(法律规则)→小前提(案件事实)→结论'
                },
                'correction_direction': f'补齐缺失的三段论要素: {", ".join(missing)}',
                'suggested_rewrite': '大前提：根据《[法律名称]》第[X]条，[法律规则]... 小前提：本案中，[案件事实]... 结论：因此，[法律判断]'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '三段论结构缺失直接影响案例分析的法律推理质量',
        'checklist_item': None
    }


def generate_correction_for_f18(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F18要件事实识别错误生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'potential_misidentification':
            count = d.get('fact_emphasis_count', 0)
            corrections.append({
                'failure_id': 'F18',
                'failure_name': '要件事实识别错误',
                'severity': '🔴 关键',
                'original_issue': f'检测到{count}处事实重要性的标注，需核查是否将非关键事实误认为法律要件事实',
                'empirical_evidence': {
                    'test_case': '测试#2 堆放物致害案',
                    'finding': "学生可能将'暴雨'作为免责事由，忽略了1255条过错推定原则下堆放人的举证责任",
                    'related_failure': 'F4 浅度正确'
                },
                'correction_direction': '标注案情中的法律要件事实清单，与学生的识别结果对比',
                'suggested_rewrite': '本案的法律要件事实清单：1）[要件事实1]（对应[法条]要件）... 2）[要件事实2]... 非关键背景事实：[列出可省略的]'
            })

    return {
        'corrections': corrections,
        'priority': 'highest',
        'reason': '要件事实识别错误会导致法律定性错误，是最根本性的问题之一',
        'checklist_item': 'C5: 我问了自己：AI有没有遗漏关键事实或法律争点？'
    }


# =============================================================================
# v4.1.0: 教信赛场景特化纠正生成器 (F19-F24)
# =============================================================================

def generate_correction_for_f19(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F19试题歧义偏差生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'question_ambiguity':
            markers = d.get('ambiguity_markers', [])
            corrections.append({
                'failure_id': 'F19',
                'failure_name': '试题歧义偏差',
                'severity': '🟠 高',
                'original_issue': f'试题表述包含{len(markers)}个歧义信号词: {", ".join(markers)}',
                'empirical_evidence': {
                    'test_case': '教信赛智慧评价赛道',
                    'finding': '歧义表述导致不同学生对同一题目产生不同且均合理的理解，直接影响评分公平性'
                },
                'correction_direction': '为题目增加限定条件：明确法律生效时间、法域范围、主体/客体/情景边界',
                'suggested_rewrite': '【修改建议】题目应限定：1）适用的法律及生效时间；2）案件发生法域；3）关键要素的具体范围。示例：「根据2021年1月1日施行的《民法典》合同编，以下情形...」'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '试题歧义直接影响评分公平性，是考试设计质量的核心问题',
        'checklist_item': None
    }


def generate_correction_for_f20(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F20评分尺度偏移生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'scoring_drift':
            corrections.append({
                'failure_id': 'F20',
                'failure_name': '评分尺度偏移',
                'severity': '🟠 高',
                'original_issue': '检测到评分尺度偏移：不同批次/评分者间评分系统性偏严或偏松',
                'empirical_evidence': {
                    'test_case': '教学质量多维评价',
                    'finding': '同一试卷由不同评分者评分差异可达8分。实证基线：DS综合平均3.84/5，千问3.06/5，可作为评分锚定参照'
                },
                'correction_direction': '引入评分锚定机制，使用实证基线作为锚点样例校准评分者',
                'suggested_rewrite': '【评分校准流程】1）每个维度设置锚点：5分=DS最佳表现，3分=DS综合平均3.84，1分=千问最弱1.70；2）评分前用基准测试集校准；3）跨批次抽检一致性。'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '评分尺度偏移破坏评分公平性和可复现性，是教育评价的核心关切',
        'checklist_item': None
    }


def generate_correction_for_f21(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F21答案格式违规生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'format_violation':
            count = d.get('format_marker_count', 0)
            corrections.append({
                'failure_id': 'F21',
                'failure_name': '答案格式违规',
                'severity': '🟡 中高',
                'original_issue': f'答案以要点/列表为主（检测到{count}个列表信号），缺乏段落式论证',
                'empirical_evidence': {
                    'test_case': '教信赛智慧评价赛道',
                    'finding': '论述题要求段落式论证，纯要点式答案虽含考点但论证深度不足'
                },
                'correction_direction': '按题目要求的格式作答：论述题需段落式论证，简答题需分点但保留展开',
                'suggested_rewrite': '【论述题格式】应包含：1）问题界定（分析本题核心争点）；2）法理分析（引用法条+学理观点）；3）结论论证（逻辑展开）。'
            })

    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '格式违规影响答案的论证深度评分',
        'checklist_item': None
    }


def generate_correction_for_f22(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F22跨题一致性破裂生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'cross_question_contradiction':
            pair = d.get('term_pair', 'A vs B')
            corrections.append({
                'failure_id': 'F22',
                'failure_name': '跨题一致性破裂',
                'severity': '🟠 高',
                'original_issue': f'同一学生的不同题目答案中对「{pair}」给出矛盾判断',
                'empirical_evidence': {
                    'test_case': '综合试卷评估',
                    'finding': '客观题与主观题对同一法律原则判断不一致，反映学生知识体系存在割裂'
                },
                'correction_direction': '跨题联合分析，标注矛盾冲突点，检查学生对核心法律概念的掌握是否成体系',
                'suggested_rewrite': '【一致性核查】「{pair}」在不同题目的答案应一致。建议：1）列出该概念在所有题目中的判断；2）定位矛盾点；3）补充该概念的定义与适用条件讲解。'
            })

    return {
        'corrections': corrections,
        'priority': 'high',
        'reason': '跨题一致性破裂反映学生知识体系不完整，是诊断性评估的重要信号',
        'checklist_item': None
    }


def generate_correction_for_f23(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F23采分点粒度失当生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'too_few_points':
            corrections.append({
                'failure_id': 'F23',
                'failure_name': '采分点粒度失当',
                'severity': '🟡 中高',
                'original_issue': f'答案键采分点仅{d.get("point_count", 0)}个，粒度过粗',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '采分点过粗导致高分扎堆，无法区分学生掌握程度'
                },
                'correction_direction': '扩充采分点至3-8个，每个对应一个明确考点',
                'suggested_rewrite': '【采分点设计】建议将答案拆分为3-8个采分点，例如：1）法律依据（法条号）；2）构成要件分析；3）案件事实对应；4）结论。'
            })
        elif d.get('type') == 'too_many_points':
            corrections.append({
                'failure_id': 'F23',
                'failure_name': '采分点粒度失当',
                'severity': '🟡 中高',
                'original_issue': f'答案键采分点多达{d.get("point_count", 0)}个，粒度过细',
                'empirical_evidence': {
                    'test_case': '法考主观题校准',
                    'finding': '采分点过细导致低分泛滥，评分标准过于苛刻'
                },
                'correction_direction': '合并采分点至3-8个，与题目分值匹配',
                'suggested_rewrite': '【采分点简化】建议合并相邻采分点，控制在3-8个，每个采分点分值与难度匹配。'
            })

    return {
        'corrections': corrections,
        'priority': 'medium',
        'reason': '采分点粒度失当影响评分区分度和公平性',
        'checklist_item': None
    }


def generate_correction_for_f24(detection_detail: dict, baseline: dict, regulation: dict) -> dict:
    """为F24教学大纲合规偏离生成纠正建议"""
    detections = detection_detail.get('detections') or []
    corrections = []

    for d in detections:
        if d.get('type') == 'syllabus_noncompliance':
            ratio = d.get('coverage_ratio', 0)
            missing = d.get('missing_knowledge_points', [])
            corrections.append({
                'failure_id': 'F24',
                'failure_name': '教学大纲合规偏离',
                'severity': '🔴 关键',
                'original_issue': f'教学内容对核心知识点的覆盖率仅{round(ratio*100)}%（要求80%以上）',
                'empirical_evidence': {
                    'test_case': '教信赛智慧评价赛道-教学大纲合规审核',
                    'finding': f'缺失核心知识点: {", ".join(missing)}。教育部法学类教学质量国家标准要求核心知识点全覆盖',
                    'source': 'reference/curriculum_requirements.json'
                },
                'correction_direction': f'对照教育部课程标准补充缺失知识点: {", ".join(missing)}',
                'suggested_rewrite': '【大纲修订建议】本学期教学大纲需补充以下必授核心知识点：1）' + '；'.join(missing) + '。同时更新课程教学目标、学时分配和考核方式。'
            })

    return {
        'corrections': corrections,
        'priority': 'highest',
        'reason': '教学大纲未覆盖国家标准必授知识点，直接影响人才培养质量和课程评估结果',
        'checklist_item': None
    }


# 纠正函数映射 (v4.1.0: 覆盖 F1-F24)
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
    'F11': generate_correction_for_f11,
    'F12': generate_correction_for_f12,
    'F13': generate_correction_for_f13,
    'F14': generate_correction_for_f14,
    'F15': generate_correction_for_f15,
    'F16': generate_correction_for_f16,
    'F17': generate_correction_for_f17,
    'F18': generate_correction_for_f18,
    'F19': generate_correction_for_f19,
    'F20': generate_correction_for_f20,
    'F21': generate_correction_for_f21,
    'F22': generate_correction_for_f22,
    'F23': generate_correction_for_f23,
    'F24': generate_correction_for_f24,
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
