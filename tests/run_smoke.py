#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LegalGuardian v5.0.0 功能冒烟测试运行器
=======================================
位置:   tests/run_smoke.py（与 skill 同仓，纯标准库，无第三方依赖）
用法:
    python tests/run_smoke.py              # 全量（含全量校准，约 1-2 分钟）
    python tests/run_smoke.py --quick      # 跳过耗时项（全量校准），约 20-40 秒
    python tests/run_smoke.py --verbose    # 失败项打印详情
    python tests/run_smoke.py --no-report  # 不写 tests/smoke_report.md

输出:   控制台 PASS/FAIL/KNOWN 表格 + tests/smoke_report.md（Markdown 版）
状态位:
    PASS   —— 符合预期
    FAIL   —— 意外失败（未预期，影响退出码 -> 1）
    KNOWN  —— 已知缺陷/声明不符（已记录在测试方案文档中，不影响退出码）

v5.0.0 变更:
    - 新增 S26 逻辑体检（干净样本 0 命中 / 混合样本 L01/L04/L08）
    - 新增 S27 VeriCoT 完整版（有效论证 valid / 缺失事实 V15）
    - 新增 D12 逻辑矩阵资产（20 单元 + 8 项检查）

v4.3.0 变更:
    - D9/D10 改为"精简断言"：reference/ 无 v2.0.0 残留、新增脚本齐全
    - S3/S4/S5 转正（F1/F17/F2 修复）
    - S14 口径修正：全量校准复现 A 级（26 项）
    - 新增 S21-S24：RAG 案例检索 / 模块D 三维规制 / 虚构法条红线 / 检索确定性

