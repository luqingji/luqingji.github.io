#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
每日数据爬虫（精简版 v5.3）
- 保留：每日总结、早报、ONE·一个、歌单、彩蛋、照片墙
- 新增：自动记录 ONE 文章标题到 one_articles.json
- 统计：总字数统计 ONE 文章纯文本字数
"""

import os
import sys
import json
import random
import re
import time
import logging
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================
API_BASE_URL = "https://api-enhanced-beta-drab.vercel.app"
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')

MODEL_WRITING = 'Qwen/Qwen2.5-7B-Instruct'

ENABLE_AI = bool(SILICONFLOW_API_KEY)
ALAPI_TOKEN = os.environ.get('ALAPI_TOKEN')

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
os.makedirs(data_dir, exist_ok=True)

# ==================== 备选数据（仅用于非 AI 模块） ====================
FALLBACK_SENTENCES = [
    {"content": "生活不止眼前的苟且，还有诗和远方的田野", "from": "高晓松"},
    {"content": "愿你出走半生，归来仍是少年", "from": "网络"},
    {"content": "世界上只有一种真正的英雄主义，那就是在认清生活的真相后依然热爱生活", "from": "罗曼·罗兰"},
]

FALLBACK_ARTICLES = [
    {"title": "荷塘月色", "description": "这几天心里颇不宁静。今晚在院子里坐着乘凉，忽然想起日日走过的荷塘，在这满月的光里，总该另有一番样子吧。", "author": "朱自清"},
    {"title": "匆匆", "description": "燕子去了，有再来的时候；杨柳枯了，有再青的时候；桃花谢了，有再开的时候。但是，聪明的，你告诉我，我们的日子为什么一去不复返呢？", "author": "朱自清"},
]

STATIC_EASTER_EGGS = [
    "🥚 今日彩蛋：再读一遍，或许会发现隐藏的温柔。",
    "🥚 今日彩蛋：时光不语，静待花开。",
    "🥚 今日彩蛋：每一段文字都是时光的琥珀。",
    "🥚 今日彩蛋：未知旋律里藏着昨天的故事。",
    "🥚 今日彩蛋：散落的诗行，是某人的心事。",
    "🥚 今日彩蛋：你正在阅读的，是宇宙送给你的礼物。",
    "🥚 今日彩蛋：此刻的宁静，胜过万语千言。",
    "🥚 今日彩蛋：读一段文字，饮一杯暖茶。"
]

# ==================== AI 调用 ====================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=45))
def call_ai(prompt: str, max_tokens: int = 300, temperature: float = 0.7, timeout: int = 60) -> Optional[str]:
    if not ENABLE_AI:
        return None
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_WRITING,
        "messages": [
            {"role": "system", "content": "你是一位资深音乐/文学/生活品味家，擅长用温暖、富有哲理的文字创作。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    try:
        resp = requests.post(f"{SILICONFLOW_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        else:
            logger.error(f"AI调用失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"AI请求异常: {e}")
    return None

def enrich_with_ai(item_type: str, raw_data: dict) -> dict:
    if not ENABLE_AI:
        return raw_data
    if item_type == "sentence":
        content = raw_data.get('content', '')
        from_ = raw_data.get('from', '')
        prompt = f"请为这句话写一段简短的解读（50-100字）：\n\n“{content}” —— {from_}"
        meaning = call_ai(prompt, max_tokens=150, timeout=30)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "article":
        title = raw_data.get('title', '')
        desc = raw_data.get('description', '')
        prompt = f"请为文章《{title}》写一段推荐语（80-120字）：{desc[:200]}"
        meaning = call_ai(prompt, max_tokens=200, timeout=30)
        if meaning:
            raw_data['meaning'] = meaning
    return raw_data

# ==================== 歌曲库 ====================
def get_tracks_from_playlist(playlist_id: int, limit: int = 50) -> list:
    url = f"{API_BASE_URL}/playlist/track/all?id={playlist_id}&limit={limit}&offset=0"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 200:
                songs = data.get('songs', [])
                return [{
                    "id": s.get('id'),
                    "name": s.get('name', '').strip(),
                    "artist": s.get('ar', [{}])[0].get('name', '').strip(),
                    "album": s.get('al', {}).get('name', '').strip()
                } for s in songs if s.get('name') and s.get('ar')]
    except Exception as e:
        logger.error(f"获取歌单失败: {e}")
    return []

def update_song_library(force: bool = False):
    library_file = os.path.join(data_dir, 'song_library.json')
    need_update = force
    if not need_update and os.path.exists(library_file):
        try:
            with open(library_file, 'r', encoding='utf-8') as f:
                lib = json.load(f)
            if lib and 'id' not in lib[0]:
                logger.info("检测到旧版歌曲库（无ID），将强制更新")
                need_update = True
        except:
            need_update = True
    if not need_update and os.path.exists(library_file):
        mtime = os.path.getmtime(library_file)
        if (time.time() - mtime) < 7 * 24 * 3600:
            logger.info("歌曲库较新且包含ID，跳过更新")
            return
    logger.info("正在更新歌曲库...")
    BILLBOARDS = [3778678, 3779629, 19723756, 2884035, 60198, 3812895, 27126504, 71384707, 991319590, 2023401535]
    all_songs = []
    for bid in BILLBOARDS:
        songs = get_tracks_from_playlist(bid, limit=50)
        all_songs.extend(songs)
        time.sleep(1)
    seen = set()
    unique = []
    for s in all_songs:
        if s['id'] and s['id'] not in seen:
            seen.add(s['id'])
            unique.append(s)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=data_dir, delete=False) as tmp:
        json.dump(unique, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, library_file)
    logger.info(f"歌曲库已更新，共 {len(unique)} 首")

def fetch_songs(n: int = 6) -> List[Dict]:
    logger.info("正在获取每日歌单...")
    library_file = os.path.join(data_dir, 'song_library.json')
    if not os.path.exists(library_file):
        logger.warning("歌曲库不存在，使用备选歌单")
        return fetch_songs_ai_fallback(n)
    with open(library_file, 'r', encoding='utf-8') as f:
        library = json.load(f)
    if not library:
        logger.warning("歌曲库为空，使用备选歌单")
        return fetch_songs_ai_fallback(n)
    if len(library) < n:
        selected = random.sample(library, len(library))
        while len(selected) < n:
            selected += random.sample(library, min(n - len(selected), len(library)))
    else:
        selected = random.sample(library, n)
    songs = []
    for item in selected:
        name = item['name']
        artist = item['artist']
        album = item.get('album', '未知专辑')
        song_id = item.get('id')
        prompt = f"请为歌曲《{name}》- {artist}写一句简短的推荐语（30字以内），说明这首歌给人的感觉或推荐理由。"
        recommendation = call_ai(prompt, max_tokens=100, temperature=0.7, timeout=20)
        if not recommendation:
            recommendation = "一首动人的旋律。"
        songs.append({
            "id": song_id,
            "name": name,
            "artist": artist,
            "album": album,
            "recommendation": recommendation
        })
        time.sleep(1)
    return songs

def fetch_songs_ai_fallback(n: int = 6) -> List[Dict]:
    fallback_songs = [
        {"id": 186016, "name": "晴天", "artist": "周杰伦", "album": "叶惠美"},
        {"id": 141268, "name": "夜曲", "artist": "周杰伦", "album": "11月的萧邦"},
        {"id": 190017, "name": "海阔天空", "artist": "Beyond", "album": "乐与怒"},
        {"id": 5252590, "name": "稻香", "artist": "周杰伦", "album": "魔杰座"},
        {"id": 449833, "name": "平凡之路", "artist": "朴树", "album": "平凡之路"},
        {"id": 27591777, "name": "岁月神偷", "artist": "金玟岐", "album": "金玟岐作品集"},
    ]
    songs = []
    for i in range(n):
        s = fallback_songs[i % len(fallback_songs)]
        songs.append({
            "id": s["id"],
            "name": s["name"],
            "artist": s["artist"],
            "album": s["album"],
            "recommendation": f"这首《{s['name']}》是经典之作，值得反复聆听。"
        })
    return songs

# ==================== 每日一句 ====================
def fetch_sentence() -> dict:
    logger.info("正在获取每日一句...")
    if ALAPI_TOKEN:
        try:
            types = [1,2,3,4,5,6,7,8]
            type_choice = random.choice(types)
            url = f"https://v3.alapi.cn/api/hitokoto?token={ALAPI_TOKEN}&type={type_choice}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success') and data.get('data'):
                    result = {
                        "content": data['data'].get('hitokoto', ''),
                        "from": data['data'].get('from', '未知')
                    }
                    logger.info(f"✓ 从 ALAPI 获取成功：{result['content'][:30]}...")
                    return enrich_with_ai("sentence", result)
        except Exception as e:
            logger.error(f"ALAPI 获取失败: {e}")
    try:
        url = "https://v1.hitokoto.cn/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "content": data["hitokoto"],
                "from": data.get("from", "未知")
            }
            logger.info(f"✓ 从原有一言获取成功：{result['content'][:30]}...")
            return enrich_with_ai("sentence", result)
    except Exception as e:
        logger.error(f"原有一言接口异常: {e}")
    logger.warning("所有来源均失败，使用备选句子")
    result = random.choice(FALLBACK_SENTENCES).copy()
    return enrich_with_ai("sentence", result)

# ==================== 每日一文 ====================
def fetch_article() -> dict:
    logger.info("正在获取每日一文...")
    sources = [fetch_zhihu, fetch_gushiwen, fetch_wikipedia]
    random.shuffle(sources)
    for source_func in sources:
        try:
            result = source_func()
            if result:
                logger.info(f"✓ 从 {result['source']} 获取：{result['title']}")
                return enrich_with_ai("article", result)
        except Exception as e:
            logger.error(f"源 {source_func.__name__} 失败: {e}")
            continue
    logger.warning("所有来源均失败，使用备选文章")
    result = random.choice(FALLBACK_ARTICLES).copy()
    return enrich_with_ai("article", result)

def fetch_zhihu() -> Optional[dict]:
    if not ALAPI_TOKEN:
        return None
    try:
        list_url = f"https://v3.alapi.cn/api/zhihu?token={ALAPI_TOKEN}"
        resp = requests.get(list_url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get('success') or not data.get('data', {}).get('stories'):
            return None
        stories = data['data']['stories']
        story = random.choice(stories)
        story_id = story.get('id')
        title = story.get('title', '知乎日报')
        detail_url = f"https://v3.alapi.cn/api/zhihu/news?token={ALAPI_TOKEN}&id={story_id}"
        detail_resp = requests.get(detail_url, timeout=10)
        content = ""
        if detail_resp.status_code == 200:
            detail_data = detail_resp.json()
            if detail_data.get('success') and detail_data.get('data'):
                body = detail_data['data'].get('body', '')
                if body:
                    soup = BeautifulSoup(body, 'html.parser')
                    content = soup.get_text()
        return {
            "title": title,
            "description": (content[:200] + "...") if content else title,
            "content": content,
            "author": "知乎日报",
            "url": story.get('url', ''),
            "source": "知乎日报"
        }
    except Exception as e:
        logger.error(f"知乎日报抓取异常: {e}")
        return None

def fetch_gushiwen() -> Optional[dict]:
    try:
        url = "https://www.gushiwen.cn/random.aspx"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        title_tag = soup.find('h1') or soup.find('b')
        title = title_tag.text.strip() if title_tag else "无题"
        content_div = soup.find('div', class_='contson')
        content = content_div.text.strip() if content_div else ""
        source_tag = soup.find('p', class_='source')
        author = source_tag.text.strip() if source_tag else "佚名"
        if not content:
            return None
        return {
            "title": title,
            "description": content[:200] + "...",
            "content": content,
            "author": author,
            "source": "古诗文网"
        }
    except Exception as e:
        logger.error(f"古诗文网抓取异常: {e}")
        return None

def fetch_wikipedia() -> Optional[dict]:
    try:
        today = datetime.now()
        url = f"https://zh.wikipedia.org/api/rest_v1/feed/featured/{today.year}/{today.month:02d}/{today.day:02d}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        tfa = data.get('tfa', {})
        if not tfa:
            return None
        return {
            "title": tfa.get('title', ''),
            "description": tfa.get('extract', ''),
            "url": tfa.get('content_urls', {}).get('desktop', {}).get('page', ''),
            "author": "维基百科",
            "source": "维基百科"
        }
    except Exception as e:
        logger.error(f"维基百科抓取异常: {e}")
        return None

# ==================== 每日总结 ====================
def generate_summary(data: dict) -> str:
    if not ENABLE_AI:
        return "今日拾光，愿您有所获。"
    sentence_content = data.get('sentence', {}).get('content', '')
    songs = data.get('songs', [])
    if songs:
        song_name = songs[0]['name']
        song_artist = songs[0]['artist']
    else:
        song_name = "未知"
        song_artist = "未知"
    article_title = data.get('article', {}).get('title', '')
    prompt = f"""
    请根据以下今日内容，用一句简短、诗意的话概括它们共同的主题或情绪（20-40字）：
    每日一句：{sentence_content}
    每日歌单示例：《{song_name}》- {song_artist}
    每日一文：《{article_title}》
    """
    ai_resp = call_ai(prompt, max_tokens=150, temperature=0.7, timeout=20)
    if ai_resp:
        return ai_resp.strip('"').strip()
    else:
        return "今日拾光，愿您有所获。"

# ==================== 每日早报 ====================
def fetch_zaobao() -> Optional[dict]:
    if not ALAPI_TOKEN:
        logger.warning("未设置 ALAPI_TOKEN，跳过早报")
        return None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            url = f"https://v3.alapi.cn/api/zaobao?token={ALAPI_TOKEN}&format=json"
            resp = requests.get(url, headers=headers, timeout=15)
            logger.info(f"早报请求尝试 {attempt}: HTTP {resp.status_code}")
            if resp.status_code != 200:
                logger.warning(f"响应内容前200字符: {resp.text[:200]}")
                continue
            try:
                data = resp.json()
            except ValueError:
                logger.error(f"JSON解析失败，原始响应: {resp.text[:500]}")
                continue
            if not isinstance(data, dict) or not data.get('success'):
                logger.warning(f"接口返回失败: {data.get('message', '未知错误')}")
                continue
            zaobao_data = data.get('data')
            if not zaobao_data or not isinstance(zaobao_data, dict):
                logger.warning(f"data字段无效: {type(zaobao_data)}")
                return {"date": "", "news": [], "weiyu": ""}
            news_list = zaobao_data.get('news', [])
            if not isinstance(news_list, list):
                logger.warning(f"news字段类型不是列表: {type(news_list)}")
                return {"date": zaobao_data.get('date', ''), "news": [], "weiyu": ""}
            valid_news = []
            for item in news_list:
                if isinstance(item, str) and item.strip():
                    valid_news.append({
                        "title": item,
                        "content": item,
                        "source": "",
                        "summary": "",
                        "url": ""
                    })
            weiyu = zaobao_data.get('weiyu', '')
            if weiyu:
                weiyu = weiyu.replace('【微语】', '').strip()
            logger.info(f"早报获取成功，共 {len(valid_news)} 条新闻")
            return {
                "date": zaobao_data.get('date', ''),
                "news": valid_news,
                "weiyu": weiyu,
                "image": zaobao_data.get('image', ''),
                "audio": zaobao_data.get('audio', '')
            }
        except requests.Timeout:
            logger.error(f"早报请求超时 (尝试 {attempt})")
        except requests.ConnectionError:
            logger.error(f"早报网络连接错误 (尝试 {attempt})")
        except requests.RequestException as e:
            logger.error(f"早报网络异常 (尝试 {attempt}): {e}")
        except Exception as e:
            logger.error(f"早报未知异常 (尝试 {attempt}): {e}")
        if attempt < max_attempts:
            wait_time = 2 ** attempt
            logger.info(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    logger.error("早报获取失败，返回空数据")
    return {"date": "", "news": [], "weiyu": ""}

# ==================== 彩蛋 ====================
def generate_easter_egg() -> str:
    if not ENABLE_AI:
        return random.choice(STATIC_EASTER_EGGS)
    prompt = "请写一句诗意、温馨、鼓励性的短句（20字以内），用于网站的每日彩蛋。"
    try:
        egg = call_ai(prompt, max_tokens=50, temperature=0.9, timeout=10)
        if egg:
            return egg.strip('"\'').strip()
    except Exception as e:
        logger.error(f"生成彩蛋失败: {e}")
    return random.choice(STATIC_EASTER_EGGS)

# ==================== ONE 文章存档 ====================
def update_one_archive(date: str, title: str):
    """记录 ONE 文章标题到 one_articles.json"""
    if not title:
        return
    archive_file = os.path.join(data_dir, 'one_articles.json')
    if os.path.exists(archive_file):
        with open(archive_file, 'r', encoding='utf-8') as f:
            try:
                archive = json.load(f)
            except:
                archive = []
    else:
        archive = []
    existing = [item for item in archive if item.get('date') == date]
    if existing:
        existing[0]['title'] = title
    else:
        archive.append({"date": date, "title": title})
    archive.sort(key=lambda x: x['date'], reverse=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=data_dir, delete=False) as tmp:
        json.dump(archive, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, archive_file)
    logger.info(f"已记录 ONE 文章：{date} - {title}")

# ==================== 照片墙记录 ====================
def update_photo_wall(date: str, photo_data: dict):
    """将每日 ONE·摄影图片添加到照片墙 JSON 中"""
    photo_file = os.path.join(data_dir, 'photos.json')
    if os.path.exists(photo_file):
        with open(photo_file, 'r', encoding='utf-8') as f:
            try:
                photos = json.load(f)
            except:
                photos = []
    else:
        photos = []
    existing = [p for p in photos if p.get('date') == date]
    if existing:
        existing[0].update({
            "title": photo_data.get('title', ''),
            "author": photo_data.get('author', ''),
            "description": photo_data.get('description', ''),
            "image": photo_data.get('image', ''),
            "src": photo_data.get('image', '')
        })
    else:
        photos.append({
            "date": date,
            "title": photo_data.get('title', ''),
            "author": photo_data.get('author', ''),
            "description": photo_data.get('description', ''),
            "image": photo_data.get('image', ''),
            "src": photo_data.get('image', '')
        })
    photos.sort(key=lambda x: x['date'], reverse=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=data_dir, delete=False) as tmp:
        json.dump(photos, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, photo_file)
    logger.info(f"已添加/更新照片墙：{date} - {photo_data.get('title', '')}")

# ==================== ONE · 一个 模块 ====================
def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator='\n')
    text = re.sub(r'这里藏着一张图片，前往应用商店，下载「一个」最新版本查看！', '', text)
    text = re.sub(r'这里藏着一张图片，前往应用商店，下载「一个」最新版本查看', '', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n\n'.join(lines)

def _fetch_one_api(url: str, name: str) -> Optional[Dict]:
    if not ALAPI_TOKEN:
        return None
    max_retries = 3
    for retry in range(max_retries):
        try:
            if retry > 0:
                wait = 2 ** retry + random.uniform(0.5, 1.5)
                logger.info(f"ONE{name} 等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)
            else:
                time.sleep(random.uniform(0.5, 1.5))
            payload = {"token": ALAPI_TOKEN, "date": ""}
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"ONE{name}请求失败: HTTP {resp.status_code}")
                continue
            data = resp.json()
            if not data.get('success'):
                msg = data.get('message', '')
                logger.warning(f"ONE{name}接口错误: {msg}")
                if '请求次数过多' in msg or data.get('code') == 10002:
                    time.sleep(5)
                    continue
                return None
            return data.get('data', {})
        except Exception as e:
            logger.error(f"ONE{name}抓取异常 (尝试{retry+1}): {e}")
            time.sleep(2)
    return None

def fetch_one_article() -> Optional[Dict[str, Any]]:
    data = _fetch_one_api("https://v3.alapi.cn/api/one", "文章")
    if not data:
        return None
    content = data.get('content', '')
    if content:
        content = clean_html(content)
    return {
        "title": data.get('title', ''),
        "author": data.get('author', ''),
        "content": content,
        "url": data.get('url', ''),
        "img_url": data.get('img_url', '')
    }

def fetch_one_photo() -> Optional[Dict[str, Any]]:
    data = _fetch_one_api("https://v3.alapi.cn/api/one/photo", "摄影")
    if not data:
        return None
    description = data.get('content', '')
    if description:
        description = clean_html(description)
    return {
        "title": data.get('title', ''),
        "author": data.get('subtitle', ''),
        "image": data.get('cover', ''),
        "description": description,
        "url": data.get('url', '')
    }

def fetch_one_question() -> Optional[Dict[str, Any]]:
    data = _fetch_one_api("https://v3.alapi.cn/api/one/question", "问答")
    if not data:
        return None
    answer = data.get('answer', '')
    if answer:
        answer = clean_html(answer)
    return {
        "question": data.get('question', ''),
        "answer": answer,
        "author": data.get('author', '')
    }

# ==================== 原子写入 ====================
def safe_write_json(data: dict, filepath: str):
    dirname = os.path.dirname(filepath)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=dirname, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, filepath)

# ==================== 统计生成（修改为统计 ONE 文章字数） ====================
def generate_stats():
    history_dir = os.path.join(data_dir, 'history')
    if not os.path.exists(history_dir):
        logger.warning("history目录不存在，无法生成统计")
        return
    total_days = 0
    total_songs = 0
    total_articles = 0
    total_words = 0
    total_recommend_words = 0
    total_news_items = 0
    total_one_items = 0
    for root, dirs, files in os.walk(history_dir):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    total_days += 1
                    songs = data.get('songs', [])
                    if songs:
                        total_songs += len(songs)
                        for song in songs:
                            rec = song.get('recommendation', '')
                            total_recommend_words += len(rec)
                    # 统计 ONE 文章字数
                    one_article = data.get('one', {}).get('article')
                    if one_article and one_article.get('content'):
                        total_articles += 1
                        content = one_article.get('content', '')
                        if content:
                            content = re.sub(r'<[^>]+>', '', content)
                            total_words += len(content)
                    zaobao = data.get('zaobao')
                    if zaobao and zaobao.get('news'):
                        total_news_items += len(zaobao['news'])
                    one = data.get('one')
                    if one:
                        if one.get('article'):
                            total_one_items += 1
                        if one.get('photo'):
                            total_one_items += 1
                        if one.get('question'):
                            total_one_items += 1
                except Exception as e:
                    logger.error(f"读取历史文件失败 {filepath}: {e}")
    read_minutes = total_words // 300 if total_words else 0
    stats = {
        "total_days": total_days,
        "total_songs": total_songs,
        "total_articles": total_articles,
        "total_words": total_words,
        "total_recommend_words": total_recommend_words,
        "total_news_items": total_news_items,
        "total_one_items": total_one_items,
        "read_minutes": read_minutes,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    stats_file = os.path.join(data_dir, 'stats.json')
    safe_write_json(stats, stats_file)
    logger.info(f"统计生成：总天数 {total_days}，歌曲 {total_songs}，ONE文章数 {total_articles}，总字数 {total_words}，早报条数 {total_news_items}，ONE内容 {total_one_items}")

# ==================== 主函数 ====================
def main():
    if not ENABLE_AI:
        logger.warning("SILICONFLOW_API_KEY 未设置，AI功能关闭")
    if not ALAPI_TOKEN:
        logger.warning("ALAPI_TOKEN 未设置，部分功能可能不可用")
    utc_now = datetime.now(timezone.utc)
    beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
    logger.info(f"=== 每日数据爬虫 v5.3 开始运行 [{utc_now.isoformat()}] ===")
    logger.info(f"AI 状态: {'启用' if ENABLE_AI else '未启用'}")

    update_song_library(force=False)
    songs = fetch_songs(6)
    easter = generate_easter_egg()

    # 获取 ONE 模块（文章、摄影、问答）
    one_article = fetch_one_article()
    one_photo = fetch_one_photo()
    one_question = fetch_one_question()

    today_data = {
        "date": beijing_now.strftime("%Y-%m-%d"),
        "updated_at": utc_now.isoformat(),
        "sentence": fetch_sentence(),
        "songs": songs,
        "article": fetch_article(),
        "zaobao": fetch_zaobao(),
        "one": {
            "article": one_article,
            "photo": one_photo,
            "question": one_question
        },
        "easter": easter
    }

    summary = generate_summary(today_data)
    today_data['summary'] = summary
    logger.info(f"📝 每日总结：{summary}")

    # 记录 ONE 文章标题到存档
    if one_article and one_article.get('title'):
        update_one_archive(today_data['date'], one_article['title'])

    # 记录 ONE·摄影到照片墙
    if one_photo and one_photo.get('image'):
        update_photo_wall(today_data['date'], one_photo)

    output_file = os.path.join(data_dir, 'daily.json')
    safe_write_json(today_data, output_file)
    logger.info("✅ 每日数据已保存")

    date_str = today_data["date"]
    y, m, d = date_str.split('-')
    hist_dir = os.path.join(data_dir, 'history', y, m)
    hist_file = os.path.join(hist_dir, f"{d}.json")
    safe_write_json(today_data, hist_file)

    generate_stats()
    logger.info("=== 运行完成 ===")

if __name__ == "__main__":
    main()
