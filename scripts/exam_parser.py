#!/usr/bin/env python3
"""
法考真题解析器 (Exam Parser)
将2022-2025年法考客观题/主观题PDF转为LegalGuardian v4.0标准答案键JSON

用法:
    python exam_parser.py <PDF文件路径> --type objective|subjective [--output <输出JSON>]
"""

import sys, json, os, re

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def parse_objective_answers(pdf_text: str) -> list:
    """
    解析客观题答案部分
    格式: "51. 答案：ABD\n解析：..."
    """
    # 单次扫描同时提取 题号 + 答案 + 解析，避免两个近似正则对全文各跑一遍 finditer
    combined_pattern = re.compile(
        r'(\d+)[．.].*?答案[：:]\s*([A-Fa-f,，、\s]+?)(?:\n解析[：:]\s*(.*?))?(?=\n\d+[．.]|\Z)',
        re.DOTALL
    )

    answers = []
    for match in combined_pattern.finditer(pdf_text):
        qnum = int(match.group(1))
        answer = match.group(2).strip().upper().replace(',', '').replace('、', '').replace(' ', '')
        entry = {
            "id": f"Q{qnum:03d}",
            "question_number": qnum,
            "correct": answer,
            # 客观题：1-50 单选(T1)，51-85 多选(T2)；
            # 86+ 的不定项在当前答案键格式下同样沿用多选(T2) 的 schema，故无需单独分支
            "qtype": "T1_single_choice" if qnum <= 50 else "T2_multi_choice",
            "max_score": 1 if qnum <= 50 else 2
        }
        explanation = match.group(3)
        if explanation:
            entry["explanation"] = explanation.strip()[:500]
        answers.append(entry)

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
    output_path = None

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
    except ImportError:
        print(json.dumps({"error": "需要安装PyMuPDF: pip install pymupdf"}, ensure_ascii=False))
        sys.exit(1)

    try:
        with fitz.open(pdf_path) as doc:
            # 逐页收集文本后一次性 join，避免 O(pages^2) 的字符串拼接
            page_texts = []
            for page in doc:
                page_texts.append(page.get_text())
            text = "".join(page_texts)
    except Exception as e:
        # 覆盖损坏/加密等打开或读取失败的情况，返回JSON错误而非裸traceback
        print(json.dumps({"error": f"读取PDF失败(文件可能损坏或已加密): {e}"}, ensure_ascii=False))
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

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(json.dumps({"ok": True, "output": output_path, "total_questions": result["meta"]["total_questions"]}, ensure_ascii=False))
    else:
        print(output_json)


if __name__ == '__main__':
    main()