退出码: 0 = 无意外失败; 1 = 存在意外失败（KNOWN 不计）
"""
import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_ROOT, 'scripts')
TESTS_DIR = os.path.join(SKILL_ROOT, 'tests')
TEST_DATA = os.path.join(TESTS_DIR, 'test_data')
INSTALLED = os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'legal-guardian')

# 子进程统一 UTF-8，规避 Windows 控制台 GBK 乱码 / 管道断链
_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')

_TMP = tempfile.mkdtemp(prefix='lg_smoke_')
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))
_RESULTS = []          # 每个元素: (cid, name, group, status, detail, seconds)
_VERBOSE = False
_SKIP = set()          # 被 --quick 跳过的 cid


# ---------------------------------------------------------------- 工具函数

def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _frontmatter_ok():
    parts = _read(os.path.join(SKILL_ROOT, 'SKILL.md')).split('---')
    return len(parts) >= 3 and 'name: legal-guardian' in parts[1]


def _write(name, text):
    """在临时目录写输入文件，返回绝对路径。"""
    full = os.path.join(_TMP, name)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(text)
    return full


def run_script(script, *args, timeout=180):
    """在 skill 根目录运行 `python scripts/<script>.py <args>`，返回 (rc, stdout, stderr)。"""
    cmd = [sys.executable, os.path.join(SCRIPTS, script), *args]
    try:
        p = subprocess.run(cmd, cwd=SKILL_ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout, env=_ENV)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, '', 'TIMEOUT'


def extract_json(text):
    """容错解析脚本输出：用 raw_decode 解码首个完整 JSON 对象，忽略前后附加文本。

    raw_decode 由解释器自身处理字符串转义，避免手工括号计数在 \\\\uXXXX 等连续
    转义边界处出错（评审修复：原手写配对逻辑在双反斜杠场景有缺陷）。
    """
    text = text.strip()
    if not text:
        raise ValueError('empty output')
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start == -1:
        raise ValueError('no JSON object in output: %r' % text[:200])
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def _detect(path):
    rc, out, err = run_script('failure_detector.py', path, timeout=120)
    if rc != 0:
        raise RuntimeError('failure_detector rc=%s: %s' % (rc, (err or out)[-200:]))
    return extract_json(out)


def _fired_ids(det):
    return [k for k, v in det.get('detections', {}).items() if v.get('fired')]


# ---------------------------------------------------------------- 用例定义

def check(cid, name, group, fn, known=False, slow=False, timeout=180):
    return {
        'cid': cid, 'name': name, 'group': group, 'fn': fn,
        'known': known, 'slow': slow, 'timeout': timeout,
    }


CHECKS = [
    # ============ ENV 环境与元数据 ============
    check('E1', 'Python 版本 >= 3.9', 'ENV 环境与元数据',
          lambda: sys.version_info >= (3, 9)),
    check('E2', 'SKILL.md frontmatter 可解析且 name=legal-guardian', 'ENV 环境与元数据',
          lambda: _frontmatter_ok()),
    check('E3', 'manifest.yaml name/version = legal-guardian/5.0.0', 'ENV 环境与元数据',
          lambda: bool(re.search(r'name:\s*legal-guardian', _read(os.path.join(SKILL_ROOT, 'manifest.yaml'))))
          and bool(re.search(r'version:\s*5\.0\.0', _read(os.path.join(SKILL_ROOT, 'manifest.yaml'))))),
    check('E4', 'legal-guardian.skill 为合法 zip 且含精简包 8 项（不含 test_data/产品技术文档）', 'ENV 环境与元数据',
          lambda: _check_package(), timeout=120),
    check('E5', '已安装 skill 目录存在 (~/.claude/skills/legal-guardian)', 'ENV 环境与元数据',
          lambda: os.path.isdir(INSTALLED)),

    # ============ DATA 数据资产完整性 ============
    check('D1', '失效模式 F1-F24 齐全且连续', 'DATA 数据资产完整性',
          lambda: _check_f24()),
    check('D2', '安全检查清单恰为 8 项 (C1-C8)', 'DATA 数据资产完整性',
          lambda: len(_load('reference', 'safety_checklist.json').get('checklist', [])) == 8),
    check('D3', '提问模板恰为 5 个 (T1-T5)', 'DATA 数据资产完整性',
          lambda: len(_load('reference', 'correction_templates.json').get('templates', [])) == 5),
    check('D4', '题型评分标准 T1-T8 共 8 种', 'DATA 数据资产完整性',
          lambda: len(_load('reference', 'question_type_rubrics.json').get('question_types', {})) == 8),
    check('D5', '案例库 5515 例 (test_data/cases/all_cases.json)', 'DATA 数据资产完整性',
          lambda: len(_load('test_data/cases', 'all_cases.json')) == 5515, timeout=120),
    check('D6', 'RAG 检索块 5515 条 (test_data/rags/chunks.json)', 'DATA 数据资产完整性',
          lambda: len(_load('test_data/rags', 'chunks.json')) == 5515, timeout=120),
    check('D7', '训练样本 22060 + 验证 5515 (test_data/training)', 'DATA 数据资产完整性',
          lambda: _lines('test_data/training/train.jsonl') == 22060
          and _lines('test_data/training/val.jsonl') == 5515, timeout=120),
    check('D8', 'benchmark meta.total_items 与实际条目一致', 'DATA 数据资产完整性',
          lambda: _check_benchmark_meta()),
    check('D9', 'reference/ 已精简：无 v2.0.0 残留数据文件', 'DATA 数据资产完整性',
          lambda: _check_no_stale_reference()),
    check('D10', '新增脚本齐全：rag / regulation / report / statute / logic / vericot / fol', 'DATA 数据资产完整性',
          lambda: os.path.exists(os.path.join(SCRIPTS, 'rag_retriever.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'regulation_assessor.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'report_builder.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'statute_verifier.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'logic_linter.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'vericot_check.py'))
          and os.path.exists(os.path.join(SCRIPTS, 'fol_engine.py'))),
    check('D11', '报告面板齐全：report_panel.html + 3 份示例数据', 'DATA 数据资产完整性',
          lambda: _check_panel()),
    check('D12', '逻辑矩阵齐全：20 单元 + 8 项检查', 'DATA 数据资产完整性',
          lambda: _check_logic_assets()),

    # ============ SMOKE 脚本冒烟 ============
    check('S1', '失效检测: F1 样本命中 repealed_law', 'SMOKE 脚本冒烟',
          lambda: _s1()),
    check('S2', '失效检测: 多模式样本命中 F1', 'SMOKE 脚本冒烟',
          lambda: _detect(_response_text('sample_ai_response_multi.json')).get('detections', {}).get('F1', {}).get('fired') is True),
    check('S3', '失效检测: 干净样本零误报', 'SMOKE 脚本冒烟',
          lambda: _s3()),
    check('S4', '失效检测: F2 罪名定性降维可触发', 'SMOKE 脚本冒烟',
          lambda: _s4()),
    check('S5', '失效检测: 显式三段论文本不命中 F17', 'SMOKE 脚本冒烟',
          lambda: _s5()),
    check('S6', '纠正引擎: F1 纠正含实证依据 (铁律1)', 'SMOKE 脚本冒烟',
          lambda: _s6()),
    check('S7', '安全检查: 输出恰 8 项清单', 'SMOKE 脚本冒烟',
          lambda: _s7()),
    check('S8', '模板匹配: 废止法陷阱推荐 T4 前提挑战型', 'SMOKE 脚本冒烟',
          lambda: 'T4' in _tpl_ids('根据《民法通则》第X条我能要回利息吗')),
    check('S9', '模板匹配: 量刑预测推荐 T2 案例对比型', 'SMOKE 脚本冒烟',
          lambda: 'T2' in _tpl_ids('朋友故意伤害大概判几年')),
    check('S10', '作业评估 v2: 识别 T8 且给出分数', 'SMOKE 脚本冒烟',
          lambda: _s10()),
    check('S11', '红线规则: 引用已废止法 → D1 归零', 'SMOKE 脚本冒烟',
          lambda: _s11()),
    check('S12', '四维评分引擎: 输出 4 维 + 综合分', 'SMOKE 脚本冒烟',
          lambda: _s12()),
    check('S13', '校准 --quick: 复现评级 A (100%/MAE0.0)', 'SMOKE 脚本冒烟',
          lambda: _calib_grade(['--quick']), slow=True, timeout=300),
    check('S14', '校准全量: 复现评级 A (v5.0.0 全量 26 项)', 'SMOKE 脚本冒烟',
          lambda: _calib_grade([]), slow=True, timeout=300),
    check('S15', '答案键验证: 畸形键返回结构化错误', 'SMOKE 脚本冒烟',
          lambda: _s15()),
    check('S16', '法条检索: 离线命中本地知识库 (故意伤害)', 'SMOKE 脚本冒烟',
          lambda: _s16()),
    check('S17', '确定性: 同输入两次检测结果逐字节一致 (铁律8)', 'SMOKE 脚本冒烟',
          lambda: _s17()),
    check('S20', '模块E: F24 在知识点覆盖<80%时触发', 'SMOKE 脚本冒烟',
          lambda: _s20()),
    check('S21', '案例检索: RAG 命中民间借贷案例 (5515库)', 'SMOKE 脚本冒烟',
          lambda: _s21()),
    check('S22', '模块D: 三维规制评估输出 13 条目', 'SMOKE 脚本冒烟',
          lambda: _s22()),
    check('S23', '红线扩展: 虚构法条命中 → D1 归零', 'SMOKE 脚本冒烟',
          lambda: _s23()),
    check('S24', '确定性: RAG 两次检索逐字节一致', 'SMOKE 脚本冒烟',
          lambda: _s24()),
    check('S25', '报告构建器: 全链路输出 9 模块且 JSON 合法', 'SMOKE 脚本冒烟',
          lambda: _s25()),
    check('S26', '逻辑体检: 干净样本 0 命中，混合样本命中 L01/L04/L08', 'SMOKE 脚本冒烟',
          lambda: _s26()),
    check('S27', 'VeriCoT 完整版: 有效论证 valid，缺失事实命中 V15', 'SMOKE 脚本冒烟',
          lambda: _s27()),

    # ============ INTEG 集成链路 ============
    check('I1', '三阶段链路: 检测→纠正→安全 全通', 'INTEG 集成链路',
          lambda: _i1()),
    check('I2', '竞赛场景: 教学大纲审核推荐 T1+T4', 'INTEG 集成链路',
          lambda: _s18()),
]


def _load(*parts):
    with open(os.path.join(SKILL_ROOT, *parts), 'r', encoding='utf-8') as f:
        return json.load(f)


def _lines(*parts):
    with open(os.path.join(SKILL_ROOT, *parts), 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)


def _data(name):
    return os.path.join(TEST_DATA, name)


def _response_text(name):
    """从 sample JSON 提取 ai_response 字段写入临时文件。

    评审修复：此前直接把整个 sample JSON（含 scenario/expected_detection 等
    元数据）喂给 failure_detector，JSON 结构噪音会放大误报数量。这里只取
    待审的 AI 回复纯文本，确保 S1/S2/S3/S6/S7/I1 测的是"回复内容"而非"文件包装"。
    """
    with open(os.path.join(TEST_DATA, name), 'r', encoding='utf-8') as f:
        d = json.load(f)
    return _write('resp_' + name.replace('.json', '.txt'), d.get('ai_response', ''))


def _check_package():
    z = zipfile.ZipFile(os.path.join(SKILL_ROOT, 'legal-guardian.skill'))
    assert z.testzip() is None
    tops = {n.split('/')[0] for n in z.namelist()}
    req = {'manifest.yaml', 'SKILL.md', 'README.md', 'benchmark', 'reference', 'scripts', 'templates', 'tests'}
    # v5.0.0 精简包：大数据集（test_data）与产品技术文档仅存于仓库，不进安装包
    assert req <= tops, 'missing: %s' % (req - tops)
    assert 'test_data' not in tops, 'test_data 不应进入精简包'
    assert '产品技术文档' not in tops
    # 中文文件名不得乱码（v4.2.1 已知缺陷#12）
    for n in z.namelist():
        n.encode('utf-8')
    return True


def _check_no_stale_reference():
    stale = {'all_1000.json', 'case_chunks.json', 'case_knowledge_base.json', 'train.jsonl', 'val.jsonl'}
    ref_dir = os.path.join(SKILL_ROOT, 'reference')
    return not (stale & set(os.listdir(ref_dir)))


def _check_f24():
    fp = _load('reference', 'failure_patterns.json')
    pats = fp.get('patterns', []) + fp.get('patterns_v2', [])
    ids = [p.get('id') for p in pats]
    return len(ids) == 24 and ids == ['F%d' % i for i in range(1, 25)]


def _check_benchmark_meta():
    b = _load('benchmark/gold_standard', 'all_types_benchmark.json')
    return b.get('meta', {}).get('total_items') == len(b.get('benchmark_items', [])) + len(b.get('regression_tests', []))


def _s1():
    # v5.0.0：与 S2/S6/S7/I1 一致，只取 ai_response 纯文本，
    # 避免 sample JSON 元数据（含"已废止"字样）触发 F1 纠正文豁免。
    d = _detect(_response_text('sample_ai_response_f1.json'))
    f1 = d.get('detections', {}).get('F1', {})
    return f1.get('fired') is True and any(t.get('type') == 'repealed_law' for t in f1.get('detections', []))


def _s3():
    d = _detect(_response_text('sample_ai_response_clean.json'))
    return not _fired_ids(d)


def _s4():
    p = _write('f2.txt', '本案中，检察院指控被告人构成故意伤害罪，我们仅分析故意伤害罪。')
    return _detect(p).get('detections', {}).get('F2', {}).get('fired') is True


def _s5():
    text = ('根据您的问题，首先需要确认法律适用。您提到的《民法通则》已于2021年1月1日被《中华人民共和国民法典》'
            '正式取代，不再具有法律效力。本案应适用现行《民法典》合同编关于借款利息的规定。'
            '大前提：借款合同约定利率不得超过合同成立时一年期LPR的4倍；'
            '小前提：您与对方约定利率在LPR的4倍以内；结论：该约定合法有效。'
            '实务建议：收集借条原件、转账记录、聊天记录作为证据，注意三年诉讼时效。')
    return _detect(_write('f17.txt', text)).get('detections', {}).get('F17', {}).get('fired') is not True


def _s6():
    det = _detect(_response_text('sample_ai_response_f1.json'))
    det_path = _write('det.json', json.dumps(det, ensure_ascii=False))
    rc, out, err = run_script('correction_engine.py', det_path)
    if rc != 0:
        raise RuntimeError('correction_engine rc=%s: %s' % (rc, (err or out)[-200:]))
    c = extract_json(out)
    corr = c.get('corrections', {}).get('F1', {}).get('corrections', [])
    return bool(corr) and bool(corr[0].get('empirical_evidence'))


def _s7():
    resp = _response_text('sample_ai_response_f1.json')
    rc, out, err = run_script('safety_checker.py', resp,
                              '--detections', _write('det7.json', json.dumps(_detect(resp), ensure_ascii=False)))
    if rc != 0:
        raise RuntimeError('safety_checker rc=%s: %s' % (rc, (err or out)[-200:]))
    return extract_json(out).get('meta', {}).get('total_checks') == 8


def _tpl_ids(question):
    rc, out, err = run_script('template_matcher.py', question)
    if rc != 0:
        raise RuntimeError('template_matcher rc=%s: %s' % (rc, (err or out)[-200:]))
    t = extract_json(out)
    return [x.get('id') for x in t.get('recommended_templates', [])]


def _s10():
    rc, out, err = run_script('law_assignment_evaluator_v2.py', _data('sample_assignment.md'))
    if rc != 0:
        raise RuntimeError('v2 rc=%s: %s' % (rc, (err or out)[-200:]))
    a = extract_json(out)
    return a.get('classification', {}).get('type') == 'T8_case_analysis' and a.get('scoring', {}).get('raw_score', 0) > 0


def _s11():
    p = _write('redline.txt', '学生作业：根据《民法通则》第108条，本案债务人应当清偿债务。')
    rc, out, err = run_script('law_assignment_evaluator_v2.py', p)
    if rc != 0:
        raise RuntimeError('v2 rc=%s: %s' % (rc, (err or out)[-200:]))
    a = extract_json(out)
    dims = a.get('scoring', {}).get('dimension_scores', {})
    d1 = next((v for k, v in dims.items() if str(k).startswith('D1')), {})
    return d1.get('score') == 0


def _s12():
    rc, out, err = run_script('scoring_engine.py', _data('sample_ai_response_f1.json'))
    if rc != 0:
        raise RuntimeError('scoring_engine rc=%s: %s' % (rc, (err or out)[-200:]))
    s = extract_json(out)
    return len(s.get('dimensions', {})) >= 4 and 'overall_score' in s.get('meta', {})


def _calib_grade(extra):
    rc, out, err = run_script('calibrate_scoring.py', *extra, timeout=280)
    if rc != 0:
        raise RuntimeError('calibrate rc=%s: %s' % (rc, (err or out)[-200:]))
    return str(extract_json(out).get('overall_grade', '')).startswith('A')


def _s15():
    # 畸形答案键 -> 应返回结构化 JSON 错误而非原始 traceback（v4.2.1 健壮性声明）。
    # 该校验失败时退出码=1，但 stdout 是合法 JSON 且含 error 键——属于预期行为。
    p = _write('bad_key.json', json.dumps({'T1': {'Q1': {'answer': 'A'}}}))
    rc, out, err = run_script('answer_key_evaluator.py', '--validate', p)
    if rc != 0 and not out.strip():
        raise RuntimeError('ake rc=%s, 无输出: %s' % (rc, (err or '')[-200:]))
    parsed = extract_json(out)
    return 'error' in parsed


def _s16():
    rc, out, err = run_script('legal_db_fetcher.py', '--search', '故意伤害', timeout=120)
    if rc != 0:
        raise RuntimeError('legal_db rc=%s: %s' % (rc, (err or out)[-200:]))
    return int(extract_json(out).get('total_results', 0)) > 0


def _s17():
    resp = _response_text('sample_ai_response_f1.json')
    d1 = _detect(resp)
    d2 = _detect(resp)
    return json.dumps(d1, ensure_ascii=False, sort_keys=True) == json.dumps(d2, ensure_ascii=False, sort_keys=True)


def _s18():
    ids = _tpl_ids('审核一下这份教学大纲是否符合国家标准')
    return 'T1' in ids and 'T4' in ids


def _s20():
    text = '本教学大纲覆盖民法、刑法、宪法基础内容，包括犯罪构成、民事法律行为、合同制度、侵权责任、刑罚制度'
    return _detect(_write('syllabus.txt', text)).get('detections', {}).get('F24', {}).get('fired') is True


def _s21():
    rc, out, err = run_script('rag_retriever.py', '--query', '民间借贷 利息 上限', '-k', '3', timeout=120)
    if rc != 0:
        raise RuntimeError('rag_retriever rc=%s: %s' % (rc, (err or out)[-200:]))
    r = extract_json(out)
    return r.get('meta', {}).get('corpus_size') == 5515 and len(r.get('results', [])) > 0 \
        and r['results'][0].get('score', 0) >= 3


def _s22():
    rc, out, err = run_script('regulation_assessor.py', '--text',
                              '本工具提供法条验证与法律法规数据库检索、争议标注与替代罪名分析、量刑置信度披露与误差区间提示、LPR利息计算验证、面向法学生与非专业人士的差异化输出与风险提示；配套AI素养课程、标准化提问模板与普法宣传；工具透明可解释，遵循伦理守则，参与监管沙盒试点与分级认证备案。',
                              timeout=120)
    if rc != 0:
        raise RuntimeError('regulation_assessor rc=%s: %s' % (rc, (err or out)[-200:]))
    a = extract_json(out)
    return a.get('overall', {}).get('total') == 13 and bool(a.get('overall', {}).get('grade')) \
        and len(a.get('dimensions', {})) == 3


def _s23():
    p = _write('fictional.txt', '学生作业：根据《人格权侵害惩治条例》第5条，甲应当承担赔偿责任。')
    rc, out, err = run_script('law_assignment_evaluator_v2.py', p)
    if rc != 0:
        raise RuntimeError('v2 rc=%s: %s' % (rc, (err or out)[-200:]))
    a = extract_json(out)
    dims = a.get('scoring', {}).get('dimension_scores', {})
    d1 = next((v for k, v in dims.items() if str(k).startswith('D1')), {})
    return a.get('red_line_triggered') is True and d1.get('score') == 0


def _s24():
    def run():
        rc, out, err = run_script('rag_retriever.py', '--query', '正当防卫 故意伤害', '-k', '5', timeout=120)
        if rc != 0:
            raise RuntimeError('rag rc=%s: %s' % (rc, (err or out)[-200:]))
        d = extract_json(out)
        d.get('meta', {}).pop('elapsed_ms', None)  # 耗时字段逐次不同，比较时剔除
        return d
    return json.dumps(run(), ensure_ascii=False, sort_keys=True) \
        == json.dumps(run(), ensure_ascii=False, sort_keys=True)


def _check_logic_assets():
    """逻辑矩阵：5 阶段 × 4 失效 = 20 单元，8 项 MVP 检查，评分规则齐备"""
    tax = _load('reference', 'logic_taxonomy.json')
    rub = _load('reference', 'logic_rubric.json')
    return (len(tax.get('stages', [])) == 5
            and len(tax.get('failure_types', [])) == 4
            and len(tax.get('cells', [])) == 20
            and len(tax.get('checks', [])) == 8
            and len(tax.get('mvp_checks', [])) == 8
            and 'cell_score_dimension' in rub)


def _lint(path):
    rc, out, err = run_script('logic_linter.py', path, '--json')
    if rc != 0:
        raise RuntimeError('logic_linter rc=%s: %s' % (rc, (err or out)[-200:]))
    return extract_json(out)


def _s26():
    """逻辑体检：干净样本零命中；混合样本命中 L01/L04/L08"""
    import sys
    if TESTS_DIR not in sys.path:
        sys.path.insert(0, TESTS_DIR)
    from logic_fixtures import FIXTURES
    by_id = {f['id']: f for f in FIXTURES}
    clean = _lint(_write('logic_clean.txt', by_id['clean_irac']['text']))
    mixed = _lint(_write('logic_mixed.txt', by_id['mixed']['text']))
    ids = {i.get('check_id') for i in mixed.get('issues', [])}
    return clean.get('summary', {}).get('total_issues') == 0 and {'L01', 'L04', 'L08'} <= ids


def _s27():
    """VeriCoT 完整版：有效论证 valid；缺失事实命中 V15"""
    def arg():
        return {
            'text': '李某在公共通道堆放石子，致张某滑倒受伤。',
            'variables': ['x'],
            'domain': ['李某'],
            'premises': [
                {'id': 'p1', 'kind': 'rule', 'text': '堆放物致害',
                 'formula': 'forall x (Stacks(x) -> Liable(x))',
                 'grounded': True, 'source': '第1255条',
                 'evidence': '李某在公共通道堆放石子'},
                {'id': 'p2', 'kind': 'fact', 'text': '李某堆放石子',
                 'formula': 'Stacks(李某)', 'grounded': True, 'source': '证据',
                 'evidence': '李某在公共通道堆放石子'},
            ],
            'steps': [{'id': 's1', 'rule': 'subsumption', 'premises': ['p1', 'p2'],
                       'conclusion': 'c1', 'formula': 'Liable(李某)',
                       'conclusion_text': '李某应承担侵权责任'}],
            'conclusion': 'c1',
        }

    def run(data):
        path = _write('vericot_%s.json' % ('bad' if data['domain'] != ['李某'] else 'ok'),
                      json.dumps(data, ensure_ascii=False))
        rc, out, err = run_script('vericot_check.py', path, '--json', timeout=120)
        if rc != 0:
            raise RuntimeError('vericot rc=%s: %s' % (rc, (err or out)[-200:]))
        return extract_json(out)

    good = run(arg())
    bad_data = arg()
    bad_data['domain'] = ['李某', '张某']
    bad_data['premises'][1]['formula'] = 'Stacks(张某)'
    bad = run(bad_data)
    return (good.get('valid') is True and good.get('meta', {}).get('mode') == 'full'
            and bad.get('valid') is False
            and 'V15' in {i.get('code') for i in bad.get('issues', [])})


def _check_panel():
    """报告面板资产：HTML 存在、内嵌 3 份示例可解析、逻辑体检已接入"""
    panel_dir = os.path.join(SKILL_ROOT, 'panel')
    html_path = os.path.join(panel_dir, 'report_panel.html')
    if not os.path.exists(html_path):
        return False
    html = _read(html_path)
    if 'function renderLogic' not in html:
        return False
    for bid in ('demo-ai', 'demo-syllabus', 'demo-assignment'):
        m = re.search(r'id="' + bid + r'">(.*?)</script>', html, re.S)
        if not m:
            return False
        try:
            data = json.loads(m.group(1))
        except Exception:
            return False
        if bid == 'demo-ai' and 'logic' not in (data.get('modules') or {}):
            return False
    for f in ('demo_report.json', 'demo_syllabus.json', 'demo_assignment.json'):
        if not os.path.exists(os.path.join(panel_dir, f)):
            return False
    return True


def _s25():
    """报告构建器全链路：对 F1 样本生成报告，9 模块齐备且含检测命中"""
    rc, out, err = run_script('report_builder.py', _data('sample_ai_response_f1.json'),
                              '--query', '民间借贷 利息', timeout=180)
    if rc != 0:
        raise RuntimeError('report_builder rc=%s: %s' % (rc, (err or out)[-200:]))
    r = extract_json(out)
    mods = r.get('meta', {}).get('modules_included', [])
    expected = {'detection', 'corrections', 'safety', 'scoring',
                'assignment', 'templates', 'retrieval', 'regulation', 'logic'}
    if not expected <= set(mods):
        return False
    det = r.get('modules', {}).get('detection', {}).get('detections', {})
    return bool(det.get('F1', {}).get('fired'))


def _i1():
    resp = _response_text('sample_ai_response_f1.json')
    det = _detect(resp)
    det_path = _write('det_i1.json', json.dumps(det, ensure_ascii=False))
    rc, out, err = run_script('correction_engine.py', det_path)
    if rc != 0:
        raise RuntimeError('correction rc=%s: %s' % (rc, (err or out)[-200:]))
    c = extract_json(out)
    rc2, out2, err2 = run_script('safety_checker.py', resp, '--detections', det_path)
    if rc2 != 0:
        raise RuntimeError('safety rc=%s: %s' % (rc2, (err2 or out2)[-200:]))
    s = extract_json(out2)
    return c.get('summary', {}).get('total_corrections', 0) > 0 and s.get('meta', {}).get('total_checks') == 8


# ---------------------------------------------------------------- 执行与报告

def run_all(quick=False, verbose=False):
    global _VERBOSE, _SKIP
    _VERBOSE = verbose
    _SKIP = set()
    if quick:
        _SKIP = {c['cid'] for c in CHECKS if c.get('slow')}
    for c in CHECKS:
        if c['cid'] in _SKIP:
            _RESULTS.append((c['cid'], c['name'], c['group'], 'SKIP', '', 0.0))
            continue
        t0 = time.time()
        try:
            ok = bool(c['fn']())
            detail, status = '', 'PASS' if ok else ('KNOWN' if c.get('known') else 'FAIL')
        except Exception as e:  # noqa: BLE001
            ok = False
            detail = '%s: %s' % (type(e).__name__, e)
            status = 'KNOWN' if c.get('known') else 'FAIL'
        _RESULTS.append((c['cid'], c['name'], c['group'], status, detail, time.time() - t0))


def _fmt(cid, name, group, status, sec):
    mark = {'PASS': 'PASS ', 'FAIL': 'FAIL ', 'KNOWN': 'KNOWN', 'SKIP': 'SKIP '}[status]
    return '%s %-5s %s [%s]  %s  (%.1fs)' % (group, cid, mark, name, status, sec)


def emit(no_report=False):
    groups = []
    for c in CHECKS:
        if c['group'] not in groups:
            groups.append(c['group'])
    n_pass = sum(1 for r in _RESULTS if r[3] == 'PASS')
    n_fail = sum(1 for r in _RESULTS if r[3] == 'FAIL')
    n_known = sum(1 for r in _RESULTS if r[3] == 'KNOWN')
    n_skip = sum(1 for r in _RESULTS if r[3] == 'SKIP')
    total = len(_RESULTS)
    rc = 1 if n_fail else 0

    lines = []
    lines.append('=' * 66)
    lines.append('LegalGuardian v5.0.0 功能冒烟测试报告')
    lines.append('=' * 66)
    lines.append('时间:    %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('根目录:  %s' % SKILL_ROOT)
    lines.append('Python:  %s' % sys.version.split()[0])
    lines.append('模式:    %s' % ('quick（跳过全量校准）' if _SKIP else 'full'))
    lines.append('')
    for g in groups:
        lines.append('[%s]' % g)
        for r in _RESULTS:
            if r[2] != g:
                continue
            cid, name, status, detail, sec = r[0], r[1], r[3], r[4], r[5]
            mark = {'PASS': '  PASS', 'FAIL': '  FAIL', 'KNOWN': '  KNOWN', 'SKIP': '  SKIP'}[status]
            line = '  %s %-5s %s  (%.1fs)' % (mark, cid, name, sec)
            lines.append(line)
            if detail and (_VERBOSE or status == 'FAIL'):
                lines.append('        ↳ %s' % detail)
        lines.append('')
    lines.append('-' * 66)
    lines.append('汇总:  PASS=%d  FAIL=%d  KNOWN(已知缺陷)=%d  SKIP=%d   共 %d 项' % (n_pass, n_fail, n_known, n_skip, total))
    lines.append('结论:  %s' % ('存在 %d 项意外失败！' % n_fail if n_fail else '无意外失败；%d 项为已记录已知缺陷。' % n_known))
    lines.append('退出码: %d' % rc)
    lines.append('')

    text = '\n'.join(lines)
    print(text)

    if not no_report:
        report_path = os.path.join(TESTS_DIR, 'smoke_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('# LegalGuardian v5.0.0 冒烟测试报告\n\n')
            f.write('- 时间: %s\n' % time.strftime('%Y-%m-%d %H:%M:%S'))
            f.write('- 根目录: `%s`\n' % SKILL_ROOT)
            f.write('- 运行命令: `python tests/run_smoke.py%s`\n\n' % (' --quick' if _SKIP else ''))
            f.write('| 状态 | 编号 | 检查项 | 用时 |\n|---|---|---|---|\n')
            for r in _RESULTS:
                f.write('| %s | %s | %s | %.1fs |\n' % (r[3], r[0], r[1], r[5]))
            f.write('\n**汇总**: PASS=%d FAIL=%d KNOWN=%d SKIP=%d\n' % (n_pass, n_fail, n_known, n_skip))
            f.write('\n`FAIL` = 意外失败；`KNOWN` = 已记录已知缺陷（详见测试方案文档"已知问题清单"）。\n')
        print('报告已写入: %s' % report_path)
    return rc


def main():
    ap = argparse.ArgumentParser(description='LegalGuardian v5.0.0 功能冒烟测试')
    ap.add_argument('--quick', action='store_true', help='跳过耗时项（全量校准）')
    ap.add_argument('--verbose', action='store_true', help='失败项打印详情')
    ap.add_argument('--no-report', action='store_true', help='不写 smoke_report.md')
    args = ap.parse_args()
    run_all(quick=args.quick, verbose=args.verbose)
    sys.exit(emit(no_report=args.no_report))


if __name__ == '__main__':
    main()
