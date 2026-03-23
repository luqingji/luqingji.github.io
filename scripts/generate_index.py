#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""生成历史索引文件 data/history/index.json"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
history_dir = os.path.join(data_dir, 'history')

def generate_index():
    if not os.path.exists(history_dir):
        logger.warning("history目录不存在，跳过索引生成")
        return

    dates = []
    for root, dirs, files in os.walk(history_dir):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                # 获取相对路径: history/2026/03/22.json
                rel_path = os.path.relpath(os.path.join(root, file), history_dir)
                parts = rel_path.split(os.sep)
                if len(parts) == 3:
                    year, month, day_file = parts
                    day = day_file.replace('.json', '')
                    date = f"{year}-{month}-{day}"
                    dates.append(date)
    dates = sorted(set(dates), reverse=True)
    index_path = os.path.join(history_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(dates, f, ensure_ascii=False, indent=2)
    logger.info(f"生成索引，共 {len(dates)} 天")

if __name__ == "__main__":
    generate_index()