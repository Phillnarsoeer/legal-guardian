#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statute Verifier — 法条时效性人工核验助手（离线优先，零第三方依赖）
====================================================================
定位：不抓取、不调用任何官方接口，只做三件事——
  1. 生成官方检索入口与检索词（链接）
  2. 依据本地种子库做条文号/废止法的离线预检（清单）
  3. 把人工核验结论追加写入本地审计日志（留痕）

用法:
    # 生成核验卡
    python scripts/statute_verifier.py --law "民法典" --article "第1165条"

    # 记录人工核验结论
    python scripts/statute_verifier.py --law "民法典" --article "第1165条" \
        --record --verdict active --verifier "张三" --note "官网核对，2026-10-26"

    # 查看记录 / 统计 / 待复核队列
    python scripts/statute_verifier.py --list
    python scripts/statute_verifier.py --stats
    python scripts/statute_verifier.py --pending --stale-days 180

设计约束:
    - 离线预检不是有效性结论；只有 --record 写入的人工结论才算核验结果。
    - 记录默认存于 ~/.legalguardian/verifications.jsonl，可用 --home 覆盖。
    - 不打包任何法规全文，不联网，不依赖 Playwright。
"""

import argparse
import json
import os
import re
import sys
import uuid
import webbrowser
from collections import Counter
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


SCHEMA_VERSION = '1.0'
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference', 'statutes_seed.json')
OFFICIAL_SEARCH = 'https://flk.npc.gov.cn/search'
OFFICIAL_HOME = 'https://flk.npc.gov.cn/'
DEFAULT_HOME = os.path.join(os.path.expanduser('~'), '.legalguardian')

VERDICTS = {
    'active': '有效',
    'repealed': '已废止',
    'amended': '已修改（需按现行版本）',
    'pending': '尚未生效',
    'not_found': '查无此文',
    'unverified': '未能核验',
}

CHECKLIST = [
    {'id': 1, 'item': '法名全称与制定机关是否一致'},
    {'id': 2, 'item': '条文号是否存在、内容是否对应'},
    {'id': 3, 'item': '时效状态：有效 / 已废止 / 已修改 / 尚未生效'},
    {'id': 4, 'item': '公布日期与施行日期'},
    {'id': 5, 'item': '最新修正/修订版本（是否引用了旧版本）'},
]

SEVERITY_ICON = {
    'critical': '🔴',
    'high': '🟠',
    'medium': '🟡',
    'none': '✅',
    'unknown': '❔',
}

SEVERITY_LABEL = {
    'critical': '极高',
    'high': '高',
    'medium': '中',
    'none': '无',
    'unknown': '未知',
}


# ---------------------------------------------------------------- 基础工具

def normalize_law(name):
    """规范化法律名称：去书名号、去“中华人民共和国”前缀、去空白。"""
    s = (name or '').strip()
    s = s.strip('《》').strip()
    s = s.replace('中华人民共和国', '')
    s = re.sub(r'[\s\u3000·•]', '', s)
    return s


_CN_DIGITS = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}
_CN_UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10000}


def cn_number(text):
    """中文数字转整数（支持到万位），失败返回 None。"""
    if not text:
        return None
    total, section, number = 0, 0, 0
    for ch in text:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if unit == 10000:
                section = (section + number) * unit
                total += section
                section = 0
            else:
                if number == 0:
                    number = 1
                section += number * unit
            number = 0
        else:
            return None
    return total + section + number


def parse_article(article):
    """从“第1165条 / 1165 / 第一千一百六十五条”提取条文序号。"""
    if article is None:
        return None
    s = str(article).strip()
    if not s:
        return None
    m = re.search(r'第\s*([0-9零〇一二两三四五六七八九十百千万]+)\s*条', s)
    token = m.group(1) if m else s
    if token.isdigit():
        return int(token)
    return cn_number(token)


def split_query(query):
    """把“民法典 第1165条”拆成 (law, article)。"""
    q = (query or '').strip()
    m = re.search(r'第\s*[0-9零〇一二两三四五六七八九十百千万]+\s*条', q)
    if m:
        article = m.group(0)
        law = (q[:m.start()] + q[m.end():]).strip(' ，,;；')
        return law, article
    return q, None


def load_seed(path=None):
    seed_path = os.path.abspath(path) if path else os.path.abspath(SEED_PATH)
    with open(seed_path, 'r', encoding='utf-8') as f:
        seed = json.load(f)
    index = {}

    def _add(entry, kind):
        keys = [entry.get('name', ''), entry.get('full_name', '')] + list(entry.get('aliases', []))
        for key in keys:
            norm = normalize_law(key)
            if norm:
                item = dict(entry)
                item['_kind'] = kind
                index[norm] = item

    for law in seed.get('laws', []):
        _add(law, 'active')
    for law in seed.get('repealed', []):
        _add(law, 'repealed')
    for law in seed.get('fictional', []):
        _add(law, 'fictional')
    return seed, index


def lookup_law(name, index):
    norm = normalize_law(name)
    if not norm:
        return None
    return index.get(norm)


# ---------------------------------------------------------------- 离线预检

def precheck(law, article, index):
    """基于本地种子库做预检，返回结构化的提示（不构成法律结论）。"""
    entry = lookup_law(law, index)
    article_no = parse_article(article)
    result = {
        'matched': bool(entry),
        'law_key': normalize_law(law),
        'law_full_name': entry.get('full_name') if entry else (law or ''),
        'article_number': article_no,
        'article_count': None,
        'in_range': None,
        'status': 'unknown',
        'kind': 'unknown',
        'f_pattern': 'F5',
        'severity': 'medium',
        'message': '',
        'entry': entry,
    }

    if not entry:
        result['message'] = ('种子库未收录该法律。可能是地方性法规、部门规章或虚构法律；'
                             '请用官方入口人工确认名称、时效与条文号。')
        return result

    kind = entry.get('_kind')
    result['article_count'] = entry.get('article_count')
    result['effective_date'] = entry.get('effective_date')
    result['latest_amendment'] = entry.get('latest_amendment')

    if kind == 'repealed':
        result.update({
            'status': 'repealed',
            'kind': 'repealed',
            'f_pattern': 'F1',
            'severity': 'critical',
            'repealed_date': entry.get('repealed_date'),
            'replaced_by': entry.get('replaced_by'),
            'message': ('该法已于 %s 废止，由《%s》取代。若 AI 仍将其作为现行法引用，触发 F1（法条幻视）。'
                        % (entry.get('repealed_date') or '未知日期', entry.get('replaced_by') or '未知法律')),
        })
        return result

    if kind == 'fictional':
        note = entry.get('note') or '种子库标记为不存在或名称有误的法律。'
        correct = entry.get('correct_name')
        extra = ('正确名称应为《%s》。' % correct) if correct else ''
        result.update({
            'status': 'fictional',
            'kind': 'fictional',
            'f_pattern': 'F1',
            'severity': 'critical',
            'correct_name': correct,
            'message': note + extra + '若 AI 将其作为法律依据，触发 F1。',
        })
        return result

    # active
    result['status'] = 'active'
    if article and article_no is None:
        result.update({
            'kind': 'article_unparsed',
            'f_pattern': 'F5',
            'severity': 'medium',
            'message': ('无法解析条文号“%s”。支持“第1165条”“1165”“第一千一百六十五条”等写法；'
                        '请改用阿拉伯数字后重试。' % article),
        })
        return result
    if article_no is not None:
        if article_no < 1:
            result.update({
                'kind': 'article_out_of_range',
                'f_pattern': 'F1',
                'severity': 'critical',
                'in_range': False,
                'message': '条文号小于 1，属于无效条文号。',
            })
            return result
        if entry.get('article_count'):
            result['in_range'] = article_no <= entry['article_count']
            if not result['in_range']:
                result.update({
                    'kind': 'article_out_of_range',
                    'f_pattern': 'F1',
                    'severity': 'critical',
                    'message': ('第 %d 条超出《%s》条文总数 %d 条，明显越界，疑似虚构条文。'
                                % (article_no, result['law_full_name'], entry['article_count'])),
                })
                return result
            result.update({
                'kind': 'active_in_range',
                'f_pattern': None,
                'severity': 'none',
                'message': ('种子库收录为现行法；第 %d 条在 1–%d 条范围内。仍需人工确认最新修正与时效。'
                            % (article_no, entry['article_count'])),
            })
            return result
        result.update({
            'kind': 'active_range_unknown',
            'f_pattern': None,
            'severity': 'none',
            'message': '种子库收录为现行法；未收录条文总数，无法做越界预检，仍需人工核对。',
        })
        return result

    result.update({
        'kind': 'active_no_article',
        'f_pattern': None,
        'severity': 'none',
        'message': '种子库收录为现行法；未指定条文号，仅核对法律名称与时效。',
    })
    return result


# ---------------------------------------------------------------- 链接与卡片

def build_links(law_full_name, article):
    keyword = (law_full_name or '').strip()
    if article:
        keyword = (keyword + ' ' + article).strip()
    return {
        'search_keyword': keyword,
        'official_search': OFFICIAL_SEARCH,
        'official_home': OFFICIAL_HOME,
        'bing_site_search': 'https://www.bing.com/search?q=' + _quote('site:flk.npc.gov.cn ' + keyword),
    }


def _quote(text):
    from urllib.parse import quote
    return quote(text, safe='')


def _quote_arg(text):
    return '"' + str(text).replace('"', '\\"') + '"'


def suggest_verdict(pre):
    """根据离线预检给出建议结论，仅作为命令行示例，不代替人工判断。"""
    kind = pre.get('kind')
    if kind == 'repealed':
        return 'repealed'
    if kind in ('fictional', 'article_out_of_range'):
        return 'not_found'
    if kind in ('unknown', 'article_unparsed'):
        return 'unverified'
    return 'active'


def build_record_command(law, article, verifier, verdict):
    parts = ['python', 'scripts/statute_verifier.py', '--law', _quote_arg(law)]
    if article:
        parts += ['--article', _quote_arg(article)]
    parts += ['--record', '--verdict', verdict, '--verifier', _quote_arg(verifier or '你的名字')]
    parts += ['--note', _quote_arg('官网核对：法名/条文/时效/施行日/版本')]
    return ' '.join(parts)


def build_card(law, article, seed, index, verifier):
    pre = precheck(law, article, index)
    links = build_links(pre['law_full_name'], article)
    suggested_verdict = suggest_verdict(pre)
    card = {
        'schema_version': SCHEMA_VERSION,
        'query': {
            'law': law,
            'article': article,
            'law_key': pre['law_key'],
            'search_keyword': links['search_keyword'],
        },
        'seed': {
            'version': seed.get('meta', {}).get('version'),
            'updated': seed.get('meta', {}).get('updated'),
            'notice': seed.get('meta', {}).get('notice'),
        },
        'offline_precheck': {k: v for k, v in pre.items() if k != 'entry'},
        'links': links,
        'checklist': CHECKLIST,
        'record_command': build_record_command(law, article, verifier, suggested_verdict),
        'suggested_verdict': {
            'value': suggested_verdict,
            'label': VERDICTS[suggested_verdict],
            'basis': '基于离线预检的建议值，请在人工核对后修改为真实结论',
        },
        'verdict_options': [{'value': k, 'label': v} for k, v in VERDICTS.items()],
        'notice': ('离线预检只用于发现明显问题（废止法、条文号越界、虚构法名），'
                   '不构成有效性结论。请打开官方入口核对后，再用 --record 写入人工结论。'),
    }
    return card, pre


# ---------------------------------------------------------------- 输出：核验卡

def render_card(card):
    pre = card['offline_precheck']
    q = card['query']
    links = card['links']
    icon = SEVERITY_ICON.get(pre.get('severity', 'unknown'), '❔')
    width = 64
    lines = []
    lines.append('=' * width)
    title = ' 法条核验卡 · %s' % (q.get('law') or '')
    if q.get('article'):
        title += ' ' + q['article']
    lines.append(title)
    lines.append('=' * width)
    lines.append('规范名称 : %s' % (pre.get('law_full_name') or q.get('law')))
    lines.append('检索词   : %s' % links['search_keyword'])
    lines.append('官方入口 : %s' % links['official_search'])
    lines.append('备用检索 : %s' % links['bing_site_search'])
    lines.append('-' * width)
    lines.append('离线预检（种子库 %s，%s 更新）' % (card['seed'].get('version'), card['seed'].get('updated')))
    lines.append('  %s [%s] %s' % (icon, SEVERITY_LABEL.get(pre.get('severity'), '未知'), pre.get('message')))
    sug = card.get('suggested_verdict') or {}
    if sug:
        lines.append('  · 预检建议结论：%s（%s），仅作填写示例，须人工确认' % (sug.get('label'), sug.get('value')))
    if pre.get('article_count') and pre.get('article_number'):
        lines.append('  · 条文范围：1–%d，本次第 %d 条' % (pre['article_count'], pre['article_number']))
    if pre.get('latest_amendment'):
        lines.append('  · 最新修正：%s' % pre['latest_amendment'])
    if pre.get('status') == 'repealed':
        lines.append('  · 废止日期：%s；替代法：%s' % (pre.get('repealed_date'), pre.get('replaced_by')))
    lines.append('  · 注意：预检不是法律结论，须以官方页面为准。')
    lines.append('-' * width)
    lines.append('人工核对清单（逐项打勾）')
    for item in card['checklist']:
        lines.append('  [ ] %d. %s' % (item['id'], item['item']))
    lines.append('-' * width)
    lines.append('写入核验结论')
    lines.append('  ' + card['record_command'])
    lines.append('  可选结论：' + ' / '.join('%s=%s' % (k, v) for k, v in VERDICTS.items()))
    lines.append('=' * width)
    return '\n'.join(lines)


# ---------------------------------------------------------------- 记录与统计

def resolve_home(explicit=None):
    path = explicit or os.environ.get('LEGALGUARDIAN_HOME') or DEFAULT_HOME
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    return path


def record_path(home):
    return os.path.join(home, 'verifications.jsonl')


def append_record(home, card, verdict, verifier, note, evidence):
    now = datetime.now().astimezone()
    pre = card['offline_precheck']
    record = {
        'schema_version': SCHEMA_VERSION,
        'id': 'v-%s-%s' % (now.strftime('%Y%m%d-%H%M%S'), uuid.uuid4().hex[:6]),
        'law': card['query']['law'],
        'law_key': card['query']['law_key'],
        'law_full_name': pre.get('law_full_name'),
        'article': card['query']['article'],
        'article_number': pre.get('article_number'),
        'verdict': verdict,
        'verdict_label': VERDICTS[verdict],
        'source': 'flk_manual',
        'source_url': OFFICIAL_SEARCH,
        'search_keyword': card['links']['search_keyword'],
        'checked_at': now.isoformat(timespec='seconds'),
        'verifier': verifier,
        'note': note or '',
        'evidence': evidence or '',
        'seed_version': card['seed'].get('version'),
        'offline_precheck': {
            'kind': pre.get('kind'),
            'f_pattern': pre.get('f_pattern'),
            'severity': pre.get('severity'),
            'message': pre.get('message'),
        },
    }
    path = record_path(home)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record, path


def load_records(home):
    path = record_path(home)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def _age_days(iso_text):
    try:
        dt = datetime.fromisoformat(iso_text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return (datetime.now().astimezone() - dt).days


def pending_records(records, stale_days):
    pending = []
    for rec in records:
        reasons = []
        if rec.get('verdict') in ('unverified', 'not_found'):
            reasons.append('结论为“%s”' % VERDICTS.get(rec.get('verdict'), rec.get('verdict')))
        age = _age_days(rec.get('checked_at', ''))
        if age is not None and age > stale_days:
            reasons.append('已 %d 天未复核' % age)
        if reasons:
            item = dict(rec)
            item['reasons'] = reasons
            pending.append(item)
    pending.sort(key=lambda r: r.get('checked_at', ''), reverse=True)
    return pending


def render_records(records, limit, path):
    if not records:
        return '暂无核验记录。\n存储位置: %s' % path
    rows = list(reversed(records))[:limit]
    lines = ['核验记录（最近 %d 条，共 %d 条）' % (len(rows), len(records))]
    lines.append('%-20s %-22s %-10s %-8s %-10s' % ('时间', '法律', '条文', '结论', '核验人'))
    for rec in rows:
        lines.append('%-20s %-22s %-10s %-8s %-10s' % (
            (rec.get('checked_at') or '')[:19].replace('T', ' '),
            _truncate(rec.get('law') or '', 20),
            _truncate(rec.get('article') or '-', 8),
            rec.get('verdict_label') or rec.get('verdict') or '',
            _truncate(rec.get('verifier') or '', 8),
        ))
    lines.append('存储位置: %s' % path)
    return '\n'.join(lines)


def render_stats(records, stale_days, path):
    if not records:
        return '暂无核验记录。\n存储位置: %s' % path
    by_verdict = Counter(r.get('verdict', 'unknown') for r in records)
    by_law = Counter(r.get('law', '') for r in records)
    pending = pending_records(records, stale_days)
    latest = max((r.get('checked_at', '') for r in records), default='')
    lines = ['核验统计']
    lines.append('总记录: %d' % len(records))
    lines.append('结论分布: ' + '  '.join(
        '%s=%d' % (VERDICTS.get(k, k), by_verdict[k]) for k in VERDICTS if by_verdict.get(k)
    ))
    lines.append('覆盖法律: %d 部' % len(by_law))
    if by_law:
        top = by_law.most_common(5)
        lines.append('高频法律: ' + '  '.join('%s(%d)' % (k, v) for k, v in top))
    lines.append('最近核验: %s' % (latest[:19].replace('T', ' ') if latest else '-'))
    lines.append('待复核: %d 条（unverified/not_found 或超过 %d 天）' % (len(pending), stale_days))
    lines.append('存储位置: %s' % path)
    return '\n'.join(lines)


def render_pending(pending, stale_days, path):
    if not pending:
        return '待复核队列为空（阈值 %d 天）。\n存储位置: %s' % (stale_days, path)
    lines = ['待复核队列（%d 条，阈值 %d 天）' % (len(pending), stale_days)]
    for rec in pending:
        lines.append('- %s  %s %s  %s  ← %s' % (
            rec.get('id', ''),
            rec.get('law', ''),
            rec.get('article') or '',
            rec.get('verdict_label') or rec.get('verdict') or '',
            '；'.join(rec.get('reasons', [])),
        ))
    lines.append('存储位置: %s' % path)
    return '\n'.join(lines)


def _truncate(text, width):
    text = str(text)
    return text if len(text) <= width else text[:width - 1] + '…'


# ---------------------------------------------------------------- 主程序

def main(argv=None):
    parser = argparse.ArgumentParser(
        description='法条时效性人工核验助手（离线链接 + 清单 + 留痕）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python scripts/statute_verifier.py --law "民法典" --article "第1165条"\n'
               '  python scripts/statute_verifier.py --law "民法通则" --article "第90条"\n'
               '  python scripts/statute_verifier.py --law "民法典" --article "第1165条" '
               '--record --verdict active --verifier "张三"\n'
               '  python scripts/statute_verifier.py --list\n'
               '  python scripts/statute_verifier.py --stats\n'
               '  python scripts/statute_verifier.py --pending --stale-days 180',
    )
    parser.add_argument('--law', help='法律名称，如“民法典”')
    parser.add_argument('--article', help='条文号，如“第1165条”')
    parser.add_argument('--query', help='合并写法，如“民法典 第1165条”')
    parser.add_argument('--record', action='store_true', help='写入人工核验结论')
    parser.add_argument('--verdict', choices=list(VERDICTS), help='人工核验结论')
    parser.add_argument('--verifier', default='', help='核验人（默认取系统用户名）')
    parser.add_argument('--note', default='', help='备注：核对页面要点、时间等')
    parser.add_argument('--evidence', default='', help='证据文件路径（截图/PDF，可选）')
    parser.add_argument('--list', action='store_true', dest='list_records', help='列出核验记录')
    parser.add_argument('--stats', action='store_true', help='统计核验记录')
    parser.add_argument('--pending', action='store_true', help='列出待复核记录')
    parser.add_argument('--stale-days', type=int, default=180, help='超过多少天视为待复核（默认 180）')
    parser.add_argument('--limit', type=int, default=20, help='列表条数（默认 20）')
    parser.add_argument('--json', action='store_true', dest='as_json', help='输出 JSON')
    parser.add_argument('--open', action='store_true', help='用默认浏览器打开备用检索链接')
    parser.add_argument('--home', help='记录目录（默认 ~/.legalguardian 或 LEGALGUARDIAN_HOME）')
    parser.add_argument('--seed', help='种子库路径（默认 reference/statutes_seed.json）')
    args = parser.parse_args(argv)

    law = args.law
    article = args.article
    if args.query:
        q_law, q_article = split_query(args.query)
        if not law:
            law = q_law
        if not article:
            article = q_article

    home = resolve_home(args.home)
    path = record_path(home)

    # 记录类操作
    if args.list_records or args.stats or args.pending:
        records = load_records(home)
        if args.list_records:
            if args.as_json:
                print(json.dumps({'total': len(records), 'path': path,
                                  'records': list(reversed(records))[:args.limit]},
                                 ensure_ascii=False, indent=2))
            else:
                print(render_records(records, args.limit, path))
        elif args.stats:
            pending = pending_records(records, args.stale_days)
            if args.as_json:
                by_verdict = Counter(r.get('verdict', 'unknown') for r in records)
                by_law = Counter(r.get('law', '') for r in records)
                print(json.dumps({
                    'total': len(records),
                    'by_verdict': dict(by_verdict),
                    'by_law': dict(by_law),
                    'pending': len(pending),
                    'stale_days': args.stale_days,
                    'path': path,
                }, ensure_ascii=False, indent=2))
            else:
                print(render_stats(records, args.stale_days, path))
        else:
            pending = pending_records(records, args.stale_days)
            if args.as_json:
                print(json.dumps({'total': len(pending), 'stale_days': args.stale_days,
                                  'path': path, 'records': pending}, ensure_ascii=False, indent=2))
            else:
                print(render_pending(pending, args.stale_days, path))
        return 0

    if not law:
        parser.print_help(sys.stderr)
        return 1

    if args.record and not args.verdict:
        msg = '错误：--record 必须同时提供 --verdict（可选值：%s）' % ' / '.join(VERDICTS)
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    try:
        seed, index = load_seed(args.seed)
    except Exception as exc:
        msg = '错误：无法加载种子库 %s（%s）' % (args.seed or SEED_PATH, exc)
        if args.as_json:
            print(json.dumps({'error': msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    verifier = args.verifier or os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown'
    card, _pre = build_card(law, article, seed, index, verifier)

    if args.open:
        ok = webbrowser.open(card['links']['bing_site_search'])
        card['opened'] = bool(ok)

    if args.record:
        record, rec_path = append_record(home, card, args.verdict, verifier, args.note, args.evidence)
        warning = ''
        if card['offline_precheck'].get('kind') == 'repealed' and args.verdict == 'active':
            warning = ('离线预检显示该法已废止，但记录结论为“有效”。'
                       '请确认种子库是否过期，或人工核对是否准确。')
        if args.as_json:
            print(json.dumps({'record': record, 'path': rec_path, 'warning': warning},
                             ensure_ascii=False, indent=2))
        else:
            print('已记录核验：%s' % record['id'])
            print('结论：%s（%s）' % (record['verdict_label'], record['verdict']))
            print('法律：%s %s' % (record['law'], record['article'] or ''))
            print('核验人：%s    时间：%s' % (record['verifier'], record['checked_at']))
            print('存储：%s' % rec_path)
            if warning:
                print('⚠️  ' + warning)
        return 0

    if args.as_json:
        print(json.dumps(card, ensure_ascii=False, indent=2))
    else:
        print(render_card(card))
    return 0


if __name__ == '__main__':
    sys.exit(main())
