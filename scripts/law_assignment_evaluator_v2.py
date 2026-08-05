#!/usr/bin/env python3
"""
LegalGuardian v4.0 法学作业统一评估器 (Unified Assignment Evaluator)
支持8大题型的自动识别→路由→差异化评分→失效模式检测→报告生成

用法:
    python law_assignment_evaluator_v2.py <作业文件> [--course <课程类型>] [--answer-key <答案键JSON>]
    python law_assignment_evaluator_v2.py --text "<作业内容>" --answer-key answer.json

输出: JSON格式的完整评估报告
"""

import sys, json, os, datetime
from typing import Dict, List

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# 说明：rubric 加载统一复用 law_assignment_evaluator.load_rubric（见 score_subjective），
# 本文件不再重复实现 load_rubric_v1 / load_rubric_v2。

# =============================================================================
# 核心评估函数
# =============================================================================
def evaluate_assignment_v2(text: str, answer_key: Dict = None, course_type: str = "general") -> Dict:
    """
    统一评估入口：
    1. 题型识别 → 2. 路由评分 → 3. 失效模式检测 → 4. 报告生成
    """
    # 步骤1：题型识别
    from question_type_classifier import classify_question, score_objective_question, score_semi_objective
    classification = classify_question(text)
    qtype = classification["type"]
    qtype_name = classification.get("type_name", qtype)

    # 步骤2：根据题型路由到对应评分逻辑
    scoring_result = {}
    red_line_triggered = False

    if qtype in ("T1_single_choice", "T2_multi_choice", "T3_true_false"):
        # === 客观题：答案键对比 ===
        if not answer_key:
            scoring_result = {
                "error": f"客观题({qtype_name})需要答案键",
                "requires_answer_key": True,
                "hint": "使用 --answer-key <JSON文件路径> 提供答案键"
            }
        else:
            scoring_result = score_objective_question(text, answer_key, qtype)

    elif qtype in ("T4_term_definition", "T5_short_answer"):
        # === 半客观题：采分点覆盖 ===
        if not answer_key:
            scoring_result = {
                "error": f"半客观题({qtype_name})需要答案键(含scoring_points)",
                "requires_answer_key": True,
                "hint": "答案键应包含scoring_points: [{point, keywords, score_value}]"
            }
        else:
            scoring_result = score_semi_objective(text, answer_key, qtype)

    else:
        # === 主观题 (T6/T7/T8)：五维加权评分 ===
        scoring_result = score_subjective(text, qtype, course_type)
        # 红线检查
        d1_result = scoring_result.get("dimension_scores", {}).get("D1_法律依据准确性", {})
        if isinstance(d1_result, dict) and d1_result.get("score", 3) == 0:
            red_line_triggered = True

    # 步骤3：失效模式检测（18种）
    failure_detection = run_failure_detection(text)

    # 步骤4：生成统合报告
    total_score = extract_total_score(scoring_result, qtype, answer_key, red_line_triggered)

    # 主观题(T6/T7/T8)的 raw_score 为 0~max_total(30/20/25) 制，
    # 需归一化到百分制后再查等级；total_score 仍保留原始 raw_score 语义不变
    grade_score = total_score
    if scoring_result.get("raw_score") is not None and scoring_result.get("max_score"):
        grade_score = round(total_score / scoring_result["max_score"] * 100, 1)

    report = {
        "meta": {
            "evaluator_version": "4.0.0",
            "text_length": len(text),
            "question_type": qtype,
            "question_type_name": qtype_name,
            "type_confidence": classification["confidence"],
            "course_type": course_type,
            "scoring_mode": classification["score_mode"],
            "is_objective": classification["is_objective"],
            "is_semi_objective": classification["is_semi_objective"],
            "is_subjective": classification["is_subjective"],
            "evaluation_date": datetime.date.today().isoformat()
        },
        "classification": classification,
        "scoring": scoring_result,
        "total_score": total_score,
        "grade": compute_grade(grade_score, red_line_triggered),
        "red_line_triggered": red_line_triggered,
        "failure_detection": {
            "fired_count": failure_detection.get("meta", {}).get("fired_patterns", 0),
            "critical_fired": failure_detection.get("meta", {}).get("critical_fired", 0),
            "high_fired": failure_detection.get("meta", {}).get("high_fired", 0),
            "overall_risk": failure_detection.get("meta", {}).get("overall_risk", "unknown"),
            "fired_patterns": failure_detection.get("detections", {}),
            "dimension_scores": failure_detection.get("dimension_scores", {})
        },
        "feedback": generate_feedback(scoring_result, failure_detection, qtype, red_line_triggered),
        "improvement_plan": generate_improvement_plan(scoring_result, failure_detection, qtype)
    }

    return report


