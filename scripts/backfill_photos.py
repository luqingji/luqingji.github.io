#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""扫描历史数据，将每日 ONE·摄影信息补录到 photos.json"""

import os
import json
import re
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
history_dir = os.path.join(data_dir, 'history')
photo_file = os.path.join(data_dir, 'photos.json')

def extract_photo_from_history(history_file):
    """从历史 JSON 文件中提取 photo 信息"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        one_photo = data.get('one', {}).get('photo')
        if one_photo and one_photo.get('image'):
            return {
                "date": data.get('date'),
                "title": one_photo.get('title', ''),
                "author": one_photo.get('author', ''),
                "description": one_photo.get('description', ''),
                "image": one_photo.get('image'),
                "src": one_photo.get('image')
            }
    except Exception as e:
        print(f"读取文件失败 {history_file}: {e}")
    return None

def main():
    if not os.path.exists(history_dir):
        print("历史目录不存在，退出")
        return

    # 读取现有 photos.json
    if os.path.exists(photo_file):
        with open(photo_file, 'r', encoding='utf-8') as f:
            existing_photos = json.load(f)
    else:
        existing_photos = []

    existing_dates = {p['date'] for p in existing_photos if 'date' in p}

    # 遍历所有历史 JSON
    new_photos = []
    for root, dirs, files in os.walk(history_dir):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                filepath = os.path.join(root, file)
                photo = extract_photo_from_history(filepath)
                if photo and photo['date'] not in existing_dates:
                    new_photos.append(photo)

    if not new_photos:
        print("没有新照片需要添加")
        return

    # 合并并排序
    all_photos = existing_photos + new_photos
    all_photos.sort(key=lambda x: x['date'], reverse=True)

    # 写入文件
    with open(photo_file, 'w', encoding='utf-8') as f:
        json.dump(all_photos, f, ensure_ascii=False, indent=2)

    print(f"已添加 {len(new_photos)} 张历史照片，总计 {len(all_photos)} 张")

if __name__ == "__main__":
    main()
