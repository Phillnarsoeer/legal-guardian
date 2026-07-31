#!/usr/bin/env python3
"""
答案键评估引擎 (Answer Key Evaluator)
LegalGuardian v4.0.0

独立的答案键格式验证、客观题批量评分、采分点管理工具。
与question_type_classifier.py配合使用。

用法:
    python answer_key_evaluator.py --validate <答案键JSON>                    # 验证答案键格式
    python answer_key_evaluator.py --batch <学生答案JSON> --key <答案键JSON> # 批量评分
    python answer_key_evaluator.py --generate-template T1                    # 生成题型答案键模板
"""

import sys, json, os, re
from typing import Dict, Any, List, Optional


# =============================================================================
# 答案键JSON Schema定义（每种题型的标准答案键格式）
# =============================================================================
ANSWER_KEY_SCHEMAS = {
    "T1_single_choice": {
        "required": ["correct"],
        "optional": ["max_score", "explanation", "legal_basis", "distractors"],
        "correct_type": "string (A-D)",
        "example": {
            "correct": "B",
            "max_score": 1,
            "explanation": "乙的行为构成不正当竞争...",
            "legal_basis": "《反不正当竞争法》第6条",
            "distractors": {
                "A": "商标、主体不同不代表不构成侵权",
                "B": "正确：足以引起消费者误认→不正当竞争",
                "C": "合法注册商标也可能侵权",
                "D": "违反竞争道德且违法"
            }
        }
    },
    "T2_multi_choice": {
        "required": ["correct"],
        "optional": ["max_score", "partial_credit", "explanation", "legal_basis"],
        "correct_type": "string (多字母如ABD)",
        "example": {
            "correct": "ABC",
            "max_score": 2,
            "partial_credit": True,
            "explanation": "A销售盗版/B购买供借阅/C出租均侵权",
            "legal_basis": "《著作权法》第53条"
        }
    },
    "T3_true_false": {
        "required": ["correct"],
        "optional": ["max_score", "required_reasoning", "explanation", "legal_basis"],
        "correct_type": "string (正确/错误)",
        "example": {
            "correct": "错误",
            "max_score": 1,
            "required_reasoning": False,
            "explanation": "重大误解属于可撤销非无效",
            "legal_basis": "《民法典》第147条"
        }
    },
    "T4_term_definition": {
        "required": ["scoring_points"],
        "optional": ["core_keywords", "element_keywords", "source_keywords", "max_score", "model_answer", "explanation"],
        "scoring_points_format": "与T5共用scoring_points或使用三维关键词",
        "example": {
            "core_keywords": ["不法侵害", "正在进行", "制止", "损害"],
            "element_keywords": ["防卫意图", "防卫起因", "防卫时间", "防卫限度"],
            "source_keywords": ["刑法", "第20条"],
            "max_score": 5,
            "model_answer": "正当防卫是指...（《刑法》第20条）"
        }
    },
    "T5_short_answer": {
        "required": ["scoring_points"],
        "optional": ["max_score", "explanation", "legal_basis"],
        "scoring_points_format": "list of {point, keywords, score_value}",
        "example": {
            "scoring_points": [
                {"point": "无民事行为能力人实施的民事法律行为无效", "keywords": ["无民事行为能力", "实施", "无效"], "score_value": 2},
                {"point": "虚假意思表示实施的民事法律行为无效", "keywords": ["虚假意思表示", "无效"], "score_value": 2}
            ],
            "max_score": 10,
            "legal_basis": "《民法典》第144条、第146条"
        }
    },
    "T6_essay": {
        "required": ["scoring_points"],
        "optional": ["model_essay", "min_word_count", "key_viewpoints", "max_score"],
        "example": {
            "scoring_points": [
                {"point": "论点1: XXX", "keywords": ["关键词"], "score_value": 10}
            ],
            "min_word_count": 600,
            "max_score": 30
        }
    },
    "T7_statutory_analysis": {
        "required": ["scoring_points"],
        "optional": ["statute_ref", "normative_structure", "max_score"],
        "example": {
            "statute_ref": "《民法典》第1165条",
            "scoring_points": [
                {"point": "法条定位正确", "keywords": ["第1165条", "民法典"], "score_value": 6}
            ],
            "max_score": 20
        }
    },
    "T8_case_analysis": {
        "required": ["scoring_points"],
        "optional": ["case_facts_summary", "legal_issues", "model_answer", "max_score"],
        "example": {
            "scoring_points": [
                {"point": "识别侵权责任", "keywords": ["侵权", "过错", "1165条"], "score_value": 5}
            ],
            "max_score": 25
        }
    }
}


