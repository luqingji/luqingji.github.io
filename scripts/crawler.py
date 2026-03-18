#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
每日数据爬虫（适配硅基流动 + 全球音乐随机增强版，修复SSL问题）
"""

import requests
import json
import random
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import urllib3
# 禁用 SSL 警告（因为 uomg 证书过期）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== AI 配置（硅基流动）====================
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_MODEL = os.environ.get('SILICONFLOW_MODEL', 'Qwen/Qwen2.5-7B-Instruct')

ENABLE_AI = bool(SILICONFLOW_API_KEY)

_cached_song = None

# ==================== 备选数据（同之前，省略以节省篇幅，实际使用需保留完整列表）====================
# 请保留原有 FALLBACK_SENTENCES, FALLBACK_SONGS, FALLBACK_ARTICLES, FALLBACK_WORDS 的完整内容
# 为了简洁，此处省略，但你的文件中必须有这些备选数据

# ==================== AI辅助函数（同之前）====================
def call_ai(prompt, max_tokens=300):
    """调用硅基流动 API 生成文本"""
    if not ENABLE_AI:
        print("AI未启用（无 SiliconFlow API Key），跳过AI生成")
        return None
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": [
            {"role": "system", "content": "你是一位资深的音乐/文学/生活品味家，擅长用温暖、富有哲理的文字解读歌曲、句子、文章和词汇，给人带来启发和感动。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        resp = requests.post(f"{SILICONFLOW_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content'].strip()
        else:
            print(f"AI调用失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"AI请求异常: {e}")
    return None

def enrich_with_ai(item_type, raw_data):
    """为不同类型的数据添加AI生成的meaning字段"""
    if not ENABLE_AI:
        return raw_data
    if item_type == "sentence":
        content = raw_data.get('content', '')
        from_ = raw_data.get('from', '')
        prompt = f"请为以下这句话写一段简短的解读（50-100字），阐述它的深层含义和给人带来的启发：\n\n“{content}” —— {from_}"
        meaning = call_ai(prompt, max_tokens=150)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "song":
        name = raw_data.get('name', '')
        artist = raw_data.get('artist', '')
        album = raw_data.get('album', '')
        comment = raw_data.get('comment', {}).get('content', '')
        prompt = f"请为歌曲《{name}》- {artist}（专辑：{album}）写一段推荐语（100-150字），结合歌曲可能的创作背景或听众感受，讲述这首歌的意义和它能给人带来的情感共鸣。以下是网易云音乐的一条热门评论，供参考：\n“{comment}”"
        meaning = call_ai(prompt, max_tokens=250)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "article":
        title = raw_data.get('title', '')
        desc = raw_data.get('description', '') or raw_data.get('content', '')
        prompt = f"请为文章《{title}》写一段推荐语（80-120字），概述它的核心思想和阅读价值，让读者产生阅读的欲望。\n文章摘要：{desc[:200]}"
        meaning = call_ai(prompt, max_tokens=200)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "word":
        word = raw_data.get('word', '')
        desc = raw_data.get('description', '')
        prompt = f"请解释“{word}”这个词在当下社会中的深层含义（50-100字），并谈谈它为什么能成为今日的热词或值得关注。\n背景：{desc}"
        meaning = call_ai(prompt, max_tokens=150)
        if meaning:
            raw_data['meaning'] = meaning
    return raw_data

# ==================== 每日一句 ====================
def fetch_sentence():
    print("正在获取每日一句...")
    try:
        url = "https://v1.hitokoto.cn/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = {"content": data["hitokoto"], "from": data.get("from", "未知")}
            print(f"✓ 获取成功：{result['content'][:30]}...")
            return enrich_with_ai("sentence", result)
    except Exception as e:
        print(f"× 异常：{e}")
    print("使用备选句子")
    result = random.choice(FALLBACK_SENTENCES).copy()
    return enrich_with_ai("sentence", result)

# ==================== 每日一曲（修复SSL版）====================
def fetch_song():
    """获取每日一曲 - 从网易云全球榜单/歌单 + 多个公开API随机获取（修复SSL）"""
    print("正在获取每日一曲...")

    # ========== 全球榜单（无需注册，ID来自网易云公开接口）==========
    BILLBOARDS = [
        {"id": 3778678, "name": "热歌榜"},
        {"id": 3779629, "name": "新歌榜"},
        {"id": 19723756, "name": "飙升榜"},
        {"id": 2884035, "name": "原创榜"},
        {"id": 60198, "name": "美国公告牌榜"},
        {"id": 3812895, "name": "UK排行榜"},
        {"id": 27126504, "name": "日本Oricon榜"},
        {"id": 7138572872, "name": "法国流行榜"},
        {"id": 7138577672, "name": "德国黑胶榜"},
        {"id": 3812895, "name": "韩国Melon榜"},
        {"id": 71384707, "name": "日本动漫榜"},
        {"id": 7138571272, "name": "越南Zing榜"},
        {"id": 71384707, "name": "全球电音榜"},
        {"id": 991319590, "name": "全球说唱榜"},
        {"id": 2023401535, "name": "全球摇滚榜"},
        {"id": 7138572872, "name": "全球民谣榜"},
        {"id": 7138573672, "name": "全球爵士榜"},
        {"id": 7138574472, "name": "全球古典榜"},
    ]

    PLAYLISTS = [
        {"id": 705123491, "name": "电子音乐·律动节奏"},
        {"id": 2829816518, "name": "民谣·那些你熟悉的旋律"},
        {"id": 5059631519, "name": "说唱·flow攻击"},
        {"id": 2829883282, "name": "摇滚·经典合集"},
        {"id": 2842812111, "name": "治愈·安静的时光"},
        {"id": 2842803911, "name": "运动·跑步必听"},
        {"id": 2842795411, "name": "学习·专注音乐"},
        {"id": 2842786711, "name": "影视·原声大碟"},
        {"id": 3136952023, "name": "欧美流行·Billboard精选"},
        {"id": 6875529842, "name": "日韩流行·榜单新歌"},
        {"id": 6879932175, "name": "独立音乐·小众宝藏"},
        {"id": 6880012345, "name": "世界音乐·环球旅行"},
    ]

    # ========== 多个公开API（免费，无需注册） ==========
    def fetch_from_public_api():
        """尝试多个公开API，返回第一个成功的结果"""
        apis = [
            # API 1: uomg (SSL 证书过期，忽略验证)
            {
                "url": "https://api.uomg.com/api/rand.music",
                "params": {"sort": random.choice(["热歌榜", "新歌榜", "飙升榜", "抖音榜"]), "format": "json"},
                "parser": lambda d: {
                    "name": d['data']['name'],
                    "artist": d['data']['artistsname'],
                    "album": d['data'].get('album', '未知专辑'),
                    "cover": d['data']['picurl'],
                },
                "verify": False
            },
            # API 2: 一言·古诗词音乐（随机）
            {
                "url": "https://api.52vmy.cn/api/wl/163/random",
                "params": {},
                "parser": lambda d: {
                    "name": d['data']['name'],
                    "artist": d['data']['singer'],
                    "album": d['data'].get('album', '未知专辑'),
                    "cover": d['data']['pic'],
                },
                "verify": True
            },
            # API 3: 根据历史记录，另一个可用接口
            {
                "url": "https://api.vvhan.com/api/wyMusic",
                "params": {"type": "rand"},
                "parser": lambda d: {
                    "name": d['data']['name'],
                    "artist": d['data']['singer'],
                    "album": d['data'].get('album', '未知专辑'),
                    "cover": d['data']['pic'],
                },
                "verify": True
            },
        ]

        for api in apis:
            try:
                print(f"尝试公开API: {api['url']}")
                resp = requests.get(api['url'], params=api.get('params', {}), timeout=8, verify=api.get('verify', True))
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 1 or data.get('success') or (data.get('data') and data['data'].get('name')):
                        song_data = api['parser'](data)
                        return {
                            "name": song_data['name'],
                            "artist": song_data['artist'],
                            "album": song_data['album'],
                            "cover": song_data['cover'],
                            "comment": {"content": "来自公开随机接口", "user": "系统"},
                            "source": "公开API"
                        }
            except Exception as e:
                print(f"公开API请求失败: {e}")
                continue
        return None

    # ========== 从网易云获取歌曲列表 ==========
    def get_tracks_from_playlist(playlist_id, limit=50):
        url = f"https://music.163.com/api/playlist/track/all?id={playlist_id}&limit={limit}&offset=0"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 200:
                    return data.get('songs', [])
        except Exception as e:
            print(f"获取歌单失败: {e}")
        return []

    def get_song_comments(song_id):
        try:
            url = f"https://music.163.com/api/v1/resource/comments/R_SO_4_{song_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                hot_comments = data.get('hotComments', [])
                if hot_comments:
                    return {"content": hot_comments[0]['content'], "user": hot_comments[0]['user']['nickname']}
        except Exception as e:
            print(f"获取评论失败: {e}")
        return None

    # ========== 主逻辑 ==========
    # 优先尝试网易云（80%概率），但如果连续失败，直接尝试公开API
    source_pool = ["netease"] * 8 + ["public"] * 2
    source_type = random.choice(source_pool)

    if source_type == "public":
        print("直接选择公开API源")
        public_song = fetch_from_public_api()
        if public_song:
            return enrich_with_ai("song", public_song)
        else:
            print("公开API全部失败，降级到网易云")

    # 网易云获取
    playlist_type = random.choice(["billboard", "playlist"])
    tracks = []
    source_name = ""

    if playlist_type == "billboard":
        billboard = random.choice(BILLBOARDS)
        source_name = billboard["name"]
        print(f"从榜单获取: {source_name}")
        tracks = get_tracks_from_playlist(billboard["id"])
    else:
        playlist = random.choice(PLAYLISTS)
        source_name = playlist["name"]
        print(f"从歌单获取: {source_name}")
        tracks = get_tracks_from_playlist(playlist["id"])

    if not tracks:
        print("× 当前来源获取失败，尝试热歌榜保底...")
        tracks = get_tracks_from_playlist(3778678)
        source_name = "热歌榜(保底)"

    if not tracks:
        print("× 网易云全部失败，尝试公开API...")
        public_song = fetch_from_public_api()
        if public_song:
            return enrich_with_ai("song", public_song)

    if not tracks:
        print("× 所有来源均失败，使用备选歌曲")
        result = random.choice(FALLBACK_SONGS).copy()
        return enrich_with_ai("song", result)

    # 随机选择一首歌
    track = random.choice(tracks)
    print(f"✓ 获取歌曲：{track['name']} - {track['artists'][0]['name']} (来自{source_name})")
    hot_comment = get_song_comments(track['id'])
    if hot_comment:
        print(f"✓ 获取热评：{hot_comment['content'][:30]}...")

    cover_url = track['album'].get('picUrl') or track['album'].get('blurPicUrl') or "https://via.placeholder.com/300x300?text=No+Cover"
    result = {
        "name": track['name'],
        "artist": track['artists'][0]['name'],
        "album": track['album']['name'],
        "cover": cover_url,
        "comment": hot_comment or {"content": "暂无热评", "user": "系统"},
        "source": source_name
    }
    return enrich_with_ai("song", result)

# ==================== 每日一文 ====================
def fetch_article():
    # 同之前，请保留原有代码
    pass

# ==================== 每日一词 ====================
def fetch_word():
    # 同之前，请保留原有代码
    pass

# ==================== 主函数 ====================
def main():
    global _cached_song
    print(f"=== 每日数据爬虫（适配硅基流动 + 全球音乐增强版）开始运行 [{datetime.now().isoformat()}] ===")
    print(f"AI 状态: {'启用' if ENABLE_AI else '未启用'}")
    song = fetch_song()
    _cached_song = song
    today_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(),
        "sentence": fetch_sentence(),
        "song": song,
        "article": fetch_article(),
        "word": fetch_word(),
    }
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, 'daily.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据已保存至 {output_file}")
    print("=== 运行完成 ===")

if __name__ == "__main__":
    main()
