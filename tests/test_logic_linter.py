#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logic_linter.py 单元测试（标准库 unittest）

运行:
    python tests/test_logic_linter.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'tests'))

import logic_linter as L  # noqa: E402
import logic_fixtures as F  # noqa: E402

_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
_TAX = L.load_taxonomy()
_RUB = L.load_rubric()


class LogicLinterTest(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, L.__file__] + list(args),
                              cwd=SKILL_ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=60, env=_ENV)

    def test_taxonomy_completeness(self):
        self.assertEqual(len(_TAX['stages']), 5)
        self.assertEqual(len(_TAX['failure_types']), 4)
        self.assertEqual(len(_TAX['cells']), 20)
        ids = [c['id'] for c in _TAX['cells']]
        self.assertEqual(len(ids), len(set(ids)), '矩阵单元 ID 重复')
        for stage in ('S1', 'S2', 'S3', 'S4', 'S5'):
            self.assertEqual(sum(1 for c in _TAX['cells'] if c['stage'] == stage), 4)
        for ftype in ('T1', 'T2', 'T3', 'T4'):
            self.assertEqual(sum(1 for c in _TAX['cells'] if c['failure_type'] == ftype), 5)
        self.assertEqual(len(_TAX['checks']), 8)
        self.assertEqual(len(_TAX['mvp_checks']), 8)

    def test_fixtures(self):
        for fixture in F.FIXTURES:
            result = L.lint_text(fixture['text'], _TAX, _RUB)
            detected = {i['check_id'] for i in result['issues']}
            if fixture['clean']:
                self.assertEqual(detected, set(),
                                 '%s 应为干净样本，实际命中 %s' % (fixture['id'], detected))
            else:
                for expected in fixture['expected']:
                    self.assertIn(expected, detected,
                                  '%s 缺少期望检查 %s（实际 %s）' % (fixture['id'], expected, detected))

    def test_labor_contract_not_treated_as_repealed_contract_law(self):
        text = ('本案争议焦点是劳动合同解除是否合法。根据《劳动合同法》第四十八条规定，'
                '用人单位违法解除劳动合同的，应当支付赔偿金。本案中，甲公司在合同期内'
                '无正当理由解除与乙的劳动合同，乙要求继续履行。因此，甲公司应承担违法'
                '解除的赔偿责任。')
        result = L.lint_text(text, _TAX, _RUB)
        self.assertNotIn('L02', {i['check_id'] for i in result['issues']})

    def test_particle_gu_not_matched_inside_guyi(self):
        text = ('本案争议焦点是甲是否构成故意伤害罪。根据《刑法》第二百三十四条规定，'
                '故意伤害他人身体的，处三年以下有期徒刑。本案中，甲持刀刺伤乙致其重伤，'
                '主观上具有伤害故意。因此，甲构成故意伤害罪。')
        result = L.lint_text(text, _TAX, _RUB)
        self.assertNotIn('L05', {i['check_id'] for i in result['issues']})

    def test_mode_changes_gate_order(self):
        text = ('因此，甲应当承担全部责任。根据《民法通则》第九十条，合法的借贷关系受法律保护。'
                '甲与乙签订借款合同，约定年利率24%，乙到期未还。任何情况下，借款人都必须承担全部责任。'
                '合同履行期限届满后，甲多次催告，乙仍未履行。该合同约定了还款期限和利息计算方式，'
                '乙在期限届满后仍未支付任何款项。')
        student = L.lint_text(text, _TAX, _RUB, mode='student')
        audit = L.lint_text(text, _TAX, _RUB, mode='ai_audit')
        self.assertIn('S1', student['summary']['by_stage'])
        self.assertIn('S2', student['summary']['by_stage'])
        self.assertIn('先修争点层', student['summary']['gate_advice'])
        self.assertIn('先修规范层', audit['summary']['gate_advice'])

    def test_dedup_marks_downstream_as_derived(self):
        text = ('根据《民法通则》第九十条，合法的借贷关系受法律保护。借款人甲应当按照约定支付利息。'
                '民间借贷利率上限经历了从24%到LPR四倍的变化，司法实践通常以合同成立时的一年期LPR为基准。'
                '该约定系双方真实意思表示，借款到期后甲多次催告乙履行。因此，甲应支付利息。')
        result = L.lint_text(text, _TAX, _RUB)
        l04 = [i for i in result['issues'] if i['check_id'] == 'L04']
        self.assertTrue(l04, '应命中 L04')
        self.assertTrue(any(i.get('derived_from') for i in l04))
        self.assertGreaterEqual(result['summary']['derived_count'], 1)

    def test_batch_mode(self):
        tmp = tempfile.mkdtemp(prefix='lg_logic_batch_')
        try:
            by_id = {f['id']: f for f in F.FIXTURES}
            with open(os.path.join(tmp, 'a.txt'), 'w', encoding='utf-8') as f:
                f.write(by_id['clean_irac']['text'])
            with open(os.path.join(tmp, 'b.txt'), 'w', encoding='utf-8') as f:
                f.write(by_id['mixed']['text'])
            p = self._run('--batch', tmp, '--json')
            self.assertEqual(p.returncode, 0, p.stderr)
            data = json.loads(p.stdout)
            self.assertEqual(data['aggregate']['files'], 2)
            self.assertGreaterEqual(data['aggregate']['total_issues'], 3)
            out = os.path.join(tmp, 'results.jsonl')
            p2 = self._run('--batch', tmp, '--out', out)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            with open(out, 'r', encoding='utf-8') as f:
                self.assertEqual(len([line for line in f if line.strip()]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_article_out_of_range(self):
        text = ('本案争议焦点是合同效力。根据《民法典》第2000条，违反法律强制性规定的民事法律行为无效。'
                '本案中，甲与乙签订的合同违反法律强制性规定。因此，该合同无效。')
        result = L.lint_text(text, _TAX, _RUB)
        self.assertIn('L02', {i['check_id'] for i in result['issues']})
        self.assertEqual(result['red_flags'][0]['cell'], 'M22')

    def test_semantic_packet(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'clean_irac')
        packet = L.build_semantic_packet(fixture['text'], _TAX, '本案是否构成侵权？')
        self.assertEqual(len(packet['tasks']), 4)
        self.assertEqual({t['cell'] for t in packet['tasks']}, {'M12', 'M32', 'M42', 'M52'})
        self.assertIn('reviews', packet['response_schema'])

    def test_semantic_merge(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'clean_irac')
        text = fixture['text']
        review = {
            'reviews': [
                {'cell': 'M12', 'verdict': 'fail', 'evidence': '李某在公共通道堆放石子',
                 'why': '题目问的是合同效力，文本却分析侵权', 'fix': '回到合同效力争点',
                 'confidence': 0.82},
                {'cell': 'M42', 'verdict': 'unclear', 'evidence': '李某的行为与损害之间存在因果关系',
                 'why': '因果关系是否成立需结合鉴定', 'confidence': 0.3},
            ]
        }
        extra, applied = L.semantic_issues_from_review(text, review, _TAX, _RUB)
        self.assertEqual(applied, 2)
        self.assertEqual({i['check_id'] for i in extra}, {'S12', 'S42'})
        result = L.lint_text(text, _TAX, _RUB, extra_issues=extra)
        self.assertIn('S12', {i['check_id'] for i in result['issues']})
        self.assertTrue(any(i['check_id'] == 'S42' for i in result['human_queue']))

    def test_semantic_cli(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'clean_irac')
        p = self._run('--text', fixture['text'], '--semantic', '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        packet = json.loads(p.stdout)
        self.assertEqual(len(packet['tasks']), 4)

        review = {'reviews': [{'cell': 'M12', 'verdict': 'fail',
                               'evidence': '李某在公共通道堆放石子',
                               'why': '争点错位', 'confidence': 0.8}]}
        tmp = tempfile.mkdtemp(prefix='lg_semantic_')
        try:
            path = os.path.join(tmp, 'review.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(review, f, ensure_ascii=False)
            p2 = self._run('--text', fixture['text'], '--semantic-input', path, '--json')
            self.assertEqual(p2.returncode, 0, p2.stderr)
            data = json.loads(p2.stdout)
            self.assertEqual(data['summary']['semantic_reviews'], 1)
            self.assertIn('S12', {i['check_id'] for i in data['issues']})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_low_confidence_queue(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'missing_issue')
        p = self._run('--text', fixture['text'], '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertGreaterEqual(data['summary']['low_confidence_count'], 1)
        self.assertTrue(data['human_queue'])
        tmp = tempfile.mkdtemp(prefix='lg_queue_')
        try:
            out = os.path.join(tmp, 'queue.jsonl')
            p2 = self._run('--text', fixture['text'], '--queue-out', out)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            with open(out, 'r', encoding='utf-8') as f:
                self.assertGreaterEqual(len([line for line in f if line.strip()]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_score_bounds(self):
        for fixture in F.FIXTURES:
            result = L.lint_text(fixture['text'], _TAX, _RUB)
            score = result['summary']['logic_score']
            self.assertGreaterEqual(score, 1.0)
            self.assertLessEqual(score, 5.0)

    def test_heatmap_shape(self):
        result = L.lint_text(F.FIXTURES[0]['text'], _TAX, _RUB)
        self.assertEqual(set(result['matrix']), {'S1', 'S2', 'S3', 'S4', 'S5'})
        for stage, row in result['matrix'].items():
            self.assertEqual(set(row), {'T1', 'T2', 'T3', 'T4'})

    def test_repealed_law_is_red_flag_not_logic_score(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'repealed_law')
        result = L.lint_text(fixture['text'], _TAX, _RUB)
        self.assertEqual(result['summary']['logic_score'], 5.0)
        self.assertTrue(result['summary']['logic_major_error_free'])
        self.assertEqual(result['summary']['red_flag_count'], 1)
        self.assertEqual(result['red_flags'][0]['cell'], 'M22')
        self.assertEqual(result['red_flags'][0]['score_dimension'], 'accuracy')

    def test_cli_json(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'mixed')
        p = self._run('--text', fixture['text'], '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data['meta']['tool'], 'logic_linter')
        self.assertEqual(set(data['matrix']), {'S1', 'S2', 'S3', 'S4', 'S5'})
        self.assertGreaterEqual(data['summary']['total_issues'], 3)

    def test_cli_min_severity(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'mixed')
        p = self._run('--text', fixture['text'], '--json', '--min-severity', 'critical')
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data['summary']['visible_issues'], 0)
        self.assertEqual(data['issues'], [])
        self.assertGreaterEqual(data['summary']['total_issues'], 3)

    def test_text_output(self):
        fixture = next(f for f in F.FIXTURES if f['id'] == 'mixed')
        p = self._run('--text', fixture['text'])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('逻辑体检', p.stdout)
        self.assertIn('矩阵', p.stdout)
        self.assertIn('修复顺序', p.stdout)

    def test_empty_input(self):
        p = self._run('--text', '   ', '--json')
        self.assertEqual(p.returncode, 2)
        self.assertIn('error', json.loads(p.stdout))

    def test_missing_file(self):
        p = self._run('__no_such_logic_file__.txt', '--json')
        self.assertEqual(p.returncode, 2)
        self.assertIn('error', json.loads(p.stdout))


if __name__ == '__main__':
    unittest.main(verbosity=2)
