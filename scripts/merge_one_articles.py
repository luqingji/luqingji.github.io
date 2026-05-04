import json
import os
from datetime import datetime

# 路径配置
NEW_DATA_FILE = "one_articles_2026_04.json"   # 你刚爬取的原始数据文件（含完整API返回）
TARGET_FILE = "../data/one_articles.json"     # 网站使用的存档文件

def extract_title_from_api_data(api_data):
    """从API返回的data中提取文章标题"""
    # API返回结构：{"data": {"title": "xxx", ...}}
    return api_data.get("data", {}).get("title", "")

def merge():
    # 读取新爬取的原始数据
    with open(NEW_DATA_FILE, "r", encoding="utf-8") as f:
        new_items = json.load(f)   # 格式: [{"date": "2026/04/01", "data": {...}}, ...]
    
    # 转换为标准存档格式
    new_records = []
    for item in new_items:
        date_str = item["date"].replace("/", "-")  # 将 2026/04/01 转为 2026-04-01
        title = extract_title_from_api_data(item)
        if title:
            new_records.append({"date": date_str, "title": title})
    
    # 读取现有存档
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # 使用日期作为去重键
        existing_dates = {entry["date"] for entry in existing}
    else:
        existing = []
        existing_dates = set()
    
    # 合并新记录（去重）
    for rec in new_records:
        if rec["date"] not in existing_dates:
            existing.append(rec)
            existing_dates.add(rec["date"])
    
    # 按日期倒序排序
    existing.sort(key=lambda x: x["date"], reverse=True)
    
    # 写回文件
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"已合并 {len(new_records)} 条新记录，总计 {len(existing)} 条")
    
    # 重新生成精选文摘页面
    os.system("python generate_one_archive.py")

if __name__ == "__main__":
    merge()
