#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
statute_verifier.py 单元测试（标准库 unittest，无第三方依赖）

运行:
    python tests/test_statute_verifier.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL_ROOT, 'scripts', 'statute_verifier.py')
SEED = os.path.join(SKILL_ROOT, 'reference', 'statutes_seed.json')

_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')


class StatuteVerifierTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix='lg_verify_')

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, SCRIPT] + list(args) + ['--home', self.home]
        return subprocess.run(cmd, cwd=SKILL_ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=60, env=_ENV)

    def _json(self, *args):
        p = self._run(*(list(args) + ['--json']))
        self.assertEqual(p.returncode, 0, p.stderr or p.stdout)
        return json.loads(p.stdout)

    def test_active_card(self):
        card = self._json('--law', '民法典', '--article', '第1165条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'active_in_range')
        self.assertEqual(pre['article_number'], 1165)
        self.assertEqual(pre['f_pattern'], None)
        self.assertEqual(len(card['checklist']), 5)
        self.assertEqual(card['links']['official_search'], 'https://flk.npc.gov.cn/search')
        self.assertEqual(card['suggested_verdict']['value'], 'active')
        self.assertIn('flk.npc.gov.cn', card['links']['bing_site_search'])

    def test_repealed_law(self):
        card = self._json('--law', '民法通则', '--article', '第90条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'repealed')
        self.assertEqual(pre['f_pattern'], 'F1')
        self.assertEqual(pre['severity'], 'critical')
        self.assertIn('民法典', pre['replaced_by'])
        self.assertEqual(card['suggested_verdict']['value'], 'repealed')

    def test_fictional_law(self):
        card = self._json('--law', '人格权侵害惩治条例', '--article', '第5条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'fictional')
        self.assertEqual(pre['f_pattern'], 'F1')
        self.assertEqual(pre['severity'], 'critical')

    def test_article_out_of_range(self):
        card = self._json('--law', '民法典', '--article', '第2000条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'article_out_of_range')
        self.assertEqual(pre['f_pattern'], 'F1')
        self.assertFalse(pre['in_range'])
        self.assertEqual(card['suggested_verdict']['value'], 'not_found')

    def test_chinese_numeral_article(self):
        card = self._json('--law', '民法典', '--article', '第一千一百六十五条')
        self.assertEqual(card['offline_precheck']['article_number'], 1165)

    def test_unknown_law(self):
        card = self._json('--law', '某地方性法规', '--article', '第3条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'unknown')
        self.assertEqual(pre['f_pattern'], 'F5')
        self.assertEqual(card['suggested_verdict']['value'], 'unverified')

    def test_unparsable_article(self):
        card = self._json('--law', '民法典', '--article', '第X条')
        pre = card['offline_precheck']
        self.assertEqual(pre['kind'], 'article_unparsed')
        self.assertEqual(pre['f_pattern'], 'F5')
        self.assertEqual(card['suggested_verdict']['value'], 'unverified')

    def test_query_parsing(self):
        card = self._json('--query', '民法典 第1165条')
        self.assertEqual(card['query']['law'], '民法典')
        self.assertEqual(card['query']['article'], '第1165条')
        self.assertEqual(card['offline_precheck']['kind'], 'active_in_range')

    def test_record_and_list(self):
        p = self._run('--law', '民法典', '--article', '第1165条', '--record',
                      '--verdict', 'active', '--verifier', '测试员', '--note', '官网核对')
        self.assertEqual(p.returncode, 0, p.stderr or p.stdout)
        self.assertIn('已记录核验', p.stdout)

        path = os.path.join(self.home, 'verifications.jsonl')
        self.assertTrue(os.path.exists(path))
        with open(path, 'r', encoding='utf-8') as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), 1)
        rec = lines[0]
        self.assertEqual(rec['verdict'], 'active')
        self.assertEqual(rec['verdict_label'], '有效')
        self.assertEqual(rec['verifier'], '测试员')
        self.assertEqual(rec['article_number'], 1165)
        self.assertRegex(rec['checked_at'], r'^\d{4}-\d{2}-\d{2}T')

        listing = self._json('--list')
        self.assertEqual(listing['total'], 1)
        self.assertEqual(listing['records'][0]['id'], rec['id'])

        stats = self._json('--stats')
        self.assertEqual(stats['total'], 1)
        self.assertEqual(stats['by_verdict'].get('active'), 1)

    def test_record_requires_verdict(self):
        p = self._run('--law', '民法典', '--record')
        self.assertEqual(p.returncode, 2)
        self.assertIn('--verdict', p.stderr)

    def test_pending_queue(self):
        p = self._run('--law', '某地方性法规', '--article', '第3条', '--record',
                      '--verdict', 'unverified', '--verifier', '测试员')
        self.assertEqual(p.returncode, 0, p.stderr or p.stdout)
        pending = self._json('--pending')
        self.assertEqual(pending['total'], 1)
        self.assertIn('未能核验', '；'.join(pending['records'][0]['reasons']))

    def test_seed_structure(self):
        with open(SEED, 'r', encoding='utf-8') as f:
            seed = json.load(f)
        self.assertTrue(seed['meta']['version'].startswith('seed-'))
        self.assertGreaterEqual(len(seed['laws']), 20)
        self.assertGreaterEqual(len(seed['repealed']), 10)
        names = [law['name'] for law in seed['laws']]
        self.assertEqual(len(names), len(set(names)), '种子库法律名称重复')
        for law in seed['laws']:
            self.assertIn(law['status'], ('active',))


if __name__ == '__main__':
    unittest.main(verbosity=2)
