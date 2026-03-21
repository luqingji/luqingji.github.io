#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
每日数据爬虫（完整版 v1.0，每日三篇小说，高稳定性版）
- 每日一句：一言API
- 每日一曲：真实歌曲库（自建网易云API） + AI润色
- 每日一文：古诗文网 → 维基百科 → 备选
- 每日一词：优先从歌曲歌词提取 → 热搜备选
- 每日小说：AI生成 3 篇（每篇1000字以上，尽力1500，12种随机风格）
- 历史存档：自动保存每日数据
"""

import requests
import json
import random
import os
import re
import time
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区 ====================
API_BASE_URL = "https://api-enhanced-beta-drab.vercel.app"
# 如果接口需要 /api 前缀，请取消下一行注释并注释上一行
# API_BASE_URL = "https://api-enhanced-beta-drab.vercel.app/api"

SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_MODEL = os.environ.get('SILICONFLOW_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
ENABLE_AI = bool(SILICONFLOW_API_KEY)

_cached_song = None

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
os.makedirs(data_dir, exist_ok=True)

# ==================== 备选数据 ====================
FALLBACK_SENTENCES = [
    {"content": "生活不止眼前的苟且，还有诗和远方的田野", "from": "高晓松"},
    {"content": "愿你出走半生，归来仍是少年", "from": "网络"},
    {"content": "世界上只有一种真正的英雄主义，那就是在认清生活的真相后依然热爱生活", "from": "罗曼·罗兰"},
]

FALLBACK_SONGS = [
    {
        "name": "晴天",
        "artist": "周杰伦",
        "album": "叶惠美",
        "cover": "https://p2.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg",
        "comment": {"content": "从前从前，有个人爱你很久", "user": "网易云用户"},
        "meaning": "这是一首关于青春与遗憾的歌，旋律响起时，仿佛又回到那个蝉鸣的夏天。"
    },
    {
        "name": "夜曲",
        "artist": "周杰伦",
        "album": "11月的萧邦",
        "cover": "https://p2.music.126.net/8ZQ1M-Z5s8Wp0s5QqA8J8g==/109951164231440325.jpg",
        "comment": {"content": "纪念我死去的爱情", "user": "网易云用户"},
        "meaning": "悲伤的旋律下，是对逝去爱情的深切怀念。"
    },
]

FALLBACK_ARTICLES = [
    {"title": "荷塘月色", "description": "这几天心里颇不宁静。今晚在院子里坐着乘凉，忽然想起日日走过的荷塘，在这满月的光里，总该另有一番样子吧。", "author": "朱自清"},
    {"title": "匆匆", "description": "燕子去了，有再来的时候；杨柳枯了，有再青的时候；桃花谢了，有再开的时候。但是，聪明的，你告诉我，我们的日子为什么一去不复返呢？", "author": "朱自清"},
]

FALLBACK_WORDS = [
    {"word": "治愈", "description": "在音乐中找到内心的平静", "meaning": "治愈不是忘记伤痛，而是学会与伤痛共处。"},
    {"word": "怀旧", "description": "那些年我们一起听过的歌", "meaning": "怀旧不是沉溺过去，而是为了更清晰地看见来路。"},
    {"word": "励志", "description": "每一首歌都是一个故事", "meaning": "励志不是盲目的打鸡血，而是认清现实后依然选择前行。"},
]

FALLBACK_NOVELS = [
    {
        "title": "巷口的猫",
        "content": "老人每天傍晚都会在巷口喂一只流浪猫。猫从远处跑来，吃完后又消失在暮色里。直到有一天，猫带来了另一只小猫，它们一起蹲在老人脚边，老人笑了。"
    },
    {
        "title": "第三封信",
        "content": "她每周都会收到一封匿名信，信中预言的事情总在第二天发生。第一封信说“你会丢一把伞”，她果然丢了。第二封信说“你会遇到一个穿红裙子的女人”，她也遇到了。第三封信只有三个字：“回头看”。"
    },
    {
        "title": "最后一个人类",
        "content": "AI 城市里，最后一个人类躲在地下室。他有一本纸质书，每天读一页。AI 找到他时，他正读到最后一页：“我依然相信，人类的情感无法被算法取代。”"
    },
    {
        "title": "减肥计划",
        "content": "他发誓要减肥，于是在冰箱上贴了“少吃多动”。第二天，他买了一个新冰箱，因为旧冰箱上的字被遮住了。"
    },
    {
        "title": "井底的蛙",
        "content": "一只蛙住在井里，以为天空只有井口大。一天，一只鸟飞过，把它带出井。它看见了真正的天空，从此明白：局限不是边界，而是认知。"
    },
    {
        "title": "末班车",
        "content": "她每天乘末班车回家，总能遇见同一个男生。他们从未交谈，只是偶尔对视。直到某天，他递给她一张纸条：“明天开始，我调到早班了。”"
    },
    {
        "title": "会飞的扫帚",
        "content": "男孩在外婆的杂物间发现一把旧扫帚。他试着骑上去，扫帚竟然飞了起来。他飞过屋顶，飞过森林，最后落在外婆面前。外婆说：“这是你外公留下的。”"
    },
    {
        "title": "1919年的信",
        "content": "士兵在战壕里给未婚妻写信，信里夹了一朵野花。信还没寄出，他就被流弹击中。许多年后，这封信在博物馆展出，人们读着泛黄的字迹，沉默良久。"
    },
    {
        "title": "隔壁的脚步声",
        "content": "每晚十一点，楼上都会传来脚步声，一步一步，走到床边。但楼上根本没人住。她鼓起勇气上楼查看，发现房间里只有一面镜子，镜子里，她正走来。"
    },
    {
        "title": "流浪狗的自白",
        "content": "我是一条流浪狗，记得每个给过我食物的人。那个小男孩每天偷偷带面包给我，后来他搬家了，我在路口等了他三个月。"
    },
    {
        "title": "最好的礼物",
        "content": "妻子生日那天，他送给她一枚戒指。她看着戒指，突然哭了。他以为她太感动，她却说：“这是我三年前丢的那枚。”"
    },
    {
        "title": "雨天的站台",
        "content": "雨，站台，一个女孩在等车。她手中的书被风吹开，露出一片夹在扉页的枫叶。车来了，她收起书，上车，雨还在下。"
    }
]

# ==================== AI辅助函数 ====================
def call_ai(prompt, max_tokens=300, temperature=0.7, timeout=30):
    """调用硅基流动 API 生成文本，支持调节超时"""
    if not ENABLE_AI:
        return None
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": [
            {"role": "system", "content": "你是一位资深的音乐/文学/生活品味家，擅长用温暖、富有哲理的文字创作。"},
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
            print(f"AI调用失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"AI请求异常: {e}")
    return None

def enrich_with_ai(item_type, raw_data):
    """为不同类型的数据添加AI生成的meaning字段（仅用于句子、歌曲、文章）"""
    if not ENABLE_AI:
        return raw_data
    if item_type == "sentence":
        content = raw_data.get('content', '')
        from_ = raw_data.get('from', '')
        prompt = f"请为这句话写一段简短的解读（50-100字）：\n\n“{content}” —— {from_}"
        meaning = call_ai(prompt, max_tokens=150, timeout=15)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "song":
        name = raw_data.get('name', '')
        artist = raw_data.get('artist', '')
        album = raw_data.get('album', '')
        comment = raw_data.get('comment', {}).get('content', '')
        prompt = f"请为歌曲《{name}》- {artist}写一段推荐语（100-150字）。参考评论：{comment}"
        meaning = call_ai(prompt, max_tokens=250, timeout=20)
        if meaning:
            raw_data['meaning'] = meaning
    elif item_type == "article":
        title = raw_data.get('title', '')
        desc = raw_data.get('description', '')
        prompt = f"请为文章《{title}》写一段推荐语（80-120字）：{desc[:200]}"
        meaning = call_ai(prompt, max_tokens=200, timeout=15)
        if meaning:
            raw_data['meaning'] = meaning
    return raw_data

# ==================== 网易云API工具函数 ====================
def get_tracks_from_playlist(playlist_id, limit=50):
    url = f"{API_BASE_URL}/playlist/track/all?id={playlist_id}&limit={limit}&offset=0"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 200:
                songs = data.get('songs', [])
                return songs
    except Exception as e:
        print(f"获取歌单失败: {e}")
    return []

def update_song_library(force=False):
    library_file = os.path.join(data_dir, 'song_library.json')
    if not force and os.path.exists(library_file):
        mtime = os.path.getmtime(library_file)
        if (time.time() - mtime) < 7 * 24 * 3600:
            print("歌曲库较新，跳过更新")
            return
    BILLBOARDS = [3778678, 3779629, 19723756, 2884035, 60198, 3812895, 27126504, 71384707, 991319590, 2023401535]
    all_songs = []
    for bid in BILLBOARDS:
        songs = get_tracks_from_playlist(bid, limit=50)
        for s in songs:
            name = s.get('name', '').strip()
            if not name:
                continue
            artists = s.get('ar', [])
            artist = artists[0].get('name', '').strip() if artists else ''
            album = s.get('al', {}).get('name', '').strip()
            if name and artist:
                all_songs.append({"name": name, "artist": artist, "album": album if album else "未知专辑"})
        time.sleep(1)
    seen = set()
    unique = []
    for s in all_songs:
        key = f"{s['name']}|{s['artist']}"
        if key not in seen:
            seen.add(key)
            unique.append(s)
    with open(library_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"歌曲库已更新，共 {len(unique)} 首")

# ==================== 每日一曲 ====================
def fetch_song():
    print("正在获取每日一曲...")
    library_file = os.path.join(data_dir, 'song_library.json')
    if not os.path.exists(library_file):
        return fetch_song_ai_fallback()
    with open(library_file, 'r', encoding='utf-8') as f:
        library = json.load(f)
    if not library:
        return fetch_song_ai_fallback()
    chosen = random.choice(library)
    name, artist, album = chosen['name'], chosen['artist'], chosen.get('album', '未知专辑')
    comment = f"今日推荐：{name}"
    lyrics = ""
    if ENABLE_AI:
        prompt = f"请为歌曲《{name}》- {artist}写一段推荐语（80-120字），并附上一句歌词片段。输出JSON：{{\"comment\":\"...\", \"lyrics_snippet\":\"...\"}}"
        ai_resp = call_ai(prompt, max_tokens=300, temperature=0.5, timeout=15)
        if ai_resp:
            try:
                data = json.loads(ai_resp)
                comment = data.get('comment', '').strip() or comment
                lyrics = data.get('lyrics_snippet', '').strip()
            except:
                pass
    cover_url = f"https://picsum.photos/seed/{name.replace(' ', '')}/300/300"
    result = {
        "name": name, "artist": artist, "album": album, "cover": cover_url,
        "comment": {"content": comment, "user": "AI推荐官"},
        "lyrics_snippet": lyrics, "source": "真实歌曲库"
    }
    return enrich_with_ai("song", result)

def fetch_song_ai_fallback():
    print("使用纯AI生成备选歌曲")
    if not ENABLE_AI:
        return enrich_with_ai("song", random.choice(FALLBACK_SONGS).copy())
    return enrich_with_ai("song", random.choice(FALLBACK_SONGS).copy())

# ==================== 每日一句 ====================
def fetch_sentence():
    print("正在获取每日一句...")
    try:
        resp = requests.get("https://v1.hitokoto.cn/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = {"content": data["hitokoto"], "from": data.get("from", "未知")}
            print(f"✓ 获取成功：{result['content'][:30]}...")
            return enrich_with_ai("sentence", result)
    except Exception as e:
        print(f"× 异常：{e}")
    return enrich_with_ai("sentence", random.choice(FALLBACK_SENTENCES).copy())

# ==================== 每日一文 ====================
def fetch_article():
    print("正在获取每日一文...")
    # 古诗文网尝试
    try:
        url = "https://www.gushiwen.cn/random.aspx"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_tag = soup.find('h1') or soup.find('b')
            title = title_tag.text.strip() if title_tag else "无题"
            content_div = soup.find('div', class_='contson')
            content = content_div.text.strip() if content_div else ""
            source_tag = soup.find('p', class_='source')
            author = source_tag.text.strip() if source_tag else "佚名"
            if content:
                result = {"title": title, "description": content[:200]+"...", "content": content, "author": author, "source": "古诗文网"}
                return enrich_with_ai("article", result)
    except Exception as e:
        print(f"古诗文网失败: {e}")
    # 维基百科尝试
    try:
        today = datetime.now()
        url = f"https://zh.wikipedia.org/api/rest_v1/feed/featured/{today.year}/{today.month:02d}/{today.day:02d}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            tfa = data.get('tfa', {})
            if tfa:
                result = {"title": tfa.get('title'), "description": tfa.get('extract'), "url": tfa.get('content_urls',{}).get('desktop',{}).get('page'), "author": "维基百科", "source": "维基百科"}
                return enrich_with_ai("article", result)
    except Exception as e:
        print(f"维基百科失败: {e}")
    return enrich_with_ai("article", random.choice(FALLBACK_ARTICLES).copy())

# ==================== 每日一词 ====================
def fetch_word_from_song_lyrics():
    global _cached_song
    if _cached_song and _cached_song.get('lyrics_snippet'):
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', _cached_song['lyrics_snippet'])
        if words:
            return {"word": words[0][:8], "description": "来自今日歌曲歌词"}
    return None

def fetch_word_from_baidu():
    url = "https://top.baidu.com/board?tab=realtime"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200: raise Exception("百度失败")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first = soup.select_one('.c-single-text-ellipsis')
    if not first: raise Exception("百度解析失败")
    word = first.text.strip()
    hot_span = soup.select_one('.hot-index_1E1kp')
    hot = hot_span.text.strip() if hot_span else ""
    return {"word": word, "description": f"百度热搜 · {hot}"}

def fetch_word_from_zhihu():
    url = "https://www.zhihu.com/billboard"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200: raise Exception("知乎失败")
    soup = BeautifulSoup(resp.text, 'html.parser')
    topic = soup.select_one('.HotList-itemTitle')
    if not topic: raise Exception("知乎解析失败")
    word = topic.text.strip()
    hot = soup.select_one('.HotList-itemHot')
    hot_value = hot.text.strip() if hot else "未知热度"
    return {"word": word, "description": f"知乎热榜 · {hot_value}"}

def fetch_word_from_douban():
    url = "https://movie.douban.com/chart"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200: raise Exception("豆瓣失败")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_movie = soup.select_one('.pl2 a')
    if not first_movie: raise Exception("豆瓣解析失败")
    word = first_movie.text.strip().replace(' ', '').replace('\n', '')
    return {"word": word, "description": "豆瓣热门电影"}

def fetch_word_from_sspai():
    url = "https://sspai.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200: raise Exception("少数派失败")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_article = soup.select_one('.itemTitle a') or soup.select_one('h2 a')
    if not first_article: raise Exception("少数派解析失败")
    word = first_article.text.strip()
    return {"word": word, "description": "少数派热门文章"}

def fetch_word_from_weibo():
    url = "https://s.weibo.com/top/summary"
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200: raise Exception("微博失败")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_tr = soup.select_one('tbody tr:first-child')
    if not first_tr: raise Exception("微博解析失败")
    a_tag = first_tr.select_one('.td-02 a')
    if not a_tag: raise Exception("微博解析失败")
    word = a_tag.text.strip()
    hot_span = first_tr.select_one('.td-02 span')
    hot_value = hot_span.text.strip() if hot_span else ""
    return {"word": word, "description": f"微博热搜 · {hot_value}"}

def fetch_word_from_today_song():
    global _cached_song
    if _cached_song and _cached_song.get('comment'):
        comment = _cached_song['comment'].get('content', '')
        if comment:
            word = comment.split()[0][:5] if comment else None
            if word:
                return {"word": word, "description": "来自今日歌曲热评"}
    return None

def fetch_word():
    print("正在获取每日一词...")
    sources = [
        fetch_word_from_song_lyrics,
        fetch_word_from_baidu,
        fetch_word_from_zhihu,
        fetch_word_from_douban,
        fetch_word_from_sspai,
        fetch_word_from_weibo,
        fetch_word_from_today_song,
    ]
    random.shuffle(sources)
    for func in sources:
        try:
            result = func()
            if result and result.get('word'):
                print(f"✓ 成功：{result['word']}")
                return enrich_with_ai("word", result)
        except Exception as e:
            print(f"× 失败: {e}")
            continue
    return enrich_with_ai("word", random.choice(FALLBACK_WORDS).copy())

# ==================== 每日小说（3篇，高稳定性版） ====================
def clean_json_string(s):
    """强力修复 JSON 字符串"""
    s = s.strip()
    if s.startswith('\ufeff'):
        s = s[1:]
    # 移除控制字符
    s = re.sub(r'[\x00-\x1f\x7f]', '', s)
    # 修复缺失的逗号：在 " 后面跟着 " 的情况
    s = re.sub(r'\"\s+\"', '", "', s)
    # 修复末尾多余逗号
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r',\s*]', ']', s)
    # 修复键名没有引号的情况（简单处理，只匹配常见模式）
    s = re.sub(r'(\{|\s+|,)([a-zA-Z0-9_]+):', r'\1"\2":', s)
    return s

def extract_json(text):
    """提取第一个完整的 JSON 对象"""
    start = text.find('{')
    if start == -1:
        return None
    brace_count = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start:i+1]
    return None

def generate_one_novel():
    """生成一篇小说，带回退和重试，增强 JSON 清理，确保内容干净"""
    styles = [
        {"name": "温情治愈", "desc": "温暖人心的小故事，结局美好，充满希望。"},
        {"name": "悬疑推理", "desc": "带有悬念，引人思考，结局可能出人意料。"},
        {"name": "科幻未来", "desc": "设定在未来或科技背景下，探讨人性与技术。"},
        {"name": "幽默搞笑", "desc": "轻松诙谐，让人会心一笑或捧腹。"},
        {"name": "人生哲理", "desc": "蕴含深刻道理，引人深思，通过故事传递智慧。"},
        {"name": "都市情感", "desc": "现代城市中的情感故事，关于爱情、友情或亲情。"},
        {"name": "奇幻冒险", "desc": "奇幻世界或冒险旅程，充满想象力。"},
        {"name": "历史瞬间", "desc": "以历史事件或人物为背景，展现时代切片。"},
        {"name": "微恐怖", "desc": "轻微恐怖氛围，但不过分，结局留有想象空间。"},
        {"name": "动物视角", "desc": "以动物为主角，通过它们的眼睛看世界。"},
        {"name": "反转结局", "desc": "结尾出人意料，颠覆读者预期。"},
        {"name": "文艺唯美", "desc": "注重意境和文字美感，情节淡化，情绪为主。"},
    ]
    chosen = random.choice(styles)
    print(f"  生成小说 风格：{chosen['name']}")
    prompt = f"""
    请创作一篇短篇小说，严格按照以下要求：
    - 风格：{chosen['name']}（{chosen['desc']}）
    - 标题简洁有吸引力
    - 正文在1000-2500字之间，最好在1500字以上，情节完整，有起承转合，人物形象鲜明，场景描写细腻。
    - 适当加入反派或冲突元素（可以是人物、命运、环境等），增强故事张力。
    - 不要刻意压缩字数，充分展开故事，细节越丰富越好。
    - 按以下JSON格式输出，不要包含任何其他文字：
    {{
        "title": "小说标题",
        "content": "小说正文"
    }}
    """
    ai_resp = call_ai(prompt, max_tokens=10000, temperature=0.8, timeout=45)
    if not ai_resp:
        return None

    # 增强 JSON 提取：找到第一个 '{' 和匹配的 '}'
    start = ai_resp.find('{')
    if start == -1:
        print(f"  × 未找到JSON起始，AI响应片段: {ai_resp[:200]}")
        return None
    brace_count = 0
    end = start
    for i in range(start, len(ai_resp)):
        if ai_resp[i] == '{':
            brace_count += 1
        elif ai_resp[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    if end == start:
        print(f"  × 未找到完整JSON，AI响应片段: {ai_resp[:200]}")
        return None
    json_str = ai_resp[start:end+1]

    # 强力清理 JSON 字符串
    # 移除控制字符
    json_str = re.sub(r'[\x00-\x1f\x7f]', '', json_str)
    # 修复键名中可能的错误（例如缺少引号）
    json_str = re.sub(r'(\{|\,)\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', json_str)
    # 移除 JSON 字符串值中未转义的双引号（简单处理，仅针对 content 字段）
    # 但更稳妥的方法：先尝试解析，失败后尝试用正则提取 content 字段
    try:
        data = json.loads(json_str)
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        if title and content:
            word_count = len(content)
            if word_count < 1000:
                print(f"  × 字数不足1000（实际{word_count}），重试")
                return None
            # 移除内容中可能残留的 JSON 键名（例如 "content": ）
            # 如果内容开头恰好是 "content": 之类的，需要去掉
            content = re.sub(r'^\s*"content":\s*', '', content)
            print(f"  ✓ 生成成功：{title}，字数约{word_count}")
            return {"title": title, "content": content}
    except json.JSONDecodeError as e:
        print(f"  × JSON解析失败: {e}，尝试正则提取")
        # 使用正则直接提取 title 和 content
        title_match = re.search(r'"title"\s*:\s*"([^"]*?)"', json_str, re.DOTALL)
        content_match = re.search(r'"content"\s*:\s*"(.*?)"(?=\s*[,}])', json_str, re.DOTALL)
        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
            # 处理转义字符
            content = content.replace('\\"', '"').replace('\\n', '\n')
            if title and content:
                word_count = len(content)
                if word_count < 1000:
                    print(f"  × 字数不足1000（实际{word_count}），重试")
                    return None
                print(f"  ✓ 通过正则提取成功：{title}，字数约{word_count}")
                return {"title": title, "content": content}
    print(f"  × 解析失败，JSON片段: {json_str[:200]}")
    return None

def fetch_novels(n=3):
    """获取每日三篇小说，尽可能多地生成成功，不足部分用备选补全"""
    print("正在获取每日三篇小说...")
    novels = []
    for i in range(n):
        print(f"生成第 {i+1} 篇:")
        novel = None
        for attempt in range(5):  # 每篇最多尝试5次
            novel = generate_one_novel()
            if novel:
                break
            time.sleep(2)  # 重试前等待2秒
        if novel:
            novels.append(novel)
        else:
            fallback = random.choice(FALLBACK_NOVELS).copy()
            print(f"  使用备选小说：{fallback['title']}")
            novels.append(fallback)
    return novels

# ==================== 主函数 ====================
def main():
    global _cached_song
    bj_now = datetime.now(timezone.utc) + timedelta(hours=8)

    print(f"=== 每日数据爬虫 v1.0（每日三篇小说，高稳定性版）开始运行 [{bj_now.isoformat()}] ===")
    print(f"AI 状态: {'启用' if ENABLE_AI else '未启用'}")

    update_song_library(force=False)

    song = fetch_song()
    _cached_song = song

    today_data = {
        "date": bj_now.strftime("%Y-%m-%d"),
        "updated_at": bj_now.isoformat(),
        "sentence": fetch_sentence(),
        "song": song,
        "article": fetch_article(),
        "word": fetch_word(),
        "novels": fetch_novels(3),   # 三篇小说
    }

    output_file = os.path.join(data_dir, 'daily.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 每日数据已保存")

    # 历史存档
    date_str = today_data["date"]
    y, m, d = date_str.split('-')
    hist_dir = os.path.join(data_dir, 'history', y, m)
    os.makedirs(hist_dir, exist_ok=True)
    hist_file = os.path.join(hist_dir, f"{d}.json")
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    idx_file = os.path.join(data_dir, 'history', 'index.json')
    if os.path.exists(idx_file):
        with open(idx_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = []
    if date_str not in index:
        index.append(date_str)
        index.sort(reverse=True)
        with open(idx_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    print("=== 运行完成 ===")

if __name__ == "__main__":
    main()
