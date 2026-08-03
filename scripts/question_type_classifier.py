#!/usr/bin/env python3
"""
题型识别与路由引擎 (Question Type Classifier)
LegalGuardian v4.0.0 — 支持8大法学题型(T1-T8)的自动识别、路由和差异化评分

用法:
    python question_type_classifier.py <输入文本> [--answer-key <答案键JSON>]
    python question_type_classifier.py --stdin

输出: JSON格式的题型分类+评分结果
"""

import sys, json, os, re
from typing import Dict, Any, Optional, List, Tuple

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# =============================================================================
# 题型识别规则库 — 基于2022-2025法考真题格式校准
# =============================================================================
TYPE_PATTERNS = {
    "T1_single_choice": {
        "name": "单项选择题",
        "name_en": "Single Choice",
        "patterns": [
            # 格式信号: A． B． C． D． 四选项
            r'[AＡ][．\.]\s*.+?\n[BＢ][．\.]\s*.+?\n[CＣ][．\.]\s*.+?\n[DＤ][．\.]',
            r'[AＡ][．\.].{5,}\n[BＢ][．\.].{5,}\n[CＣ][．\.].{5,}\n[DＤ][．\.]',
            # 题型标注
            r'(?:单选题|单项选择题|单项选择|单选)',
            # 题干信号词
            r'下列(?:哪一|哪个|哪项)(?:选项|说法|表述|判断)(?:是)?正确的',
            r'下列(?:哪一|哪个|哪项)(?:选项|说法|表述|判断)(?:是)?错误的',
            r'关于.{1,30}(?:下列说法|下列表述|下列判断)正确的',
        ],
        "score_mode": "exact_match",
        "partial_credit": False,
        "max_score_default": 1,
        "answer_extraction": r'(?:答案|选|选择)[：:\s]*([A-Da-d])',
        "exam_calibration": "法考客观题试卷一/二 第1-50题，每题1分"
    },

    "T2_multi_choice": {
        "name": "多项选择题",
        "name_en": "Multiple Choice",
        "patterns": [
            # 格式信号: A-F选项且题干说"哪些"
            r'下列(?:哪些|哪几|哪几项|哪些选项)(?:选项|说法|表述|判断|行为)(?:是)?正确的',
            r'下列(?:哪些|哪几|哪几项|哪些选项)(?:选项|说法|表述|判断|行为)(?:是)?错误的',
            r'(?:多选题|多项选择题|多项选择|多选)',
            # 选项数>4 (A-F)
            r'[A-FＡ-Ｆ][．\.]\s*.+?\n[A-FＡ-Ｆ][．\.]\s*.+?\n[A-FＡ-Ｆ][．\.]\s*.+?\n[A-FＡ-Ｆ][．\.]\s*.+?\n[A-FＡ-Ｆ][．\.]',
            # 中文序号选项 (①②③④) 通常也是多选题
            r'[①②③④⑤⑥][．\.]?\s*.{10,}\n[①②③④⑤⑥][．\.]?\s*.{10,}\n[①②③④⑤⑥][．\.]?\s*.{10,}',
            # 题目含"哪些"+"侵犯/构成/属于"等多选特征
            r'哪些.{1,30}(?:侵犯|构成|属于|应当|可以)',
        ],
        "score_mode": "partial_credit",
        "partial_credit": True,
        "max_score_default": 2,
        "answer_extraction": r'(?:答案|选|选择)[：:\s]*([A-Fa-f,，、\s]+)',
        "exam_calibration": "法考客观题试卷一/二 第51-85题，每题2分，少选得部分分"
    },

    "T3_true_false": {
        "name": "判断题",
        "name_en": "True/False",
        "patterns": [
            r'(?:判断题|判断正误|判断对错|判断下列)',
            r'判断(?:下列|以下)(?:说法|表述|命题)(?:是否)?正确',
            r'[✓✗✅❌对错√×]',
            r'请判断.{1,30}(?:正确|错误|对|错)',
            r'下列说法(?:是否)?正确的(?:是|请)',
        ],
        "score_mode": "exact_match",
        "partial_credit": False,
        "max_score_default": 1,
        "answer_extraction": r'(?:答案|判断)[：:\s]*(正确|错误|对|错|[✓✗✅❌√×])',
        "exam_calibration": "法学本科期末常见题型，每题1-2分"
    },

    "T4_term_definition": {
        "name": "名词解释",
        "name_en": "Term Definition",
        "patterns": [
            r'(?:名词解释|解释下列|解释以下|定义下列)',
            r'(?:什么是|何谓|何为|简述.*概念|简述.*含义)',
            r'(?:请解释|请说明|请简述).{1,20}(?:的概念|的含义|的定义)',
            r'^.{2,15}(?:是指|指的是|即|又称).{2,30}$',
        ],
        "score_mode": "keyword_coverage",
        "partial_credit": True,
        "max_score_default": 5,
        "answer_extraction": None,
        "exam_calibration": "法学本科期末常见题型，每题3-5分"
    },

    "T5_short_answer": {
        "name": "简答题",
        "name_en": "Short Answer",
        "patterns": [
            r'(?:简答题|简答|简述|简要说明|简要回答|试简述)',
            r'(?:试述|试论).{1,50}(?:。|$)',
            r'请(?:简述|简要说明|简要回答).{1,60}',
            r'(?:列出|列举|指出).{1,30}(?:的|有哪些|是什么)',
        ],
        "score_mode": "scoring_point_coverage",
        "partial_credit": True,
        "max_score_default": 10,
        "answer_extraction": None,
        "exam_calibration": "法学本科期末/考研常见题型，每题5-15分"
    },

    "T6_essay": {
        "name": "论述题",
        "name_en": "Essay/Discussion",
        "patterns": [
            r'(?:论述题|论述|论.*的|试论|试述|申论)',
            r'谈谈.{1,50}(?:的理解|的认识|的看法)',
            r'(?:不少于|字数要求|字以上|不少于\d+字)',
            r'结合.{1,30}(?:谈谈|论述|分析)',
            r'(?:观点正确|表述完整|总字数)',
        ],
        "score_mode": "five_dimension_weighted",
        "partial_credit": True,
        "max_score_default": 30,
        "answer_extraction": None,
        "exam_calibration": "法考主观题第一题，约600字，30分左右"
    },

    "T7_statutory_analysis": {
        "name": "法条分析题",
        "name_en": "Statutory Analysis",
        "patterns": [
            r'(?:法条分析|分析.*法条|评析.*条款|法条评析)',
            r'《[^》]+》第[^条]+条.{1,30}(?:分析|评析|论述|如何理解)',
            r'请(?:分析|评析|解读).{1,20}《[^》]+》',
            r'(?:如何理解|谈谈你对).{1,20}法条',
        ],
        "score_mode": "structured_rubric",
        "partial_credit": True,
        "max_score_default": 20,
        "answer_extraction": None,
        "exam_calibration": "考研法学常见题型，每题15-25分"
    },

    "T8_case_analysis": {
        "name": "案例分析题",
        "name_en": "Case Analysis",
        "patterns": [
            r'(?:案例分析|案例.*分析|分析.*案例|案件分析)',
            r'【案情】',
            r'(?:案|案由|案情).{50,}(?:问题|请分析|请回答|问[：:])',
            r'(?:根据.*案情|阅读.*材料).{50,}(?:回答|分析)',
            # 实务案例特征: 自然人间纠纷+请分析责任
            r'(?:张某|李某|王某|赵某|刘某|陈某|杨某|周某).{30,}(?:纠纷|侵权|合同|债务|赔偿).{30,}请分析',
            r'请分析.{1,30}(?:侵权责任|法律责任|民事责任|刑事责任|违约责任)',
            # 含原被告位置/日期/金额等实务案件特征
            r'\d{4}年\d{1,2}月.{50,}(?:起诉|要求赔偿|原告诉|被告诉)',
        ],
        "score_mode": "five_dimension_weighted",
        "partial_credit": True,
        "max_score_default": 25,
        "answer_extraction": None,
        "exam_calibration": "法考主观题核心题型，每题约25分"
    }
}