def score_subjective(text: str, qtype: str, course_type: str) -> Dict:
    """
    主观题五维评分 (T6论述/T7法条分析/T8案例分析)
    复用law_assignment_evaluator.py的五维逻辑，微调权重
    """
    from law_assignment_evaluator import (
        evaluate_dimension_1_accuracy,
        evaluate_dimension_2_logic,
        evaluate_dimension_3_depth,
        evaluate_dimension_4_practicality,
        evaluate_dimension_5_academic_norms,
        load_rubric
    )

    rubric = load_rubric()

    # 根据题型调整权重
    if qtype == "T6_essay":
        # 论述题：逻辑30% + 深度25% + 准确20% + 规范15% + 实务10%
        weights = {"D1": 20, "D2": 30, "D3": 25, "D4": 10, "D5": 15}
        max_total = 30
    elif qtype == "T7_statutory_analysis":
        # 法条分析题：准确30% + 逻辑25% + 深度25% + 实务10% + 规范10%
        weights = {"D1": 30, "D2": 25, "D3": 25, "D4": 10, "D5": 10}
        max_total = 20
    else:  # T8 案例分析
        weights = {"D1": 30, "D2": 25, "D3": 20, "D4": 15, "D5": 10}
        max_total = 25

    d1 = evaluate_dimension_1_accuracy(text, rubric)
    d2 = evaluate_dimension_2_logic(text, rubric)
    d3 = evaluate_dimension_3_depth(text, rubric)
    d4 = evaluate_dimension_4_practicality(text, rubric)
    d5 = evaluate_dimension_5_academic_norms(text, rubric)

    # 加权计算（归一化到5分制→再换算到max_total）
    raw_weighted = (
        d1["score"] * weights["D1"] / 100 +
        d2["score"] * weights["D2"] / 100 +
        d3["score"] * weights["D3"] / 100 +
        d4["score"] * weights["D4"] / 100 +
        d5["score"] * weights["D5"] / 100
    ) * 5  # 归一化

    return {
        "qtype": qtype,
        "scoring_method": "五维加权结构化评分",
        "max_score": max_total,
        "raw_score": round(raw_weighted * max_total / 25, 1),
        "weights_used": weights,
        "dimension_scores": {
            "D1_法律依据准确性": {"score": round(d1["score"], 1), "weighted": weights["D1"], "assessment": d1.get("assessment", ""), "issues": d1.get("issues", [])},
            "D2_论证逻辑严密性": {"score": round(d2["score"], 1), "weighted": weights["D2"], "assessment": d2.get("assessment", ""), "issues": d2.get("issues", [])},
            "D3_法理深度": {"score": round(d3["score"], 1), "weighted": weights["D3"], "assessment": d3.get("assessment", ""), "issues": d3.get("issues", [])},
            "D4_实务操作性": {"score": round(d4["score"], 1), "weighted": weights["D4"], "assessment": d4.get("assessment", ""), "issues": d4.get("issues", [])},
            "D5_学术规范": {"score": round(d5["score"], 1), "weighted": weights["D5"], "assessment": d5.get("assessment", ""), "issues": d5.get("issues", [])}
        }
    }


# 失效模式检测失败时的默认返回（共享常量，避免重复字面量）
_DETECTION_ERROR = {
    "meta": {"fired_patterns": 0, "critical_fired": 0, "high_fired": 0, "overall_risk": "error"},
    "detections": {},
    "dimension_scores": {}
}


def run_failure_detection(text: str) -> Dict:
    """运行24种失效模式检测（进程内调用，避免命令行长度限制与启动开销）"""
    try:
        from failure_detector import detect_all
        return detect_all(text)
    except Exception as e:
        print(f"[warning] 失效模式检测失败: {e}", file=sys.stderr)
        return dict(_DETECTION_ERROR)


def extract_total_score(scoring: Dict, qtype: str, answer_key: Dict, red_line_triggered: bool) -> float:
    """从评分结果中提取总分"""
    if red_line_triggered:
        return 0.0

    if "score" in scoring:
        return scoring["score"]
    if "raw_score" in scoring:
        return scoring["raw_score"]
    if "error" in scoring:
        return 0.0

    # 尝试从五维计算
    dims = scoring.get("dimension_scores", {})
    if dims:
        total = 0
        for dname, dresult in dims.items():
            if isinstance(dresult, dict):
                total += dresult.get("score", 0)
        return round(total, 1)

    return 0.0


def compute_grade(score: float, red_line_triggered: bool) -> str:
    """计算等级"""
    if red_line_triggered:
        return "不及格（红线触发：法律依据根本性错误）"
    if score >= 90:
        return "优秀"
    elif score >= 80:
        return "良好"
    elif score >= 70:
        return "中等"
    elif score >= 60:
        return "及格"
    else:
        return "不及格"


