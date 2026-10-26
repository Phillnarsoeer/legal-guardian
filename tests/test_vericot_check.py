#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vericot_check.py 单元测试（标准库 unittest）

运行:
    python tests/test_vericot_check.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'scripts'))

import vericot_check as V  # noqa: E402

_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')


def valid_argument():
    return {
        'case': '堆放物致害',
        'premises': [
            {'id': 'p1', 'kind': 'rule', 'text': '堆放物致害适用过错推定',
             'grounded': True, 'source': '《民法典》第1255条'},
            {'id': 'p2', 'kind': 'fact', 'text': '李某堆放石子致张某滑倒受伤',
             'grounded': True, 'source': '监控、医疗记录'},
        ],
        'steps': [
            {'id': 's1', 'rule': 'subsumption', 'premises': ['p1', 'p2'],
             'conclusion': 'c1', 'conclusion_text': '李某应承担侵权责任'},
        ],
        'conclusion': 'c1',
    }


def full_argument():
    return {
        'case': '堆放物致害',
        'text': '李某在公共通道堆放石子，致张某滑倒受伤。',
        'variables': ['x'],
        'domain': ['李某'],
        'premises': [
            {'id': 'p1', 'kind': 'rule', 'text': '堆放物致害适用过错推定',
             'formula': 'forall x (Stacks(x) -> Liable(x))',
             'grounded': True, 'source': '《民法典》第1255条',
             'evidence': '李某在公共通道堆放石子'},
            {'id': 'p2', 'kind': 'fact', 'text': '李某堆放石子',
             'formula': 'Stacks(李某)',
             'grounded': True, 'source': '监控/医疗记录',
             'evidence': '李某在公共通道堆放石子'},
        ],
        'steps': [
            {'id': 's1', 'rule': 'subsumption', 'premises': ['p1', 'p2'],
             'conclusion': 'c1', 'formula': 'Liable(李某)',
             'conclusion_text': '李某应承担侵权责任'},
        ],
        'conclusion': 'c1',
    }


class VeriCoTTest(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, V.__file__] + list(args),
                              cwd=SKILL_ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=60, env=_ENV)

    def test_valid_argument(self):
        result = V.validate(valid_argument())
        self.assertTrue(result['valid'])
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['score'], 5.0)

    def test_full_valid_argument(self):
        result = V.validate(full_argument())
        self.assertEqual(result['meta']['mode'], 'full')
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual(result['score'], 5.0)
        self.assertEqual(result['fol']['steps'][0]['status'], 'entailed')
        self.assertEqual(result['fol']['final']['status'], 'entailed')

    def test_full_missing_fact_not_entailed(self):
        data = full_argument()
        data['domain'] = ['李某', '张某']
        data['premises'][1]['formula'] = 'Stacks(张某)'
        result = V.validate(data)
        self.assertFalse(result['valid'])
        self.assertIn('V15', {i['code'] for i in result['issues']})
        self.assertTrue(any(i.get('countermodel') for i in result['issues'] if i['code'] == 'V15'))

    def test_full_inconsistent_premises(self):
        data = full_argument()
        data['premises'][0]['formula'] = 'P'
        data['premises'][1]['formula'] = '~P'
        data['steps'][0]['formula'] = 'P'
        result = V.validate(data)
        self.assertIn('V14', {i['code'] for i in result['issues']})

    def test_full_parse_error(self):
        data = full_argument()
        data['premises'][0]['formula'] = 'forall x (Stacks(x) ->'
        result = V.validate(data)
        self.assertIn('V10', {i['code'] for i in result['issues']})
        self.assertFalse(result['valid'])

    def test_full_final_not_entailed(self):
        data = full_argument()
        data['steps'][0]['formula'] = 'Q(李某)'
        result = V.validate(data)
        self.assertIn('V16', {i['code'] for i in result['issues']})

    def test_full_ungrounded_evidence(self):
        data = full_argument()
        data['premises'][1]['evidence'] = '原文中没有这句话'
        result = V.validate(data)
        self.assertIn('V2', {i['code'] for i in result['issues']})

    def test_full_forward_reference(self):
        data = full_argument()
        data['steps'] = [
            {'id': 's1', 'rule': 'subsumption', 'premises': ['s2'],
             'conclusion': 'c1', 'formula': 'Liable(李某)', 'conclusion_text': '结论'},
            {'id': 's2', 'rule': 'subsumption', 'premises': ['p1', 'p2'],
             'conclusion': 'c2', 'formula': 'Liable(李某)', 'conclusion_text': '结论'},
        ]
        result = V.validate(data)
        self.assertIn('V17', {i['code'] for i in result['issues']})

    def test_ungrounded_premise(self):
        data = valid_argument()
        data['premises'][1]['grounded'] = False
        result = V.validate(data)
        self.assertFalse(result['valid'])
        self.assertIn('V2', {i['code'] for i in result['issues']})

    def test_unknown_premise_reference(self):
        data = valid_argument()
        data['steps'][0]['premises'] = ['p1', 'p9']
        result = V.validate(data)
        self.assertFalse(result['valid'])
        self.assertIn('V3', {i['code'] for i in result['issues']})

    def test_missing_final_conclusion(self):
        data = valid_argument()
        data['conclusion'] = 'c9'
        result = V.validate(data)
        self.assertIn('V5', {i['code'] for i in result['issues']})

    def test_contradictory_conclusions(self):
        data = valid_argument()
        data['steps'][0]['conclusion_text'] = '该合同有效，因此应继续履行。该合同无效。'
        result = V.validate(data)
        self.assertIn('V6', {i['code'] for i in result['issues']})

    def test_packet_shape(self):
        packet = V.build_packet('本案中……')
        self.assertIn('template', packet)
        self.assertIn('premises', packet['template'])
        self.assertIn('steps', packet['template'])

    def test_cli_json(self):
        data = valid_argument()
        tmp = tempfile.mkdtemp(prefix='lg_vericot_')
        try:
            path = os.path.join(tmp, 'arg.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            p = self._run(path, '--json')
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertTrue(out['valid'])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
