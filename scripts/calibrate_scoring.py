#!/usr/bin/env python3
"""
评分校准器 (Scoring Calibrator)
LegalGuardian v4.0 — 用黄金标准基准测试集校准各题型评分精度

用法:
    python calibrate_scoring.py [--benchmark <基准文件>] [--quick]
"""

import sys, json, os

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def append_options(text: str, options: dict) -> str:
    """将题目选项拼接进题干文本，构造完整题目"""
    if not options:
        return text
    for opt_label, opt_text in options.items():
        text += f"\n{opt_label}．{opt_text}"
    return text


def run_calibration(benchmark_path: str, quick: bool = False) -> dict:
    """运行全量校准测试"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    with open(benchmark_path, 'r', encoding='utf-8') as f:
        benchmark = json.load(f)

    items = benchmark.get("benchmark_items", [])
    regression = benchmark.get("regression_tests", [])

    if quick:
        items = items[:4]  # 只测试前4项
        regression = regression[:2]

    # === 测试1：题型识别准确率 ===
    from question_type_classifier import classify_question

    type_results = []
    type_correct = 0
    for item in items:
        text = item.get("stem", "")
        # 构造完整题目文本（含选项）
        text = append_options(text, item.get("options", {}))

        classification = classify_question(text)
        is_correct = classification["type"] == item["expected_classification"]
        if is_correct:
            type_correct += 1

        type_results.append({
            "id": item["id"],
            "expected": item["expected_classification"],
            "got": classification["type"],
            "confidence": classification["confidence"],
            "correct": is_correct
        })

    type_accuracy = type_correct / len(items) if items else 0

    # === 测试2：客观题评分精度 ===
    from question_type_classifier import score_objective_question

    scoring_results = []
    scoring_errors = []
    for item in items:
        if item["type"] not in ("T1_single_choice", "T2_multi_choice", "T3_true_false"):
            continue
        if "answer_key" not in item:
            continue

        # 模拟学生答案：用正确答案构造"学生回答"
        correct = item["answer_key"]["correct"]
        # v4.3.0 修复（评审缺陷#11）：多选答案键可能存为 LIST（如 ["B","C"]），
        # 评分器期望字符串格式；此处统一归一化（构造学生回答 + 评分用的答案键），
        # 避免该题项被排除在评分统计外或误判为 0 分。
        if isinstance(correct, list):
            correct = ''.join(str(c) for c in correct)
        # 构造学生回答文本 = 题干 + "答案: " + 正确答案
        student_text = item.get("stem", "") + f"\n答案：{correct}"

        scoring_key = dict(item["answer_key"])
        scoring_key["correct"] = correct
        scoring = score_objective_question(student_text, scoring_key, item["type"])

        expected = item.get("expected_scoring", {})
        if "score" in expected and "score" in scoring:
            error = abs(scoring["score"] - expected["score"])
            scoring_errors.append(error)
            scoring_results.append({
                "id": item["id"],
                "expected_score": expected["score"],
                "got_score": scoring["score"],
                "error": error,
                "is_correct": scoring.get("is_correct")
            })

    mae = sum(scoring_errors) / len(scoring_errors) if scoring_errors else 0

    # === 测试3：失效模式检测 ===
    from failure_detector import detect_all

    detection_results = []
    detection_recall_total = 0
    detection_recall_hit = 0

    for item in items + regression:
        if "failure_patterns_expected" not in item and "expected_failures" not in item:
            continue
        expected_failures = item.get("failure_patterns_expected", item.get("expected_failures", []))
        if not expected_failures:
            continue

        text = item.get("input", item.get("stem", ""))
        text = append_options(text, item.get("options", {}))

        result = detect_all(text)
        fired_set = set(result.get("detections", {}).keys())

        hit = set(expected_failures) & fired_set
        miss = set(expected_failures) - fired_set
        detection_recall_total += len(expected_failures)
        detection_recall_hit += len(hit)

        detection_results.append({
            "id": item.get("id", "unknown"),
            "expected": expected_failures,
            "fired": list(fired_set),
            "hit": list(hit),
            "miss": list(miss)
        })

    detection_recall = detection_recall_hit / detection_recall_total if detection_recall_total > 0 else 0

    # === 汇总报告 ===
    return {
        "meta": {
            "calibrator_version": "4.3.0",
            "benchmark": os.path.basename(benchmark_path),
            "total_items": len(items),
            "quick_mode": quick
        },
        "type_classification": {
            "accuracy": f"{type_accuracy:.1%}",
            "correct": type_correct,
            "total": len(items),
            "details": type_results
        },
        "objective_scoring": {
            "mean_absolute_error": round(mae, 2),
            "tested_count": len(scoring_results),
            "passed": f"{sum(1 for e in scoring_errors if e < 0.5)}/{len(scoring_errors)}" if scoring_errors else "N/A",
            "details": scoring_results
        },
        "failure_detection": {
            "recall": f"{detection_recall:.1%}",
            "hit": detection_recall_hit,
            "total_expected": detection_recall_total,
            "details": detection_results
        },
        "overall_grade": compute_calibration_grade(type_accuracy, mae, detection_recall),
        "recommendations": generate_calibration_recommendations(type_accuracy, mae, detection_recall)
    }


def compute_calibration_grade(type_acc: float, mae: float, detection_recall: float) -> str:
    """综合评分"""
    score = type_acc * 0.4 + max(0, 1 - mae / 3) * 0.3 + detection_recall * 0.3
    if score >= 0.90:
        return "A (优秀校准)"
    elif score >= 0.75:
        return "B (良好校准)"
    elif score >= 0.60:
        return "C (需要调整)"
    else:
        return "D (需要重新校准)"


def generate_calibration_recommendations(type_acc: float, mae: float, detection_recall: float) -> list:
    """生成校准建议"""
    recs = []
    if type_acc < 0.85:
        recs.append(f"题型识别准确率{type_acc:.1%} < 85%，建议增强TYPE_PATTERNS中的pattern覆盖")
    if mae > 1.0:
        recs.append(f"客观题评分MAE={mae:.1f} > 1.0，建议检查answer_extraction正则是否匹配学生答案格式")
    if detection_recall < 0.70:
        recs.append(f"失效模式检测召回率{detection_recall:.1%} < 70%，建议增加特征关键词或降低检测阈值")
    if not recs:
        recs.append("[OK] 所有指标在可接受范围内。")
    return recs


def main():
    benchmark_path = None
    quick = False

    for i, arg in enumerate(sys.argv):
        if arg == '--benchmark' and i + 1 < len(sys.argv):
            benchmark_path = sys.argv[i + 1]
        if arg == '--quick':
            quick = True

    if not benchmark_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        benchmark_path = os.path.join(script_dir, '..', 'benchmark', 'gold_standard', 'all_types_benchmark.json')

    if not os.path.exists(benchmark_path):
        print(json.dumps({"error": f"基准文件不存在: {benchmark_path}"}, ensure_ascii=False))
        sys.exit(1)

    # 确保scripts目录在path中
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))

    result = run_calibration(benchmark_path, quick)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
