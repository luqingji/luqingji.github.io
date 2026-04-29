#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""扫描历史数据，将每日 ONE 文章标题补录到 one_articles.json，并重新生成精选文摘页面"""

import os
import json
import sys
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
history_dir = os.path.join(data_dir, 'history')
archive_file = os.path.join(data_dir, 'one_articles.json')
generate_script = os.path.join(script_dir, 'generate_one_archive.py')

def extract_article_from_history(history_file):
    """从历史 JSON 文件中提取文章标题"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        one_article = data.get('one', {}).get('article')
        if one_article and one_article.get('title'):
            return {
                "date": data.get('date'),
                "title": one_article.get('title')
            }
    except Exception as e:
        print(f"读取文件失败 {history_file}: {e}")
    return None

def main():
    if not os.path.exists(history_dir):
        print("历史目录不存在，退出")
        sys.exit(1)

    # 读取现有 one_articles.json（如果存在）
    existing_articles = {}
    if os.path.exists(archive_file):
        with open(archive_file, 'r', encoding='utf-8') as f:
            existing_articles = {item['date']: item for item in json.load(f)}

    # 遍历所有历史 JSON
    new_articles = []
    for root, dirs, files in os.walk(history_dir):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                filepath = os.path.join(root, file)
                article = extract_article_from_history(filepath)
                if article and article['date'] not in existing_articles:
                    new_articles.append(article)

    if not new_articles:
        print("没有新文章需要添加")
    else:
        # 合并并排序
        all_articles = list(existing_articles.values()) + new_articles
        all_articles.sort(key=lambda x: x['date'], reverse=True)
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"已添加 {len(new_articles)} 篇历史文章，总计 {len(all_articles)} 篇")

    # 重新生成精选文摘页面
    if os.path.exists(generate_script):
        print("正在重新生成 one_archive.html...")
        import subprocess
        result = subprocess.run([sys.executable, generate_script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"生成页面失败: {result.stderr}")
            sys.exit(1)
        print("one_archive.html 已更新")
    else:
        print("警告: generate_one_archive.py 不存在，请手动运行该脚本生成页面")

if __name__ == "__main__":
    main()