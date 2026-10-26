#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fol_engine.py — 无第三方依赖的一阶逻辑（FOL）小引擎
====================================================
用途：为 VeriCoT 完整版提供“形式化 → 有限域接地 → DPLL 可满足性 → 蕴涵检查”。

支持:
    - 原子：P、P(a)、P(a,b)
    - 连接词：~ / ¬、& / ∧、| / ∨、-> / →、<-> / ↔
    - 量词：forall / ∀、exists / ∃（必须带括号，如 ∀x (P(x) -> Q(x))）
    - 变量：由 variables 列表或量词绑定声明；其余标识符视为常量
    - 函数符号：不支持（保持函数无关；法律论证通常不需要）
    - 等词：不支持（用 Same(x,y) 谓词代替）

边界:
    - 有限域接地：常量来自 domain + 公式中出现的常量；域为空时使用 __d0
    - 接地后原子数超过 max_atoms 时返回 undecided，不假装证明
    - DPLL 是完备的（对函数无关有限域 FOL），但复杂度指数级；只适合小论证
"""

import re


class FOLParseError(Exception):
    pass


ID_RE = re.compile(r'[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*')
SYMBOLS = ('(', ')', ',', '~', '¬', '&', '∧', '|', '∨', '→', '↔', '∀', '∃')


def tokenize(text):
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if text.startswith('<->', i):
            tokens.append(('SYM', '<->'))
            i += 3
            continue
        if text.startswith('->', i):
            tokens.append(('SYM', '->'))
            i += 2
            continue
        if c in SYMBOLS:
            tokens.append(('SYM', c))
            i += 1
            continue
        m = ID_RE.match(text, i)
        if m:
            tokens.append(('ID', m.group(0)))
            i = m.end()
            continue
        raise FOLParseError('无法识别字符：%r（位置 %d）' % (c, i))
    tokens.append(('EOF', ''))
    return tokens


class Parser:
    def __init__(self, text, variables=None):
        self.tokens = tokenize(text)
        self.pos = 0
        self.variables = set(variables or [])
        self.bound = set()

    def peek(self):
        return self.tokens[self.pos]

    def take(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def accept(self, value):
        if self.peek()[1] == value:
            self.pos += 1
            return True
        return False

    def expect(self, value):
        tok = self.take()
        if tok[1] != value:
            raise FOLParseError('期望 %r，实际 %r' % (value, tok[1]))
        return tok

    def parse(self):
        formula = self.parse_iff()
        if self.peek()[0] != 'EOF':
            raise FOLParseError('多余内容：%r' % (self.peek()[1],))
        self._check_free(formula, set())
        return formula

    def parse_iff(self):
        left = self.parse_implies()
        while self.accept('<->') or self.accept('↔'):
            right = self.parse_implies()
            left = ('iff', left, right)
        return left

    def parse_implies(self):
        left = self.parse_or()
        if self.accept('->') or self.accept('→'):
            return ('implies', left, self.parse_implies())
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.accept('|') or self.accept('∨'):
            left = ('or', [left, self.parse_and()])
        return left

    def parse_and(self):
        left = self.parse_unary()
        while self.accept('&') or self.accept('∧'):
            left = ('and', [left, self.parse_unary()])
        return left

    def parse_unary(self):
        tok = self.peek()
        if tok[1] in ('~', '¬', 'not'):
            self.take()
            return ('not', self.parse_unary())
        if tok[1] in ('forall', '∀', 'exists', '∃'):
            self.take()
            var_tok = self.take()
            if var_tok[0] != 'ID':
                raise FOLParseError('量词后需要变量名')
            var = var_tok[1]
            self.expect('(')
            self.bound.add(var)
            body = self.parse_iff()
            self.bound.discard(var)
            self.expect(')')
            return ('forall' if tok[1] in ('forall', '∀') else 'exists', var, body)
        if tok[1] == '(':
            self.take()
            formula = self.parse_iff()
            self.expect(')')
            return formula
        return self.parse_atom()

    def parse_atom(self):
        tok = self.take()
        if tok[0] != 'ID':
            raise FOLParseError('期望谓词名，实际 %r' % (tok[1],))
        pred = tok[1]
        if pred == 'true':
            return ('true',)
        if pred == 'false':
            return ('false',)
        args = []
        if self.accept('('):
            if not self.accept(')'):
                args.append(self.parse_term())
                while self.accept(','):
                    args.append(self.parse_term())
                self.expect(')')
        return ('atom', pred, tuple(args))

    def parse_term(self):
        tok = self.take()
        if tok[0] != 'ID':
            raise FOLParseError('期望常量/变量，实际 %r' % (tok[1],))
        name = tok[1]
        if name in self.bound or name in self.variables:
            return ('var', name)
        return ('const', name)

    def _check_free(self, formula, bound):
        tag = formula[0]
        if tag == 'atom':
            for term in formula[2]:
                if term[0] == 'var' and term[1] not in bound:
                    raise FOLParseError('自由变量：%s' % term[1])
        elif tag in ('not',):
            self._check_free(formula[1], bound)
        elif tag in ('and', 'or'):
            for f in formula[1]:
                self._check_free(f, bound)
        elif tag in ('implies', 'iff'):
            self._check_free(formula[1], bound)
            self._check_free(formula[2], bound)
        elif tag in ('forall', 'exists'):
            self._check_free(formula[2], bound | {formula[1]})


def parse_formula(text, variables=None):
    return Parser(text, variables).parse()


def substitute(formula, var, const):
    tag = formula[0]
    if tag == 'atom':
        args = tuple(('const', const) if t == ('var', var) else t for t in formula[2])
        return ('atom', formula[1], args)
    if tag == 'not':
        return ('not', substitute(formula[1], var, const))
    if tag in ('and', 'or'):
        return (tag, [substitute(f, var, const) for f in formula[1]])
    if tag in ('implies', 'iff'):
        return (tag, substitute(formula[1], var, const), substitute(formula[2], var, const))
    if tag in ('forall', 'exists'):
        if formula[1] == var:
            return formula
        return (tag, formula[1], substitute(formula[2], var, const))
    return formula


def constants_in(formula):
    found = set()
    tag = formula[0]
    if tag == 'atom':
        for term in formula[2]:
            if term[0] == 'const':
                found.add(term[1])
    elif tag == 'not':
        found |= constants_in(formula[1])
    elif tag in ('and', 'or'):
        for f in formula[1]:
            found |= constants_in(f)
    elif tag in ('implies', 'iff'):
        found |= constants_in(formula[1])
        found |= constants_in(formula[2])
    elif tag in ('forall', 'exists'):
        found |= constants_in(formula[2])
    return found


def ground(formula, constants):
    tag = formula[0]
    if tag in ('true', 'false'):
        return formula
    if tag == 'atom':
        if any(t[0] == 'var' for t in formula[2]):
            raise FOLParseError('接地后仍有变量：%s' % (formula[1],))
        return formula
    if tag == 'not':
        return ('not', ground(formula[1], constants))
    if tag in ('and', 'or'):
        return (tag, [ground(f, constants) for f in formula[1]])
    if tag in ('implies', 'iff'):
        return (tag, ground(formula[1], constants), ground(formula[2], constants))
    if tag == 'forall':
        return ('and', [ground(substitute(formula[2], formula[1], c), constants)
                        for c in constants])
    if tag == 'exists':
        return ('or', [ground(substitute(formula[2], formula[1], c), constants)
                       for c in constants])
    raise FOLParseError('未知公式节点：%r' % (tag,))


def atoms_in(formula):
    found = set()
    tag = formula[0]
    if tag == 'atom':
        found.add(formula)
    elif tag == 'not':
        found |= atoms_in(formula[1])
    elif tag in ('and', 'or'):
        for f in formula[1]:
            found |= atoms_in(f)
    elif tag in ('implies', 'iff'):
        found |= atoms_in(formula[1])
        found |= atoms_in(formula[2])
    return found


def predicate_arities(formula):
    result = {}

    def merge(other):
        for name, arity in other.items():
            if name in result and result[name] != arity:
                raise FOLParseError('谓词 %s 元数不一致：%d vs %d' % (name, result[name], arity))
            result[name] = arity

    tag = formula[0]
    if tag == 'atom':
        merge({formula[1]: len(formula[2])})
    elif tag == 'not':
        merge(predicate_arities(formula[1]))
    elif tag in ('and', 'or'):
        for f in formula[1]:
            merge(predicate_arities(f))
    elif tag in ('implies', 'iff'):
        merge(predicate_arities(formula[1]))
        merge(predicate_arities(formula[2]))
    return result


def simplify(formula, assignment):
    tag = formula[0]
    if tag == 'true':
        return True
    if tag == 'false':
        return False
    if tag == 'atom':
        return assignment.get(formula)
    if tag == 'not':
        value = simplify(formula[1], assignment)
        return None if value is None else not value
    if tag == 'and':
        unknown = False
        for f in formula[1]:
            value = simplify(f, assignment)
            if value is False:
                return False
            if value is None:
                unknown = True
        return None if unknown else True
    if tag == 'or':
        unknown = False
        for f in formula[1]:
            value = simplify(f, assignment)
            if value is True:
                return True
            if value is None:
                unknown = True
        return None if unknown else False
    if tag == 'implies':
        return simplify(('or', [('not', formula[1]), formula[2]]), assignment)
    if tag == 'iff':
        return simplify(('and', [('implies', formula[1], formula[2]),
                                 ('implies', formula[2], formula[1])]), assignment)
    raise FOLParseError('未知公式节点：%r' % (tag,))


def _dpll(formulas, atom_list, assignment, depth=0):
    values = [simplify(f, assignment) for f in formulas]
    if any(v is False for v in values):
        return None
    if all(v is True for v in values):
        return assignment
    if depth > len(atom_list):
        return None
    atom = next((a for a in atom_list if a not in assignment), None)
    if atom is None:
        return None
    for value in (True, False):
        nxt = dict(assignment)
        nxt[atom] = value
        result = _dpll(formulas, atom_list, nxt, depth + 1)
        if result is not None:
            return result
    return None


def satisfiable(formulas, domain=None, max_atoms=2000):
    constants = set(domain or [])
    for f in formulas:
        constants |= constants_in(f)
    if not constants:
        constants = {'__d0'}
    constants = sorted(constants)
    grounded = [ground(f, constants) for f in formulas]
    atoms = set()
    for f in grounded:
        atoms |= atoms_in(f)
    if len(atoms) > max_atoms:
        return {'status': 'undecided', 'reason': '接地原子数 %d 超过上限 %d' % (len(atoms), max_atoms),
                'constants': constants, 'atoms': len(atoms)}
    atom_list = sorted(atoms, key=repr)
    model = _dpll(grounded, atom_list, {})
    if model is None:
        return {'status': 'unsat', 'constants': constants, 'atoms': len(atoms)}
    true_atoms = {a: v for a, v in model.items() if v}
    return {'status': 'sat', 'constants': constants, 'atoms': len(atoms),
            'model': true_atoms}


def entails(premises, conclusion, domain=None, max_atoms=2000):
    check = satisfiable(premises + [('not', conclusion)], domain, max_atoms)
    if check['status'] == 'unsat':
        return {'status': 'entailed', 'constants': check['constants'], 'atoms': check['atoms']}
    if check['status'] == 'sat':
        return {'status': 'not_entailed', 'countermodel': check.get('model', {}),
                'constants': check['constants'], 'atoms': check['atoms']}
    return {'status': 'undecided', 'reason': check.get('reason'), 'constants': check['constants'],
            'atoms': check['atoms']}


def format_atom(atom):
    if not atom[2]:
        return atom[1]
    return '%s(%s)' % (atom[1], ', '.join(t[1] for t in atom[2]))


def format_model(model):
    if not model:
        return '（空模型）'
    return '; '.join('%s=%s' % (format_atom(a), 'T' if v else 'F') for a, v in sorted(model.items(), key=repr))