def validate_answer_key(answer_key: Dict, qtype: str) -> Dict:
    """验证答案键格式是否符合对应题型的Schema"""
    schema = ANSWER_KEY_SCHEMAS.get(qtype)
    if not schema:
        return {"valid": False, "error": f"未知题型: {qtype}", "available_types": list(ANSWER_KEY_SCHEMAS.keys())}

    errors = []
    warnings = []

    # 检查必填字段
    for field in schema["required"]:
        if field not in answer_key:
            errors.append(f"缺少必填字段: {field}")

    # 检查correct字段
    if "correct" in answer_key and qtype in ("T1_single_choice", "T2_multi_choice", "T3_true_false"):
        correct = answer_key["correct"]
        if qtype == "T1_single_choice":
            if not isinstance(correct, str) or correct.upper() not in "ABCD":
                errors.append(f"T1的correct应为A-D单个字母，当前值: {correct}")
        elif qtype == "T2_multi_choice":
            if not isinstance(correct, str) or not re.match(r'^[A-F]{2,}$', correct.upper().replace(',', '').replace('、', '').replace(' ', '')):
                errors.append(f"T2的correct应为多字母组合(如ABD)，当前值: {correct}")
        elif qtype == "T3_true_false":
            valid_tf = {'正确', '错误', '对', '错', 'TRUE', 'FALSE', 'T', 'F', '是', '否'}
            if correct not in valid_tf:
                warnings.append(f"T3的correct建议使用'正确'或'错误'，当前值: {correct}")

    # 检查scoring_points
    if "scoring_points" in answer_key and qtype in ("T4_term_definition", "T5_short_answer", "T6_essay", "T7_statutory_analysis", "T8_case_analysis"):
        points = answer_key["scoring_points"]
        if not isinstance(points, list) or len(points) == 0:
            errors.append("scoring_points应为非空列表")
        else:
            total_value = 0
            for i, point in enumerate(points):
                if not isinstance(point, dict):
                    errors.append(f"scoring_points[{i}]应为字典")
                    continue
                if "point" not in point:
                    errors.append(f"scoring_points[{i}]缺少point字段")
                if "keywords" not in point and qtype == "T5_short_answer":
                    warnings.append(f"scoring_points[{i}]建议添加keywords字段以便自动评分")
                if "score_value" in point:
                    total_value += point["score_value"]
            if total_value > 0:
                max_score = answer_key.get("max_score", total_value)
                if abs(total_value - max_score) > 0.01:
                    warnings.append(f"scoring_points分值总和({total_value})与max_score({max_score})不一致")

    return {
        "valid": len(errors) == 0,
        "qtype": qtype,
        "errors": errors,
        "warnings": warnings,
        "schema_ref": ANSWER_KEY_SCHEMAS[qtype]
    }


def generate_template(qtype: str) -> Dict:
    """生成指定题型的答案键模板"""
    schema = ANSWER_KEY_SCHEMAS.get(qtype)
    if not schema:
        return {"error": f"未知题型: {qtype}"}
    return {
        "qtype": qtype,
        "template": schema["example"],
        "required_fields": schema["required"],
        "optional_fields": schema["optional"],
        "notes": {
            "T1_single_choice": "correct字段为A-D单个字母",
            "T2_multi_choice": "correct字段为多字母如ABD，partial_credit默认为true（少选得分）",
            "T3_true_false": "correct字段为'正确'或'错误'",
            "T4_term_definition": "使用core_keywords/element_keywords/source_keywords三维关键词，或scoring_points",
            "T5_short_answer": "scoring_points中每个采分点含point/keywords/score_value",
            "T6_essay": "scoring_points列出必须涉及的核心论点",
            "T7_statutory_analysis": "含statute_ref和规范结构分解",
            "T8_case_analysis": "scoring_points列出每个子问题的采分点"
        }.get(qtype, "")
    }


