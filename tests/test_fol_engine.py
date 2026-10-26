#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fol_engine.py 单元测试（标准库 unittest）

运行:
    python tests/test_fol_engine.py
"""

import os
import sys
import unittest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, 'scripts'))

import fol_engine as F  # noqa: E402


class FOLEngineTest(unittest.TestCase):
    def test_parse_atom_and_implication(self):
        self.assertEqual(F.parse_formula('P'), ('atom', 'P', ()))
        self.assertEqual(F.parse_formula('P(a)'), ('atom', 'P', (('const', 'a'),)))
        f = F.parse_formula('P(a) -> Q(a)')
        self.assertEqual(f[0], 'implies')

    def test_modus_ponens_entailed(self):
        p = F.parse_formula('P')
        q = F.parse_formula('Q')
        imp = F.parse_formula('P -> Q')
        result = F.entails([p, imp], q)
        self.assertEqual(result['status'], 'entailed')

    def test_converse_not_entailed(self):
        p = F.parse_formula('P')
        q = F.parse_formula('Q')
        imp = F.parse_formula('P -> Q')
        result = F.entails([imp, q], p)
        self.assertEqual(result['status'], 'not_entailed')
        self.assertTrue(result['countermodel'])

    def test_universal_syllogism(self):
        rule = F.parse_formula('forall x (Man(x) -> Mortal(x))')
        fact = F.parse_formula('Man(socrates)')
        conclusion = F.parse_formula('Mortal(socrates)')
        self.assertEqual(F.entails([rule, fact], conclusion)['status'], 'entailed')

    def test_contradiction_unsat(self):
        p = F.parse_formula('P')
        not_p = F.parse_formula('~P')
        self.assertEqual(F.satisfiable([p, not_p])['status'], 'unsat')

    def test_arity_mismatch_raises(self):
        with self.assertRaises(F.FOLParseError):
            F.predicate_arities(F.parse_formula('P(a) & P(a,b)'))

    def test_free_variable_rejected(self):
        with self.assertRaises(F.FOLParseError):
            F.parse_formula('P(x)', variables=['x'])

    def test_exists(self):
        exists = F.parse_formula('exists x (P(x))')
        fact = F.parse_formula('P(a)')
        self.assertEqual(F.entails([fact], exists)['status'], 'entailed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