def generate_feedback(scoring: Dict, failure: Dict, qtype: str, red_line: bool) -> List[str]:
    """生成可操作的反馈建议"""
    feedback = []

    if red_line:
        feedback.append("🔴 红线触发：作业引用了已废止或虚构的法律。这是根本性错误，请先修正法律依据后重新提交。")
        return feedback

    # 客观题反馈
    if "is_correct" in scoring:
        is_correct = scoring["is_correct"]
        if is_correct == True:
            feedback.append("✅ 答案正确。")
        elif is_correct == False:
            feedback.append("❌ 答案错误。请查看解析理解正确答案的依据。")
            if scoring.get("explanation"):
                feedback.append(f"💡 解析：{scoring['explanation'][:200]}")
        elif is_correct == "partial":
            feedback.append("🟡 部分正确（少选）。已选中的选项都是正确的，但遗漏了一些正确选项。")

    # 半客观题反馈
    if "coverage_rate" in scoring:
        feedback.append(f"📊 采分点覆盖率：{scoring['coverage_rate']}")
    if "missing_keywords" in scoring and scoring.get("missing_keywords"):
        feedback.append(f"⚠️ 遗漏关键词：{', '.join(scoring['missing_keywords'][:5])}")

    # 失效模式反馈
    fired = failure.get("detections", {})
    for pid, detail in fired.items():
        severity = detail.get("severity", "unknown")
        icon = "🔴" if severity == "critical" else "🟠" if severity == "high" else "🟡"
        feedback.append(f"{icon} 检测到失效模式 [{pid}] — 概率{detail.get('probability', 0):.0%}")

    # 无问题则给正向反馈
    if not feedback:
        feedback.append("✅ 未检测到明显问题。")

    return feedback


def generate_improvement_plan(scoring: Dict, failure: Dict, qtype: str) -> List[Dict]:
    """生成改进计划"""
    plan = []

    # 从失效模式生成改进项
    fired = failure.get("detections", {})
    for pid, detail in fired.items():
        plan.append({
            "priority": "highest" if detail.get("severity") == "critical" else "high",
            "area": f"失效模式-{pid}",
            "current_issue": str(detail.get("detections", [{}])[0].get("recommendation", ""))[:150] if detail.get("detections") else "",
            "action": "对照纠正建议修改相关内容"
        })

    # 从评分维度生成改进项
    dims = scoring.get("dimension_scores", {})
    for dname, dresult in dims.items():
        if isinstance(dresult, dict) and dresult.get("score", 3) < 3.0:
            plan.append({
                "priority": "medium",
                "area": dname,
                "current_score": f"{dresult['score']}/5",
                "target_score": "3.0/5",
                "action_items": dresult.get("issues", ["整体提升该维度质量"])
            })

    return plan[:10]


# =============================================================================
# 主入口
# =============================================================================
def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({
            "error": "用法: python law_assignment_evaluator_v2.py <作业文件> [--answer-key <JSON>] [--course <类型>] | --text \"内容\"",
            "supported_types": [
                "T1_single_choice", "T2_multi_choice", "T3_true_false",
                "T4_term_definition", "T5_short_answer",
                "T6_essay", "T7_statutory_analysis", "T8_case_analysis"
            ]
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    text = None
    answer_key = None
    course_type = "general"

    # 解析参数：跳过 flag 及其取值，第一个非 flag 参数作为位置参数（文件路径/文本）
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--text':
            if i + 1 >= len(args):
                print(json.dumps({"error": "--text 需要提供文本内容"}, ensure_ascii=False))
                sys.exit(1)
            text = args[i + 1]
            i += 2
        elif arg == '--stdin':
            text = sys.stdin.read()
            i += 1
        elif arg == '--answer-key' and i + 1 < len(args):
            ak_path = args[i + 1]
            if os.path.exists(ak_path):
                with open(ak_path, 'r', encoding='utf-8') as f:
                    answer_key = json.load(f)
            i += 2
        elif arg == '--course' and i + 1 < len(args):
            course_type = args[i + 1]
            i += 2
        elif arg.startswith('--'):
            i += 1  # 跳过未知 flag
        elif text is None:
            from law_assignment_evaluator import read_assignment
            if os.path.exists(arg):
                text = read_assignment(arg)
                if text is None:
                    print(json.dumps({"error": f"读取失败: {arg}。请确认文件有效且已安装 python-docx（pip install python-docx）。"}, ensure_ascii=False))
                    sys.exit(1)
            else:
                text = arg  # 视为直接输入的作业文本
            i += 1
        else:
            i += 1  # 已设置 text，忽略多余位置参数

    if not text:
        print(json.dumps({"error": "未提供输入内容"}, ensure_ascii=False))
        sys.exit(1)

    result = evaluate_assignment_v2(text, answer_key, course_type)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
