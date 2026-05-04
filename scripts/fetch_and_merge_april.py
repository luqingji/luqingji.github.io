#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
ONE_ARCHIVE_FILE = os.path.join(DATA_DIR, 'one_articles.json')
GENERATE_SCRIPT = os.path.join(SCRIPT_DIR, 'generate_one_archive.py')

def fetch_one_article(date_str):
    """获取指定日期的 ONE 文章标题（仅标题）"""
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
        print(f"❌ {date_str} 请求失败: {e}")
    return None

def fetch_month(year, month):
    """遍历某个月每一天，返回 {date_str: title} 字典"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    results = {}
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")      # 2026-04-01
        api_date = current.strftime("%Y/%m/%d")      # 2026/04/01
        print(f"正在获取 {api_date} ...")
        title = fetch_one_article(api_date)
        if title:
            results[date_str] = title
        else:
            print(f"⚠️  {api_date} 无文章或获取失败")
        time.sleep(0.5)   # 礼貌间隔
        current += timedelta(days=1)
    return results

def merge_to_local(new_records):
    """合并到 data/one_articles.json 并去重"""
    existing = []
    if os.path.exists(ONE_ARCHIVE_FILE):
        with open(ONE_ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing_dates = {item['date'] for item in existing}
    
    # 添加新记录
    for date, title in new_records.items():
        if date not in existing_dates:
            existing.append({"date": date, "title": title})
            existing_dates.add(date)
            print(f"➕ 添加 {date}: {title}")
    
    # 按日期倒序排序
    existing.sort(key=lambda x: x['date'], reverse=True)
    
    with open(ONE_ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"✅ 合并完成，现有总记录数: {len(existing)}")

def regenerate_archive():
    """重新生成精选文摘页面"""
    if not os.path.exists(GENERATE_SCRIPT):
        print("⚠️  generate_one_archive.py 不存在，请手动运行")
        return
    import subprocess
    subprocess.run([sys.executable, GENERATE_SCRIPT], check=True)
    print("✅ one_archive.html 已更新")

def main():
    print("开始获取 2026年4月 ONE 文章...")
    april_data = fetch_month(2026, 4)
    if not april_data:
        print("❌ 没有获取到任何文章，请检查网络或 token")
        sys.exit(1)
    merge_to_local(april_data)
    regenerate_archive()
    print("🎉 全部完成！")

if __name__ == "__main__":
    main()