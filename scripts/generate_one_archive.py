#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
archive_file = os.path.join(data_dir, 'one_articles.json')
output_file = os.path.join(script_dir, '..', 'one_archive.html')

def history_file_exists(date: str) -> bool:
    y, m, d = date.split('-')
    hist_file = os.path.join(data_dir, 'history', y, m, f"{d}.json")
    return os.path.exists(hist_file)

def generate_archive_page():
    if not os.path.exists(archive_file):
        print("没有找到 ONE 文章存档，跳过生成")
        return
    with open(archive_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    if not articles:
        print("存档为空")
        return

    # 过滤：只保留有历史 JSON 文件的日期
    valid_articles = [item for item in articles if history_file_exists(item['date'])]
    if not valid_articles:
        print("没有可用的历史数据，放弃生成")
        return

    # 按年月分组
    grouped = {}
    for item in valid_articles:
        date = item['date']
        year = date[:4]
        month = date[5:7]
        if year not in grouped:
            grouped[year] = {}
        if month not in grouped[year]:
            grouped[year][month] = []
        grouped[year][month].append(item)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <title>隅 · 精选文摘</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1e1e2f;
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 2rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #8e8e9e;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}
        .year-group {{
            margin-bottom: 2rem;
        }}
        .year-title {{
            font-size: 1.6rem;
            font-weight: 500;
            color: #1e1e2f;
            border-bottom: 1px solid #f0f2f5;
            padding-bottom: 0.3rem;
            margin-bottom: 1rem;
        }}
        .month-group {{
            margin-left: 1rem;
            margin-bottom: 1.2rem;
        }}
        .month-title {{
            font-size: 1.2rem;
            font-weight: 500;
            color: #5b5b6e;
            margin-bottom: 0.5rem;
        }}
        .article-list {{
            list-style: none;
            margin-left: 1rem;
        }}
        .article-item {{
            margin-bottom: 0.6rem;
        }}
        .article-link {{
            color: #1e1e2f;
            text-decoration: none;
            border-bottom: 1px dotted #e0e4e8;
            transition: border-color 0.2s;
            font-size: 0.95rem;
        }}
        .article-link:hover {{
            border-bottom-color: #1e1e2f;
        }}
        .article-date {{
            color: #8e8e9e;
            font-size: 0.8rem;
            margin-right: 0.8rem;
        }}
        .footer {{
            margin-top: 3rem;
            text-align: center;
            font-size: 0.75rem;
            color: #b0b0c0;
            border-top: 1px solid #f0f2f5;
            padding-top: 1.5rem;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 1.5rem;
            color: #1e1e2f;
            text-decoration: none;
            border-bottom: 1px dotted #e0e4e8;
        }}
        @media (max-width: 480px) {{
            h1 {{ font-size: 1.6rem; }}
            .year-title {{ font-size: 1.4rem; }}
            .month-title {{ font-size: 1rem; }}
            .article-link {{ font-size: 0.85rem; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">← 返回主页</a>
    <h1>📖 精选文摘</h1>
    <div class="subtitle">ONE · 一个 文章存档</div>
'''
    for year in sorted(grouped.keys(), reverse=True):
        html += f'    <div class="year-group">\n        <div class="year-title">{year} 年</div>\n'
        for month in sorted(grouped[year].keys(), reverse=True):
            html += f'        <div class="month-group">\n            <div class="month-title">{month} 月</div>\n            <ul class="article-list">\n'
            for item in sorted(grouped[year][month], key=lambda x: x['date'], reverse=True):
                date_str = item['date']
                title = item['title']
                html += f'                <li class="article-item"><a href="/detail.html?date={date_str}#one" class="article-link"><span class="article-date">{date_str}</span> {title}</a></li>\n'
            html += '            </ul>\n        </div>\n'
        html += '    </div>\n'
    html += f'''
    <div class="footer">
        <a href="/" style="color:#1e1e2f; text-decoration:none; border-bottom:1px dotted #e0e4e8;">🏠 隅</a>
        <span style="margin:0 0.5rem">·</span>
        <a href="/history.html" style="color:#1e1e2f; text-decoration:none; border-bottom:1px dotted #e0e4e8;">📜 历史回顾</a>
    </div>
</div>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"已生成精选文摘页面，共 {len(valid_articles)} 条有效文章")

if __name__ == "__main__":
    generate_archive_page()
