#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
补全 2026 年 4 月 ONE·一个文章标题到 one_articles.json
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta
import time

# 配置
TOKEN = "gwr5bfmq0fvtwbdjcngnzurxaemqp9"
API_URL = "https://v3.alapi.cn/api/one"
HEADERS = {"Content-Type": "application/json"}

def fetch_article_title(date_str):
    """获取指定日期的 ONE 文章标题，失败返回 None"""
    params = {"date": date_str, "token": TOKEN}
    try:
        resp = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('data'):
                title = data['data'].get('title', '')
                if title:
                    return title
    except Exception as e:
        print(f"  请求失败: {e}")
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    archive_file = os.path.join(data_dir, 'one_articles.json')

    # 读取现有 one_articles.json
    existing_dict = {}  # {date: title}
    if os.path.exists(archive_file):
        with open(archive_file, 'r', encoding='utf-8') as f:
            try:
                existing_list = json.load(f)
                for item in existing_list:
                    existing_dict[item['date']] = item['title']
            except:
                existing_dict = {}

    # 准备存储新记录
    new_records = []
    start = datetime(2026, 4, 1)
    end = datetime(2026, 4, 30)
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        api_date = current.strftime("%Y/%m/%d")
        if date_str not in existing_dict:
            print(f"正在获取 {api_date} ...")
            title = fetch_article_title(api_date)
            if title:
                new_records.append({"date": date_str, "title": title})
                print(f"  ✅ 添加: {title}")
            else:
                print(f"  ❌ 无文章或获取失败")
        else:
            print(f"⏭️ 跳过已存在: {date_str}")
        time.sleep(0.5)
        current += timedelta(days=1)

    if not new_records:
        print("没有新文章需要添加")
        return

    # 合并现有和新记录
    all_records = []
    for date, title in existing_dict.items():
        all_records.append({"date": date, "title": title})
    all_records.extend(new_records)
    # 按日期去重（保留最新）
    unique = {}
    for item in all_records:
        unique[item['date']] = item
    final_list = list(unique.values())
    final_list.sort(key=lambda x: x['date'], reverse=True)

    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    print(f"✅ 已更新 one_articles.json，新增 {len(new_records)} 条，总计 {len(final_list)} 条")

    # 可选：重新生成精选文摘页面
    generate_script = os.path.join(script_dir, 'generate_one_archive.py')
    if os.path.exists(generate_script):
        print("正在重新生成 one_archive.html ...")
        import subprocess
        subprocess.run([sys.executable, generate_script], check=True)
        print("✅ one_archive.html 已更新")
    else:
        print("⚠️ 未找到 generate_one_archive.py，请手动运行该脚本生成页面")

if __name__ == "__main__":
    main()