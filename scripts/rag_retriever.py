#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案例库检索器 (Case RAG Retriever) — LegalGuardian v4.3.0

对人民法院案例库 5,515 个真实案例（test_data/rags/chunks.json）做
确定性关键词检索（无需外部依赖/嵌入模型），落实 SKILL.md 中
"案例库 RAG 检索"能力声明，为失效模式纠正、相似案例对比、
教学案例引用提供本地可复现的检索增强。

用法:
    python rag_retriever.py --query "民间借贷 利息上限" [-k 5] [--detail] [--stats]

输出: JSON — {meta, results:[{id, score, category, snippet, ...}]}

设计约束（竞赛铁律：确定性/可复现）:
    - 评分规则固定：标题命中×3 + 分类命中×2 + 正文命中×1
    - 排序：分数降序，同分按 id 升序；无随机采样
"""

import sys
import json
import os
import re
import time

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CHUNKS_PATH = os.path.join(_SCRIPT_DIR, '..', 'test_data', 'rags', 'chunks.json')
_CASES_PATH = os.path.join(_SCRIPT_DIR, '..', 'test_data', 'cases', 'all_cases.json')

_chunks_cache = None
_cases_cache = None


def load_chunks():
    """加载 5,515 个 RAG 检索块（模块级缓存）"""
    global _chunks_cache
    if _chunks_cache is None:
        with open(_CHUNKS_PATH, 'r', encoding='utf-8') as f:
            _chunks_cache = json.load(f)
    return _chunks_cache


def load_cases():
    """加载 5,515 案例完整元数据（模块级缓存，仅 --detail 时使用）"""
    global _cases_cache
    if _cases_cache is None:
        with open(_CASES_PATH, 'r', encoding='utf-8') as f:
            _cases_cache = json.load(f)
    return _cases_cache


def tokenize_query(query: str) -> list:
    """查询分词：按空白/标点切分，过滤空串与单字虚词"""
    parts = re.split(r'[\s,，、;；。:：()（）"\'《》]+', query)
    stopwords = {'的', '了', '与', '和', '及', '或', '在', '是', '根据', '请问', '一下', '什么', '如何', '是否', '我', '他', '她'}
    terms = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and p not in stopwords:
            terms.append(p)
    return terms


def score_chunk(chunk: dict, terms: list) -> int:
    """确定性评分：标题×3 + 分类×2 + 正文×1（同一词不重复计分）"""
    text = chunk.get('text', '')
    lines = text.split('\n')
    title_line = lines[0] if lines else ''
    cat = (chunk.get('category', '') or '') + (chunk.get('subcategory', '') or '')
    score = 0
    hits = {'title': [], 'category': [], 'body': []}
    for t in terms:
        if t in title_line:
            score += 3
            hits['title'].append(t)
        elif t in cat:
            score += 2
            hits['category'].append(t)
        elif t in text:
            score += 1
            hits['body'].append(t)
    return score, hits


def retrieve(query: str, top_k: int = 5, with_detail: bool = False) -> dict:
    """执行检索，返回确定性排序的 top-k 结果"""
    t0 = time.time()
    terms = tokenize_query(query)
    chunks = load_chunks()
    cases_by_no = None
    if with_detail:
        cases_by_no = {c.get('no'): c for c in load_cases()}

    scored = []
    for chunk in chunks:
        score, hits = score_chunk(chunk, terms)
        if score > 0:
            scored.append((score, chunk, hits))

    # 确定性排序：分数降序，同分按 id 升序
    scored.sort(key=lambda x: (-x[0], x[1].get('id', '')))

    results = []
    for score, chunk, hits in scored[:top_k]:
        item = {
            'id': chunk.get('id', ''),
            'score': score,
            'category': chunk.get('category', ''),
            'subcategory': chunk.get('subcategory', ''),
            'hit_terms': hits,
            'snippet': (chunk.get('text', '') or '')[:160],
        }
        if with_detail and cases_by_no:
            case = cases_by_no.get(chunk.get('id', ''))
            if case:
                item['detail'] = {
                    'title': case.get('title', ''),
                    'case_id': case.get('case_id', ''),
                    'court': case.get('court', ''),
                    'date': case.get('date', ''),
                    'trial': case.get('trial', ''),
                    'ruling': case.get('ruling', ''),
                }
            else:
                item['detail'] = {'full_text': chunk.get('text', '')}
        results.append(item)

    return {
        'meta': {
            'retriever': 'rag_retriever v4.3.0',
            'corpus_size': len(chunks),
            'query': query,
            'terms': terms,
            'top_k': top_k,
            'matched_chunks': len(scored),
            'elapsed_ms': round((time.time() - t0) * 1000, 1),
            'deterministic': True,
        },
        'results': results,
    }


def main():
    args = sys.argv[1:]
    query = None
    top_k = 5
    with_detail = False
    show_stats = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--query' and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        elif arg == '-k' and i + 1 < len(args):
            try:
                top_k = max(1, min(int(args[i + 1]), 50))
            except ValueError:
                pass
            i += 2
        elif arg == '--detail':
            with_detail = True
            i += 1
        elif arg == '--stats':
            show_stats = True
            i += 1
        else:
            i += 1

    if show_stats:
        chunks = load_chunks()
        cats = {}
        for c in chunks:
            cats[c.get('category', '未知')] = cats.get(c.get('category', '未知'), 0) + 1
        print(json.dumps({
            'meta': {'retriever': 'rag_retriever v4.3.0', 'corpus_size': len(chunks)},
            'categories': cats,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if not query:
        print(json.dumps({
            'error': '用法: python rag_retriever.py --query "<关键词>" [-k 5] [--detail] [--stats]'
        }, ensure_ascii=False))
        sys.exit(1)

    result = retrieve(query, top_k, with_detail)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