def classify_question(text: str) -> Dict[str, Any]:
    """
    识别文本属于哪种法学题型

    策略: 加权特征匹配，每种题型有多个正则pattern，匹配数×权重=得分
    置信度 = 最高分/(最高分+第二高分)，体现区分能力
    """
    scores = {}
    text_clean = text.strip()

    for qtype, config in TYPE_PATTERNS.items():
        score = 0.0
        matched_patterns = []
        for pattern in config["patterns"]:
            if re.search(pattern, text_clean, re.DOTALL | re.MULTILINE):
                score += 1.0
                matched_patterns.append(pattern[:60] + "...")

        scores[qtype] = {
            "raw_score": score,
            "matched_count": len(matched_patterns),
            "matched_patterns": matched_patterns
        }

    # 找出最高分
    max_type = max(scores, key=lambda k: scores[k]["raw_score"])
    max_score = scores[max_type]["raw_score"]

    # 如果最高分也为0，尝试启发式判断
    if max_score == 0:
        # 检查是否有大量法律条文引用 → T7
        law_count = len(re.findall(r'《[^》]+》', text_clean))
        if law_count >= 3:
            max_type = "T7_statutory_analysis"
            max_score = 0.5
        # 检查是否包含完整案情描述 → T8
        elif len(text_clean) > 500 and any(w in text_clean for w in ['原告', '被告', '被害人', '案情']):
            max_type = "T8_case_analysis"
            max_score = 0.5
        # 检查是否是简短的定义式表述 → T4
        elif len(text_clean) < 200 and ('是指' in text_clean or '指的是' in text_clean):
            max_type = "T4_term_definition"
            max_score = 0.5
        else:
            max_type = "unknown"
            max_score = 0

    # 计算置信度
    score_values = sorted([s["raw_score"] for s in scores.values()], reverse=True)
    runner_up = score_values[1] if len(score_values) > 1 else 0
    if max_score > 0 and runner_up > 0:
        confidence = min(max_score / (max_score + runner_up + 0.01), 1.0)
    elif max_score > 0:
        confidence = 0.6
    else:
        confidence = 0.0

    return {
        "type": max_type,
        "type_name": TYPE_PATTERNS[max_type]["name"] if max_type in TYPE_PATTERNS else "未知题型",
        "confidence": round(confidence, 2),
        "score_mode": TYPE_PATTERNS[max_type]["score_mode"] if max_type in TYPE_PATTERNS else "unknown",
        "is_objective": max_type in ("T1_single_choice", "T2_multi_choice", "T3_true_false"),
        "is_semi_objective": max_type in ("T4_term_definition", "T5_short_answer"),
        "is_subjective": max_type in ("T6_essay", "T7_statutory_analysis", "T8_case_analysis"),
        "max_score_default": TYPE_PATTERNS[max_type]["max_score_default"] if max_type in TYPE_PATTERNS else 0,
        "all_scores": {k: round(v["raw_score"], 1) for k, v in
                       sorted(scores.items(), key=lambda x: -x[1]["raw_score"])[:4]}
    }