def batch_score(student_answers: List[Dict], answer_keys: List[Dict]) -> Dict:
    """
    批量评分：对多个学生答案进行客观题评分

    student_answers: [{"id": "Q1", "text": "学生答案文本", "qtype": "T1_single_choice"}, ...]
    answer_keys: [{"id": "Q1", "correct": "B", "max_score": 1}, ...] 或按id索引的字典
    """
    from question_type_classifier import score_objective_question

    # 构建答案键索引
    key_index = {}
    for ak in answer_keys:
        kid = ak.get("id", ak.get("question_id", str(len(key_index))))
        key_index[kid] = ak

    results = []
    total_score = 0
    total_possible = 0

    for sa in student_answers:
        qid = sa.get("id", sa.get("question_id", str(len(results))))
        qtype = sa.get("qtype", "T1_single_choice")
        text = sa.get("text", "")

        ak = key_index.get(qid, {})
        if not ak:
            results.append({"id": qid, "error": f"未找到题目{qid}的答案键", "score": 0})
            continue

        scoring = score_objective_question(text, ak, qtype)
        scoring["id"] = qid
        results.append(scoring)

        if "score" in scoring:
            total_score += scoring["score"]
            total_possible += scoring.get("max_score", 0)

    return {
        "total_students": len(student_answers),
        "total_questions": len(results),
        "total_score": total_score,
        "total_possible": total_possible,
        "accuracy": f"{total_score}/{total_possible} ({total_score/max(total_possible,1):.1%})" if total_possible > 0 else "N/A",
        "results": results
    }


# =============================================================================
# 主入口
# =============================================================================
def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "用法: python answer_key_evaluator.py --validate <JSON> | --batch <JSON> --key <JSON> | --generate-template <T1-T8>",
            "supported_types": list(ANSWER_KEY_SCHEMAS.keys())
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    args = sys.argv[1:]

    if args[0] == '--generate-template':
        qtype = args[1] if len(args) > 1 else "T1_single_choice"
        result = generate_template(qtype)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args[0] == '--validate':
        path = args[1] if len(args) > 1 else None
        qtype = None
        for i, a in enumerate(args):
            if a == '--type' and i + 1 < len(args):
                qtype = args[i + 1]

        if not path or not os.path.exists(path):
            print(json.dumps({"error": "请提供有效的答案键JSON文件路径"}, ensure_ascii=False))
            sys.exit(1)

        with open(path, 'r', encoding='utf-8') as f:
            ak = json.load(f)

        # 尝试从答案键自身获取题型
        if not qtype:
            qtype = ak.get("qtype", ak.get("type", "T1_single_choice"))

        result = validate_answer_key(ak, qtype)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args[0] == '--batch':
        # 批量评分
        student_path = None
        key_path = None
        for i, a in enumerate(args):
            if a == '--key' and i + 1 < len(args):
                key_path = args[i + 1]
            elif a != '--batch' and not student_path and a != '--key' and not a.startswith('--'):
                if not student_path:
                    student_path = a

        if not student_path or not key_path:
            print(json.dumps({"error": "用法: python answer_key_evaluator.py --batch <学生答案JSON> --key <答案键JSON>"}, ensure_ascii=False))
            sys.exit(1)

        with open(student_path, 'r', encoding='utf-8') as f:
            students = json.load(f)
        with open(key_path, 'r', encoding='utf-8') as f:
            keys = json.load(f)

        result = batch_score(students if isinstance(students, list) else students.get("answers", []),
                            keys if isinstance(keys, list) else keys.get("answer_keys", []))
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(json.dumps({"error": f"未知参数: {args[0]}"}, ensure_ascii=False))


if __name__ == '__main__':
    main()
