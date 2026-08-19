#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LegalGuardian 精简包构建器 (v4.3.0)
====================================
构建 legal-guardian.skill 安装包：仅含运行时必需文件
（SKILL.md / manifest.yaml / README.md / scripts / reference /
 benchmark / templates / tests / panel），不含 test_data 与 产品技术文档。

用法:
    python tests/rebuild_package.py            # 重建 legal-guardian.skill
    python tests/rebuild_package.py --dry-run  # 只打印将打包的文件清单

说明:
    - 中文文件名以 UTF-8 写入 zip 中心目录（修复 v4.2.1 乱码缺陷#12）
    - 打包后运行 python tests/run_smoke.py 验证（E4 检查包内容）
"""
import argparse
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'legal-guardian.skill')

# 打包的顶层条目
TOP_LEVEL = ['SKILL.md', 'manifest.yaml', 'README.md', 'scripts', 'reference',
             'benchmark', 'templates', 'tests', 'panel']

# 排除项（按相对路径子串）
EXCLUDE = [
    '__pycache__',                # Python 缓存
    '.git',                       # VCS 元数据
    'tests/smoke_report.md',      # 运行时生成物
    'panel/_shot.png',            # 本地验证截图
]


def collect_files():
    files = []
    for top in TOP_LEVEL:
        path = os.path.join(ROOT, top)
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.git')]
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    rel = os.path.relpath(full, ROOT).replace(os.sep, '/')
                    if any(seg in rel for seg in EXCLUDE):
                        continue
                    files.append(full)
    return files


def build(dry_run=False):
    files = collect_files()
    if dry_run:
        for f in files:
            print(os.path.relpath(f, ROOT).replace(os.sep, '/'))
        print(f'\n共 {len(files)} 个文件')
        return

    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            arcname = os.path.relpath(f, ROOT).replace(os.sep, '/')
            z.write(f, arcname)
    size_mb = os.path.getsize(OUT) / 1024 / 1024
    print(f'已重建 {OUT}  ({len(files)} 个文件, {size_mb:.2f} MB)')
    with zipfile.ZipFile(OUT) as z:
        tops = {n.split('/')[0] for n in z.namelist()}
        assert 'test_data' not in tops and '产品技术文档' not in tops
        print('精简包校验通过：不含 test_data / 产品技术文档')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='LegalGuardian 精简包构建器')
    ap.add_argument('--dry-run', action='store_true', help='只打印文件清单')
    args = ap.parse_args()
    build(dry_run=args.dry_run)
    sys.exit(0)