def extract_student_answer(text: str, qtype: str) -> Optional[str]:
    """从学生回答文本中提取选择题/判断题的答案"""
    config = TYPE_PATTERNS.get(qtype, {})
    extraction_pattern = config.get("answer_extraction")
    if not extraction_pattern:
        return None

    match = re.search(extraction_pattern, text, re.MULTILINE)
    if match:
        return match.group(1).strip().upper()
    return None


def parse_answer_key_option(key_str: str) -> set:
    """解析答案键中的选项字符串 → 集合"""
    if not key_str:
        return set()
    # 处理各种分隔符: "ABD", "A,B,D", "A、B、D", "A B D"
    key_str = key_str.upper().strip()
    if re.match(r'^[A-F]+$', key_str):
        return set(key_str)
    return set(re.split(r'[,，、\s]+', key_str)) - {''}


def score_objective_question(text: str, answer_key: Dict, qtype: str) -> Dict:
    """
    客观题评分 (T1/T2/T3)

    T1: 精确匹配，学生答案==答案键 → 满分；否则 → 0
    T2: 部分得分，全对→满分；少选→按比例得分；多选/错选→0
    T3: 精确匹配，对/错=答案键 → 满分；否则 → 0
    """
    if not answer_key:
        return {"error": "客观题评分需要答案键(answer_key)", "requires_answer_key": True}

    correct = answer_key.get("correct", answer_key.get("answer", ""))
    if not correct:
        return {"error": "答案键中缺少correct或answer字段"}

    max_score = answer_key.get("max_score", TYPE_PATTERNS[qtype]["max_score_default"])
    student_answer = extract_student_answer(text, qtype)

    if qtype == "T1_single_choice":
        correct_set = parse_answer_key_option(str(correct))
        student_set = parse_answer_key_option(student_answer) if student_answer else set()

        if student_set == correct_set and len(student_set) == 1:
            is_correct = True
            score = max_score
        else:
            is_correct = False
            score = 0

        return {
            "qtype": qtype,
            "qtype_name": "单项选择题",
            "student_answer": student_answer or "(未检测到答案)",
            "correct_answer": correct,
            "is_correct": is_correct,
            "score": score,
            "max_score": max_score,
            "explanation": answer_key.get("explanation", "")
        }

    elif qtype == "T2_multi_choice":
        correct_set = parse_answer_key_option(str(correct))
        student_set = parse_answer_key_option(student_answer) if student_answer else set()

        if student_set == correct_set:
            is_correct = True
            score = max_score
        elif len(student_set) > 0 and student_set.issubset(correct_set):
            # 少选 → 按比例得分
            is_correct = "partial"
            partial_ratio = len(student_set) / len(correct_set)
            score = round(max_score * partial_ratio, 1)
        else:
            # 多选或错选 → 0分
            is_correct = False
            score = 0

        return {
            "qtype": qtype,
            "qtype_name": "多项选择题",
            "student_answer": student_answer or "(未检测到答案)",
            "correct_answer": correct,
            "student_set": sorted(student_set) if student_set else [],
            "correct_set": sorted(correct_set),
            "is_correct": is_correct,
            "score": score,
            "max_score": max_score,
            "explanation": answer_key.get("explanation", "")
        }

    elif qtype == "T3_true_false":
        # 标准化对错判断
        TRUE_VALUES = {'正确', '对', '✓', '✅', '√', 'TRUE', 'T', 'YES', 'Y', '是'}
        FALSE_VALUES = {'错误', '错', '✗', '❌', '×', 'FALSE', 'F', 'NO', 'N', '否'}

        student_norm = None
        if student_answer:
            if student_answer.upper() in TRUE_VALUES or student_answer in TRUE_VALUES:
                student_norm = "正确"
            elif student_answer.upper() in FALSE_VALUES or student_answer in FALSE_VALUES:
                student_norm = "错误"

        correct_norm = None
        if str(correct).upper() in TRUE_VALUES or str(correct) in TRUE_VALUES:
            correct_norm = "正确"
        elif str(correct).upper() in FALSE_VALUES or str(correct) in FALSE_VALUES:
            correct_norm = "错误"
        else:
            correct_norm = str(correct)

        is_correct = student_norm == correct_norm if student_norm else False
        score = max_score if is_correct else 0

        return {
            "qtype": qtype,
            "qtype_name": "判断题",
            "student_answer": student_answer or "(未检测到答案)",
            "student_normalized": student_norm,
            "correct_answer": correct_norm,
            "is_correct": is_correct,
            "score": score,
            "max_score": max_score,
            "explanation": answer_key.get("explanation", "")
        }

    return {"error": f"未知的客观题类型: {qtype}"}


