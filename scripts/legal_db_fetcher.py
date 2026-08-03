#!/usr/bin/env python3
"""
法律数据库检索器 (Legal DB Fetcher)

从国家法律法规数据库(flk.npc.gov.cn)检索指定法律条文或法律文件。
支持精确搜索、模糊搜索、法条查询和有效性筛选。

用法:
    python legal_db_fetcher.py --search "民法典" [--exact] [--status 3]
    python legal_db_fetcher.py --fetch <法律ID> [--format docx]
    python legal_db_fetcher.py --article <法律ID> "第X条"

注意:
    本脚本优先使用本地 reference/legal_knowledge_base.json 中的缓存数据。
    如需在线检索，建议使用 cn-law-hub 工具 (https://github.com/ZongziForu/cn-law-hub)。
    在线检索需安装Playwright: pip install playwright --break-system-packages && playwright install
"""

import sys
import json
import os
import re

# UTF-8 输出兼容 (Windows GBK 控制台)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def load_local_kb() -> dict:
    """加载本地法律知识库"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(script_dir, '..', 'reference', 'legal_knowledge_base.json')
    if os.path.exists(kb_path):
        with open(kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def search_local(text: str, kb: dict) -> list:
    """在本地知识库中搜索"""
    results = []

    # 搜索民法典相关
    civil_law = kb.get('civil_law', {})
    civil_code = civil_law.get('民法典', {})
    key_articles = civil_code.get('key_articles', {})

    for section_name, articles in key_articles.items():
        for article_id, article_data in articles.items():
            article_title = article_data.get('title', '')
            article_content = article_data.get('content', '')
            search_text = f'{article_title} {article_content}'

            if text in search_text or text in article_id or text in article_title:
                results.append({
                    'source': 'local_knowledge_base',
                    'section': section_name,
                    'article_id': article_id,
                    'title': article_title,
                    'content': article_content,
                    'test_case_relevance': article_data.get('test_case_relevance', ''),
                    'related_law': article_data.get('related_law', '')
                })

    # 搜索刑法相关
    criminal_law = kb.get('criminal_law', {})
    criminal_code = criminal_law.get('刑法', {})
    criminal_articles = criminal_code.get('key_articles', {})

    for article_id, article_data in criminal_articles.items():
        article_title = article_data.get('title', '')
        search_text = f'{article_title} {article_data.get("sentencing", "")}'

        if text in search_text or text in article_id or text in article_title:
            results.append({
                'source': 'local_knowledge_base',
                'section': '刑法',
                'article_id': article_id,
                'title': article_title,
                'content': article_data.get('sentencing', ''),
                'distinction': article_data.get('distinction_from_232', ''),
                'test_case_relevance': article_data.get('test_case_relevance', '')
            })

    # 搜索废止法律信息
    repealed = civil_code.get('repealed_laws_warning', {})
    for law_name, info in repealed.items():
        if text in law_name:
            results.append({
                'source': 'local_knowledge_base',
                'type': 'repealed_law_warning',
                'law_name': law_name,
                'status': info,
                'note': '此法律已废止，请勿在分析中引用'
            })

    # 搜索常见陷阱
    common_traps = kb.get('common_traps', {})
    for trap_type, traps in common_traps.items():
        if isinstance(traps, dict):
            for trap_name, trap_info in traps.items():
                if text in trap_name:
                    results.append({
                        'source': 'local_knowledge_base',
                        'type': f'trap_{trap_type}',
                        'name': trap_name,
                        'info': trap_info
                    })

    return results


def search_online(query: str, exact: bool = False, status: int = 3) -> dict:
    """
    在线检索国家法律法规数据库（需要cn-law-hub工具支持）

    如需使用在线检索功能，请:
    1. 克隆cn-law-hub: git clone https://github.com/ZongziForu/cn-law-hub.git
    2. 安装依赖: pip install playwright --break-system-packages && playwright install
    3. 将cn-law-hub路径添加到CN_LAW_HUB_PATH环境变量
    """
    cn_law_hub_path = os.environ.get('CN_LAW_HUB_PATH', '')
    if not cn_law_hub_path:
        return {
            'success': False,
            'error': '未找到cn-law-hub。请设置CN_LAW_HUB_PATH环境变量指向cn-law-hub目录',
            'help': 'git clone https://github.com/ZongziForu/cn-law-hub.git && export CN_LAW_HUB_PATH=/path/to/cn-law-hub'
        }

    import subprocess
    download_script = os.path.join(cn_law_hub_path, 'scripts', 'download.py')

    cmd = ['python3', download_script, '--search', query]
    if exact:
        cmd.append('--exact')
    if status:
        cmd.extend(['--status', str(status)])
    cmd.extend(['--size', '10'])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            'success': True,
            'query': query,
            'output': result.stdout[:5000],
            'stderr': result.stderr[:1000] if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': '检索超时（60秒）'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': '用法: python legal_db_fetcher.py --search "关键词" [--exact] [--status 3] [--online] | --article "法条号" | --fetch "法律ID"',
            'examples': [
                'python legal_db_fetcher.py --search "民法典"',
                'python legal_db_fetcher.py --search "民法通则" --exact',
                'python legal_db_fetcher.py --article "第一千一百六十五条"',
                'python legal_db_fetcher.py --online --search "民法典" --status 3'
            ]
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    args = sys.argv[1:]
    query = None
    use_online = False
    exact = False
    status = 3
    article_query = None
    fetch_id = None

    i = 0
    while i < len(args):
        if args[i] == '--search' and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        elif args[i] == '--exact':
            exact = True
            i += 1
        elif args[i] == '--status' and i + 1 < len(args):
            status = int(args[i + 1])
            i += 2
        elif args[i] == '--online':
            use_online = True
            i += 1
        elif args[i] == '--article' and i + 1 < len(args):
            article_query = args[i + 1]
            i += 2
        elif args[i] == '--fetch' and i + 1 < len(args):
            fetch_id = args[i + 1]
            i += 2
        else:
            i += 1

    results = {
        'query': query or article_query or fetch_id,
        'search_type': 'online' if use_online else 'local',
        'results': []
    }

    if use_online:
        if query:
            online_result = search_online(query, exact, status)
            results['online_search'] = online_result
        else:
            results['error'] = '在线检索需要--search参数'
    else:
        kb = load_local_kb()
        if query:
            local_results = search_local(query, kb)
        elif article_query:
            local_results = search_local(article_query, kb)
        else:
            local_results = []

        results['results'] = local_results
        results['total_results'] = len(local_results)

        if not local_results:
            results['suggestion'] = '本地知识库未找到匹配结果。建议：1) 使用 --online 在线检索；2) 更新本地知识库；3) 访问 https://flk.npc.gov.cn 手动检索'

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
