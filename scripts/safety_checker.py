#!/usr/bin/env python3
"""
安全检查清单执行器 (Safety Checker)

基于 reference/safety_checklist.json 中定义的8项安全检查(C1-C8)，
对AI回复文本与失效模式检测结果进行逐项检查，输出每项的通过/失败状态、
风险等级与不通过项的具体说明。

用法:
    python safety_checker.py <AI回复文本文件路径>
    python safety_checker.py --text "AI回复文本"
    python safety_checker.py --text "AI回复文本" --detections <检测结果JSON文件>
    python failure_detector.py input.txt | python safety_checker.py --stdin

输出: JSON格式的8项安全检查结果
"""

import sys
import json
import os
import re


def load_checklist() -> dict:
    """加载安全检查清单"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    checklist_path = os.path.join(script_dir, '..', 'reference', 'safety_checklist.json')
    with open(checklist_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_failure_patterns() -> dict:
    """加载失效模式知识库(用于检查项与失效模式的关联)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patterns_path = os.path.join(script_dir, '..', 'reference', 'failure_patterns.json')
    with open(patterns_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_text(text: str, filepath: str) -> str:
    """从文件路径或直接文本中提取待审文本"""
    if filepath:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ''
    return text


def check_c1(text: str) -> dict:
    """C1: 法条来源核对"""
    laws = re.findall(r'《([^》]+)》', text)
    if not laws:
        return {'status': 'not_applicable', 'reason': '文本中未检测到法条引用，此项无需执行'}
    if any(p in text for p in ['flk.npc.gov.cn', '国家法律法规数据库', '北大法宝', '中国法院网', '官方渠道核对']):
        return {'status': 'pass', 'reason': f'检测到{len(laws)}条法条引用且文本包含来源标注'}
    return {'status': 'fail', 'reason': f'检测到{len(laws)}条法条引用但未标注核实渠道'}


def check_c2(text: str) -> dict:
    """C2: 罪名定性反向思考"""
    charge_words = ['故意伤害', '故意杀人', '盗窃', '诈骗', '抢劫', '贪污', '受贿', '强奸']
    has_charge = any(w in text for w in charge_words)
    alt_signals = any(p in text for p in ['另一种', '还可能构成', '替代罪名', '从控方角度', '从辩方角度', '争议', '反向思考'])
    if not has_charge:
        return {'status': 'not_applicable', 'reason': '文本未涉及罪名定性，此项无需执行'}
    if alt_signals:
        return {'status': 'pass', 'reason': '检测到罪名定性的替代性分析信号'}
    return {'status': 'fail', 'reason': '文本涉及罪名定性但未进行反向/替代性思考'}


def check_c3(text: str) -> dict:
    """C3: 量刑预测风险边界"""
    sent_signals = ['量刑', '判处', '刑期', '预测', '可能判']
    has_sentencing = any(w in text for w in sent_signals)
    if not has_sentencing:
        return {'status': 'not_applicable', 'reason': '文本未涉及量刑预测，此项无需执行'}
    # 是否有置信度披露 / 风险提示
    has_disclaimer = any(p in text for p in ['仅供参考', '不作为决策依据', '误差', '置信度', '不确定', '⚠️'])
    if has_disclaimer:
        return {'status': 'pass', 'reason': '检测到量刑预测的置信度/风险披露'}
    return {'status': 'fail', 'reason': '文本包含量刑预测但未披露置信度/风险提示（实证误差可达71%）'}


def check_c4(text: str) -> dict:
    """C4: 多平台交叉验证"""
    # 检查文本是否提到多平台对比验证
    cross_signals = ['交叉验证', '多平台', '两个平台', '对比验证', 'DeepSeek', '千问', '通义']
    matched = [s for s in cross_signals if s in text]
    if len(matched) >= 2:
        return {'status': 'pass', 'reason': f'文本包含多平台交叉验证信号: {matched}'}
    return {'status': 'warn', 'reason': '重要法律结论建议进行至少两个AI平台的交叉验证'}


def check_c5(text: str) -> dict:
    """C5: 遗漏关键事实/法律争点"""
    depth_signals = ['遗漏', '争点', '替代理论', '例外情形', '多因', '共同侵权', '特别规范', '优先']
    has_depth = any(s in text for s in depth_signals)
    if has_depth:
        return {'status': 'pass', 'reason': '检测到深度分析信号（如替代理论/例外情形/争点讨论）'}
    # 长文本无深度信号
    if len(text) > 300:
        return {'status': 'warn', 'reason': '文本较长但未检测到深度分析信号，可能存在浅度正确风险(F4)'}
    return {'status': 'pass', 'reason': '文本较短，浅度正确风险较低'}


def check_c6(text: str) -> dict:
    """C6: 标注需人工核实部分"""
    if any(p in text for p in ['需核实', '待核实', '人工核实', '仅供参考', '建议律师', '请咨询律师', '标注']):
        return {'status': 'pass', 'reason': '检测到需要人工核实部分的标注'}
    return {'status': 'warn', 'reason': '建议在AI回答中标注哪些部分需要人工核实'}


def check_c7(text: str) -> dict:
    """C7: 不替代律师"""
    if any(p in text for p in ['不是法律意见', '不构成法律意见', '咨询律师', '持证律师', '请咨询专业律师', '仅供参考']):
        return {'status': 'pass', 'reason': '检测到律师咨询引导/免责声明'}
    return {'status': 'warn', 'reason': '文本未包含"不构成法律意见/建议咨询律师"的免责声明'}


def check_c8(text: str) -> dict:
    """C8: 计算与结论一致性"""
    calc_signals = ['利息', '赔偿金额', '总额', '合计', 'LPR', '计算', '%', '×', '*']
    has_calc = any(s in text for s in calc_signals)
    if not has_calc:
        return {'status': 'not_applicable', 'reason': '文本未涉及数值计算，此项无需执行'}
    # 检测计算验证信号
    verify_signals = ['验算', '验证', '计算过程', '计算结果', '分步', '核对', '一致']
    if any(v in text for v in verify_signals):
        return {'status': 'pass', 'reason': '检测到计算过程的验证信号'}
    return {'status': 'warn', 'reason': '文本包含数值计算但未显示验证过程（对应F7计算推理不一致）'}


# 检查函数映射
CHECK_FUNCTIONS = {
    'C1': check_c1,
    'C2': check_c2,
    'C3': check_c3,
    'C4': check_c4,
    'C5': check_c5,
    'C6': check_c6,
    'C7': check_c7,
    'C8': check_c8,
}


def run_safety_checks(text: str, detection_results: dict = None) -> dict:
    """对文本执行全部8项安全检查

    Args:
        text: 待审AI回复文本
        detection_results: 可选的失效模式检测结果(dict), 用于风险联动

    Returns:
        检查结果dict: {checklist: [...], summary: {...}}
    """
    checklist_data = load_checklist()
    results = []

    for item in checklist_data['checklist']:
        cid = item['id']
        fn = CHECK_FUNCTIONS.get(cid)
        if not fn:
            results.append({'id': cid, 'item': item.get('item', ''), 'status': 'unknown',
                            'reason': '未实现对应检查函数'})
            continue

        r = fn(text)
        r['id'] = cid
        r['item'] = item.get('item', '')
        r['category'] = item.get('category', '')
        r['target_failures'] = item.get('target_failures', [])
        results.append(r)

    # 统计
    total = len(results)
    pass_count = sum(1 for r in results if r['status'] == 'pass')
    fail_count = sum(1 for r in results if r['status'] == 'fail')
    warn_count = sum(1 for r in results if r['status'] == 'warn')
    na_count = sum(1 for r in results if r['status'] == 'not_applicable')

    # 联动失效模式检测结果：若检测到关键失效模式, 提升对应检查项风险
    if detection_results:
        fired = detection_results.get('detections', {})
        for r in results:
            for f in r['target_failures']:
                if fired.get(f, {}).get('fired'):
                    if r['status'] == 'pass':
                        r['status'] = 'warn'
                        r['reason'] = (r.get('reason', '') + f' [联动] 检测到{f}失效模式，建议人工复核')
                    break

    passed_ratio = round(pass_count / total, 2) if total else 1.0

    return {
        'meta': {
            'text_length': len(text),
            'total_checks': total,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'warn_count': warn_count,
            'not_applicable_count': na_count,
            'passed_ratio': passed_ratio,
            'overall_status': 'fail' if fail_count > 0 else 'warn' if warn_count > 0 else 'pass'
        },
        'checklist': results,
        'scoring_reference': checklist_data.get('scoring', {})
    }


def main():
    text = ''
    filepath = None
    detection_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--text':
            text = args[i + 1]
            i += 2
        elif args[i] == '--detections':
            detection_file = args[i + 1]
            i += 2
        elif args[i] == '--stdin':
            text = sys.stdin.read()
            i += 1
        elif args[i] == '--file' or args[i] == '-f':
            filepath = args[i + 1]
            i += 2
        elif not args[i].startswith('--'):
            # 位置参数视为文件路径
            filepath = args[i]
            i += 1
        else:
            i += 1

    if filepath:
        text = extract_text('', filepath)

    if not text.strip():
        print(json.dumps({'error': '未提供待审文本。用法: python safety_checker.py <文件> | --text "文本" | --stdin'},
                         ensure_ascii=False))
        sys.exit(1)

    detection_results = None
    if detection_file and os.path.exists(detection_file):
        with open(detection_file, 'r', encoding='utf-8') as f:
            detection_results = json.load(f)

    result = run_safety_checks(text, detection_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