def score_semi_objective(text: str, answer_key: Dict, qtype: str) -> Dict:
    """
    半客观题评分 (T4/T5)

    T4 名词解释: 关键词覆盖法
      - 核心概念准确 (50%): 是否精准定义
      - 要素完整性 (30%): 构成要件是否完整
      - 法条依据 (20%): 是否标注来源

    T5 简答题: 采分点覆盖法
      - 每个采分点含关键词和分值
      - 覆盖率×满分 = 得分
    """
    if not answer_key:
        return {"error": "半客观题评分需要答案键(含scoring_points或keywords)", "requires_answer_key": True}

    scoring_points = answer_key.get("scoring_points", [])
    keywords = answer_key.get("keywords", [])
    max_score = answer_key.get("max_score", TYPE_PATTERNS[qtype]["max_score_default"])

    if qtype == "T4_term_definition":
        # 三维关键词覆盖
        core_keywords = answer_key.get("core_keywords", [])
        element_keywords = answer_key.get("element_keywords", [])
        source_keywords = answer_key.get("source_keywords", [])

        core_score = sum(1 for kw in core_keywords if kw in text) / max(len(core_keywords), 1) if core_keywords else 0.5
        elem_score = sum(1 for kw in element_keywords if kw in text) / max(len(element_keywords), 1) if element_keywords else 0.5
        source_score = sum(1 for kw in source_keywords if kw in text) / max(len(source_keywords), 1) if source_keywords else 0.5

        weighted = core_score * 0.5 + elem_score * 0.3 + source_score * 0.2
        score = round(weighted * max_score, 1)

        return {
            "qtype": qtype,
            "qtype_name": "名词解释",
            "scoring_method": "三维关键词覆盖",
            "score": score,
            "max_score": max_score,
            "dimension_scores": {
                "核心概念准确(50%)": f"{core_score:.0%}",
                "要素完整性(30%)": f"{elem_score:.0%}",
                "法条依据(20%)": f"{source_score:.0%}"
            },
            "matched_keywords": [kw for kw in (core_keywords + element_keywords + source_keywords) if kw in text],
            "missing_keywords": [kw for kw in (core_keywords + element_keywords + source_keywords) if kw not in text],
            "explanation": answer_key.get("explanation", "")
        }

    elif qtype == "T5_short_answer":
        # 采分点覆盖
        if not scoring_points:
            # Fallback: 用关键词代替采分点
            scoring_points = [{"point": kw, "score_value": max_score / len(keywords)} for kw in keywords]

        total_possible = sum(p.get("score_value", max_score / len(scoring_points)) for p in scoring_points)
        earned = 0.0
        point_details = []

        for point in scoring_points:
            point_keywords = point.get("keywords", [])
            point_text = point.get("point", "")
            point_value = point.get("score_value", total_possible / len(scoring_points))

            # 关键词匹配
            if point_keywords:
                matched = sum(1 for kw in point_keywords if kw in text)
                coverage = matched / len(point_keywords) if point_keywords else 0
            else:
                # 无关键词则检查采分点文本本身
                coverage = 1.0 if point_text in text else 0.0

            # 至少50%关键词匹配才得分
            if coverage >= 0.5:
                earned += point_value
                status = "covered"
            elif coverage > 0:
                earned += point_value * coverage
                status = "partial"
            else:
                status = "missed"

            point_details.append({
                "point": point_text,
                "score_value": point_value,
                "coverage": f"{coverage:.0%}",
                "status": status
            })

        score = round(earned, 1)

        return {
            "qtype": qtype,
            "qtype_name": "简答题",
            "scoring_method": "采分点覆盖法",
            "score": score,
            "max_score": max_score,
            "coverage_rate": f"{len([p for p in point_details if p['status'] in ('covered', 'partial')])}/{len(scoring_points)}",
            "point_details": point_details,
            "explanation": answer_key.get("explanation", "")
        }

    return {"error": f"未知的半客观题类型: {qtype}"}


