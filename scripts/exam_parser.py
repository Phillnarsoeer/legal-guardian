#!/usr/bin/env python3
"""
法考真题解析器 (Exam Parser)
将2022-2025年法考客观题/主观题PDF转为LegalGuardian v4.0标准答案键JSON

用法:
    python exam_parser.py <PDF文件路径> --type objective|subjective [--output <输出JSON>]
"""

import sys, json, os, re


def parse_objective_answers(pdf_text: str) -> list:
    """
    解析客观题答案部分
    格式: "51. 答案：ABD\n解析：..."
    """
    answer_pattern = re.compile(
        r'(\d+)[．.].*?答案[：:]\s*([A-Fa-f,，、\s]+)',
        re.MULTILINE
    )
    explanation_pattern = re.compile(
        r'(\d+)[．.].*?答案[：:]\s*[A-Fa-f,，、\s]+\n解析[：:]\s*(.+?)(?=\n\d+[．.]|\Z)',
        re.DOTALL
    )

    answers = []
    for match in answer_pattern.finditer(pdf_text):
        qnum = int(match.group(1))
        answer = match.group(2).strip().upper().replace(',', '').replace('、', '').replace(' ', '')
        answers.append({
            "id": f"Q{qnum:03d}",
            "question_number": qnum,
            "correct": answer,
            "qtype": "T1_single_choice" if qnum <= 50 else "T2_multi_choice" if qnum <= 85 else "T2_multi_choice",
            "max_score": 1 if qnum <= 50 else 2
        })

    # 匹配解析
    for match in explanation_pattern.finditer(pdf_text):
        qnum = int(match.group(1))
        explanation = match.group(2).strip()
        # 找到对应answer更新explanation
        for ans in answers:
            if ans["question_number"] == qnum:
                ans["explanation"] = explanation[:500]
                break

    return answers


def parse_subjective_content(pdf_text: str) -> list:
    """
    解析主观题部分
    提取：题目+问题+参考答案作为采分点来源
    """
    questions = []

    # 查找"问题："→"参考答案"段
    qa_pattern = re.compile(
        r'问题[：:]\s*(.+?)\n参考答案\s*\n(.+?)(?=\n(?:问题[：:]|\Z))',
        re.DOTALL
    )

    for match in qa_pattern.finditer(pdf_text):
        q_text = match.group(1).strip()
        answer_text = match.group(2).strip()
        questions.append({
            "question": q_text[:300],
            "model_answer": answer_text[:500],
            "qtype": "T5_short_answer"
        })

    return questions


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "用法: python exam_parser.py <PDF> --type objective|subjective [--output out.json]"}, ensure_ascii=False))
        sys.exit(1)

    pdf_path = sys.argv[1]
    exam_type = "objective"

    for i, arg in enumerate(sys.argv):
        if arg == '--type' and i + 1 < len(sys.argv):
            exam_type = sys.argv[i + 1]
        if arg == '--output' and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    if not os.path.exists(pdf_path):
        print(json.dumps({"error": f"PDF文件不存在: {pdf_path}"}, ensure_ascii=False))
        sys.exit(1)

    # 提取PDF文本
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
    except ImportError:
        print(json.dumps({"error": "需要安装PyMuPDF: pip install pymupdf"}, ensure_ascii=False))
        sys.exit(1)

    result = {}

    if exam_type == "objective":
        answers = parse_objective_answers(text)
        result = {
            "meta": {
                "source": os.path.basename(pdf_path),
                "type": "objective",
                "format": "LegalGuardian v4.0 answer key",
                "total_questions": len(answers)
            },
            "answer_keys": answers
        }
    else:
        questions = parse_subjective_content(text)
        result = {
            "meta": {
                "source": os.path.basename(pdf_path),
                "type": "subjective",
                "format": "LegalGuardian v4.0 scoring points",
                "total_questions": len(questions)
            },
            "questions": questions
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