# =============================================================================
# 主入口
# =============================================================================
def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "用法: python question_type_classifier.py <输入文本> [--answer-key <JSON文件>] | --stdin",
            "supported_types": {k: v["name"] for k, v in TYPE_PATTERNS.items()}
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    text = None
    answer_key = None

    # 解析参数
    args = sys.argv[1:]
    if args[0] == '--stdin':
        text = sys.stdin.read()
    elif os.path.exists(args[0]):
        with open(args[0], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args[0]  # 直接当文本处理

    # 查找--answer-key参数
    for i, arg in enumerate(args):
        if arg == '--answer-key' and i + 1 < len(args):
            ak_path = args[i + 1]
            if os.path.exists(ak_path):
                with open(ak_path, 'r', encoding='utf-8') as f:
                    answer_key = json.load(f)

    if not text:
        print(json.dumps({"error": "未提供输入文本"}, ensure_ascii=False))
        sys.exit(1)

    # 1. 题型识别
    classification = classify_question(text)

    # 2. 路由评分
    result = {"classification": classification}

    qtype = classification["type"]
    if qtype in ("T1_single_choice", "T2_multi_choice", "T3_true_false"):
        result["scoring"] = score_objective_question(text, answer_key, qtype) if answer_key else {
            "error": "客观题需要答案键(--answer-key)", "requires_answer_key": True
        }
    elif qtype in ("T4_term_definition", "T5_short_answer"):
        result["scoring"] = score_semi_objective(text, answer_key, qtype) if answer_key else {
            "error": "半客观题需要答案键(--answer-key, 含scoring_points)", "requires_answer_key": True
        }
    else:
        result["scoring"] = {
            "method": "主观题(T6/T7/T8)需通过law_assignment_evaluator_v2.py进行五维加权评分",
            "route_to": "law_assignment_evaluator_v2.py"
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
