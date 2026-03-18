#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
每日数据爬虫（适配硅基流动 + AI生成每日一曲）
- 每日一句：一言API
- 每日一曲：完全由AI生成（使用硅基流动）
- 每日一文：古诗文网随机诗词 → 维基百科 → 备选文章库
- 每日一词：百度/知乎/豆瓣/少数派/微博 → 备选词库
- AI 增强：使用硅基流动 API 生成 meaning 字段
"""

import requests
import json
import random
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import urllib3
# 禁用 SSL 警告（仅用于可能的外部请求，AI 生成模式基本用不到）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== AI 配置（硅基流动）====================
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
SILICONFLOW_BASE_URL = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_MODEL = os.environ.get('SILICONFLOW_MODEL', 'Qwen/Qwen2.5-7B-Instruct')  # 免费模型

ENABLE_AI = bool(SILICONFLOW_API_KEY)

# 用于在每日一词中引用今日歌曲评论的缓存
_cached_song = None

# ==================== 备选数据 ====================

FALLBACK_SENTENCES = [
    {"content": "生活不止眼前的苟且，还有诗和远方的田野", "from": "高晓松"},
    {"content": "愿你出走半生，归来仍是少年", "from": "网络"},
    {"content": "世界上只有一种真正的英雄主义，那就是在认清生活的真相后依然热爱生活", "from": "罗曼·罗兰"},
    {"content": "黑夜无论怎样悠长，白昼总会到来", "from": "莎士比亚"},
    {"content": "活着，就要活到袒胸露背迎接万箭攒头，犹能举头对苍天一笑的境地", "from": "简媜"},
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
    {"title": "春", "description": "盼望着，盼望着，东风来了，春天的脚步近了。一切都像刚睡醒的样子，欣欣然张开了眼。", "author": "朱自清"},
    {"title": "背影", "description": "我与父亲不相见已二年余了，我最不能忘记的是他的背影。", "author": "朱自清"},
    {"title": "济南的冬天", "description": "对于一个在北平住惯的人，像我，冬天要是不刮风，便觉得是奇迹；济南的冬天是没有风声的。", "author": "老舍"},
    {"title": "故都的秋", "description": "秋天，无论在什么地方的秋天，总是好的；可是啊，北国的秋，却特别地来得清，来得静，来得悲凉。", "author": "郁达夫"},
    {"title": "雨巷", "description": "撑着油纸伞，独自彷徨在悠长，悠长又寂寥的雨巷，我希望逢着一个丁香一样的结着愁怨的姑娘。", "author": "戴望舒"},
    {"title": "再别康桥", "description": "轻轻的我走了，正如我轻轻的来；我轻轻的招手，作别西天的云彩。", "author": "徐志摩"},
    {"title": "面朝大海，春暖花开", "description": "从明天起，做一个幸福的人，喂马、劈柴，周游世界。", "author": "海子"},
    {"title": "乡愁", "description": "小时候，乡愁是一枚小小的邮票，我在这头，母亲在那头。", "author": "余光中"},
    {"title": "致橡树", "description": "我如果爱你——绝不像攀援的凌霄花，借你的高枝炫耀自己。", "author": "舒婷"},
    {"title": "相信未来", "description": "当蜘蛛网无情地查封了我的炉台，当灰烬的余烟叹息着贫困的悲哀，我依然固执地铺平失望的灰烬，用美丽的雪花写下：相信未来。", "author": "食指"},
    {"title": "陋室铭", "description": "山不在高，有仙则名。水不在深，有龙则灵。斯是陋室，惟吾德馨。", "author": "刘禹锡"},
    {"title": "爱莲说", "description": "水陆草木之花，可爱者甚蕃。晋陶渊明独爱菊。自李唐来，世人甚爱牡丹。予独爱莲之出淤泥而不染，濯清涟而不妖。", "author": "周敦颐"},
    {"title": "小石潭记", "description": "从小丘西行百二十步，隔篁竹，闻水声，如鸣佩环，心乐之。", "author": "柳宗元"},
    {"title": "岳阳楼记", "description": "庆历四年春，滕子京谪守巴陵郡。越明年，政通人和，百废具兴，乃重修岳阳楼。", "author": "范仲淹"},
    {"title": "醉翁亭记", "description": "环滁皆山也。其西南诸峰，林壑尤美。望之蔚然而深秀者，琅琊也。", "author": "欧阳修"},
    {"title": "桃花源记", "description": "晋太元中，武陵人捕鱼为业。缘溪行，忘路之远近。忽逢桃花林，夹岸数百步，中无杂树，芳草鲜美，落英缤纷。", "author": "陶渊明"},
    {"title": "兰亭集序", "description": "永和九年，岁在癸丑，暮春之初，会于会稽山阴之兰亭，修禊事也。", "author": "王羲之"},
    {"title": "前赤壁赋", "description": "壬戌之秋，七月既望，苏子与客泛舟游于赤壁之下。清风徐来，水波不兴。", "author": "苏轼"},
]

FALLBACK_WORDS = [
    {"word": "治愈", "description": "在音乐中找到内心的平静", "meaning": "治愈不是忘记伤痛，而是学会与伤痛共处，并从中汲取力量。"},
    {"word": "怀旧", "description": "那些年我们一起听过的歌", "meaning": "怀旧不是沉溺过去，而是为了更清晰地看见来路。"},
    {"word": "励志", "description": "每一首歌都是一个故事", "meaning": "励志不是盲目的打鸡血，而是认清现实后依然选择前行。"},
    {"word": "孤独", "description": "一个人的时候，你听见了世界", "meaning": "孤独是自我对话的珍贵时刻。"},
    {"word": "希望", "description": "黑夜无论怎样悠长，白昼总会到来", "meaning": "希望是黑暗中永不熄灭的微光。"},
    {"word": "勇气", "description": "真正的勇气，是含着泪奔跑", "meaning": "勇气不是不害怕，而是害怕后依然向前。"},
    {"word": "成长", "description": "成长就是学会与不完美的自己和解", "meaning": "每一次跌倒都是成长的伏笔。"},
    {"word": "梦想", "description": "梦想是注定孤独的旅行", "meaning": "有梦想的人，永远年少。"},
    {"word": "陪伴", "description": "最长情的告白是陪伴", "meaning": "陪伴是最温暖的治愈。"},
    {"word": "告别", "description": "每一次告别，都是新的开始", "meaning": "学会告别，是人生的必修课。"},
    {"word": "坚持", "description": "不是因为看到希望才坚持，而是坚持了才看到希望", "meaning": "坚持让平凡变得伟大。"},
    {"word": "珍惜", "description": "珍惜眼前人，心中无黄昏", "meaning": "珍惜当下，是最好的生活态度。"},
    {"word": "初心", "description": "不忘初心，方得始终", "meaning": "初心是出发时的那份纯粹。"},
    {"word": "释怀", "description": "放过自己，与过去和解", "meaning": "释怀是给心灵松绑。"},
    {"word": "温暖", "description": "愿有人问你粥可温", "meaning": "温暖是世间最柔软的力量。"},
    {"word": "自由", "description": "真正的自由，是内心的从容", "meaning": "自由不是随心所欲，而是自我主宰。"},
    {"word": "简单", "description": "简单是复杂的最高境界", "meaning": "简单的生活，往往最有力。"},
    {"word": "相信", "description": "相信美好，终会遇见美好", "meaning": "相信是一种能力，也是一种选择。"},
    {"word": "热爱", "description": "热爱可抵岁月漫长", "meaning": "热爱让平凡的日子闪闪发光。"},
    {"word": "平静", "description": "内心平静，世界便安静了", "meaning": "平静是喧嚣中的一座孤岛。"},
    {"word": "从容", "description": "宠辱不惊，看庭前花开花落", "meaning": "从容是历经风雨后的淡定。"},
    {"word": "豁达", "description": "去留无意，望天上云卷云舒", "meaning": "豁达是心胸的开阔。"},
    {"word": "感恩", "description": "滴水之恩，涌泉相报", "meaning": "感恩让生活充满阳光。"},
    {"word": "善良", "description": "善良是灵魂的香味", "meaning": "善良是人性中最温暖的光。"},
    {"word": "真诚", "description": "真诚是通往一切的桥梁", "meaning": "真诚是最高级的情商。"},
    {"word": "专注", "description": "专注是成功的基石", "meaning": "专注让人在纷扰中守住内心。"},
    {"word": "沉淀", "description": "沉淀是为了更好的出发", "meaning": "沉淀是给时间以生命。"},
    {"word": "淡然", "description": "淡然于心，从容于表", "meaning": "淡然是看透后的平和。"},
    {"word": "柔软", "description": "柔软的心最有力量", "meaning": "柔软不是软弱，而是包容。"},
    {"word": "丰盈", "description": "内心丰盈者，独行也如众", "meaning": "丰盈是精神世界的富足。"},
]

# ==================== AI辅助函数（适配硅基流动）====================

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
    """获取每日一句 - 来自一言API"""
    print("正在获取每日一句...")
    try:
        url = "https://v1.hitokoto.cn/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "content": data["hitokoto"],
                "from": data.get("from", "未知")
            }
            print(f"✓ 获取成功：{result['content'][:30]}...")
            return enrich_with_ai("sentence", result)
    except Exception as e:
        print(f"× 异常：{e}")

    print("使用备选句子")
    result = random.choice(FALLBACK_SENTENCES).copy()
    return enrich_with_ai("sentence", result)

# ==================== 每日一曲（AI生成模式）====================

def fetch_song():
    """获取每日一曲 - 由 AI 直接生成推荐歌曲"""
    print("正在获取每日一曲（AI生成模式）...")

    if not ENABLE_AI:
        print("AI未启用，使用备选歌曲")
        result = random.choice(FALLBACK_SONGS).copy()
        return enrich_with_ai("song", result)

    # 构建让 AI 生成歌曲的提示词（加入随机元素）
    styles = ["流行", "摇滚", "民谣", "电子", "爵士", "古典", "说唱", "R&B", "乡村", "世界音乐"]
    eras = ["80年代", "90年代", "00年代", "10年代", "当代", "经典老歌"]
    regions = ["华语", "欧美", "日韩", "拉丁", "全球小众"]
    prompt = f"""
    请你扮演一位专业的音乐推荐官，为我推荐一首 {random.choice(regions)} {random.choice(eras)} 的 {random.choice(styles)} 歌曲。
    请严格按照以下 JSON 格式输出，不要包含任何其他文字：

    {{
        "name": "推荐的歌曲名称",
        "artist": "歌手或乐队名",
        "album": "所属专辑",
        "comment": {{
            "content": "用一句简短、有吸引力的话作为推荐理由，类似网易云热评的风格"
        }}
    }}

    请确保推荐真实存在、有代表性的歌曲。
    """

    ai_response_text = call_ai(prompt, max_tokens=300)

    # 解析 AI 返回的 JSON
    try:
        # 尝试从AI回复中提取JSON（如果AI回复中包含了其他文字）
        # 这里简单起见，假设AI严格按照指令返回了纯JSON
        song_data = json.loads(ai_response_text)
        name = song_data.get('name', '').strip()
        artist = song_data.get('artist', '').strip()
        album = song_data.get('album', '').strip()
        comment_content = song_data.get('comment', {}).get('content', '').strip()

        if name and artist:
            print(f"✓ AI生成成功：{name} - {artist}")

            # 使用可靠的在线图片服务作为封面（每次刷新都会变化）
            # 为了更稳定，也可使用固定的占位图服务，这里用 picsum 基于歌曲名生成随机图片
            cover_url = f"https://picsum.photos/seed/{name.replace(' ', '')}/300/300"

            result = {
                "name": name,
                "artist": artist,
                "album": album if album else "未知专辑",
                "cover": cover_url,
                "comment": {
                    "content": comment_content if comment_content else f"今日AI推荐：{name}",
                    "user": "AI推荐官"
                },
                "source": "AI生成"
            }
            return enrich_with_ai("song", result)
        else:
            print("× AI返回的歌曲信息不完整，使用备选歌曲")

    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f"× 解析AI响应失败: {e}")
        print(f"AI原始响应: {ai_response_text}")

    # 任何失败情况，降级使用备选
    print("使用备选歌曲")
    result = random.choice(FALLBACK_SONGS).copy()
    return enrich_with_ai("song", result)

# ==================== 每日一文 ====================

def fetch_article():
    """获取每日一文：优先古诗文网，其次维基百科，最后备选"""
    print("正在获取每日一文...")

    # 1. 尝试古诗文网随机诗词
    try:
        url = "https://www.gushiwen.cn/random.aspx"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_tag = soup.find('h1')
            if not title_tag:
                title_tag = soup.find('b')
            title = title_tag.text.strip() if title_tag else "无题"

            content_div = soup.find('div', class_='contson')
            content = content_div.text.strip() if content_div else ""

            source_tag = soup.find('p', class_='source')
            author = source_tag.text.strip() if source_tag else "佚名"

            if content:
                print(f"✓ 从古诗文网获取：{title}")
                result = {
                    "title": title,
                    "description": content[:200] + "..." if len(content) > 200 else content,
                    "content": content,
                    "author": author,
                    "source": "古诗文网"
                }
                return enrich_with_ai("article", result)
    except Exception as e:
        print(f"古诗文网获取失败：{e}")

    # 2. 尝试维基百科每日特色条目
    try:
        today = datetime.now()
        url = f"https://zh.wikipedia.org/api/rest_v1/feed/featured/{today.year}/{today.month:02d}/{today.day:02d}"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; DailySiteBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            tfa = data.get('tfa', {})
            if tfa:
                title = tfa.get('title', '')
                extract = tfa.get('extract', '')
                page_url = tfa.get('content_urls', {}).get('desktop', {}).get('page', '')
                print(f"✓ 从维基百科获取：{title}")
                result = {
                    "title": title,
                    "description": extract,
                    "url": page_url,
                    "author": "维基百科",
                    "source": "维基百科"
                }
                return enrich_with_ai("article", result)
    except Exception as e:
        print(f"维基百科失败：{e}")

    # 3. 使用备选文章
    print("所有来源均失败，使用备选文章")
    result = random.choice(FALLBACK_ARTICLES).copy()
    return enrich_with_ai("article", result)

# ==================== 每日一词（多来源抓取） ====================

def fetch_word_from_baidu():
    """从百度热搜抓取"""
    url = "https://top.baidu.com/board?tab=realtime"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200:
        raise Exception(f"百度请求失败: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first = soup.select_one('.c-single-text-ellipsis')
    if not first:
        raise Exception("百度解析失败")
    word = first.text.strip()
    hot_span = soup.select_one('.hot-index_1E1kp')
    hot_value = hot_span.text.strip() if hot_span else ""
    return {"word": word, "description": f"百度热搜 · {hot_value}"}

def fetch_word_from_zhihu():
    """从知乎热榜抓取"""
    url = "https://www.zhihu.com/billboard"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200:
        raise Exception(f"知乎请求失败: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    topic = soup.select_one('.HotList-itemTitle')
    if not topic:
        raise Exception("知乎解析失败")
    word = topic.text.strip()
    hot = soup.select_one('.HotList-itemHot')
    hot_value = hot.text.strip() if hot else "未知热度"
    return {"word": word, "description": f"知乎热榜 · {hot_value}"}

def fetch_word_from_douban():
    """从豆瓣电影热门抓取"""
    url = "https://movie.douban.com/chart"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200:
        raise Exception(f"豆瓣请求失败: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_movie = soup.select_one('.pl2 a')
    if not first_movie:
        raise Exception("豆瓣解析失败")
    word = first_movie.text.strip().replace(' ', '').replace('\n', '')
    return {"word": word, "description": "豆瓣热门电影"}

def fetch_word_from_sspai():
    """从少数派热门文章抓取"""
    url = "https://sspai.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200:
        raise Exception(f"少数派请求失败: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_article = soup.select_one('.itemTitle a')
    if not first_article:
        first_article = soup.select_one('h2 a')
    if not first_article:
        raise Exception("少数派解析失败")
    word = first_article.text.strip()
    return {"word": word, "description": "少数派热门文章"}

def fetch_word_from_weibo():
    """从微博热搜抓取（移动端）"""
    url = "https://s.weibo.com/top/summary"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200:
        raise Exception(f"微博请求失败: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    first_tr = soup.select_one('tbody tr:first-child')
    if not first_tr:
        raise Exception("微博解析失败")
    a_tag = first_tr.select_one('.td-02 a')
    if not a_tag:
        raise Exception("微博解析失败")
    word = a_tag.text.strip()
    hot_span = first_tr.select_one('.td-02 span')
    hot_value = hot_span.text.strip() if hot_span else ""
    return {"word": word, "description": f"微博热搜 · {hot_value}"}

def fetch_word_from_today_song():
    """从今日歌曲热评中提取一个词（需要全局缓存 _cached_song）"""
    global _cached_song
    if _cached_song and _cached_song.get('comment'):
        comment = _cached_song['comment'].get('content', '')
        if comment:
            # 简单取第一个词或前五个字
            word = comment.split()[0][:5] if comment else None
            if word:
                return {"word": word, "description": "来自今日歌曲热评"}
    return None

def fetch_word():
    """获取每日一词：依次尝试多个来源，最后备选"""
    print("正在获取每日一词...")

    sources = [
        fetch_word_from_baidu,
        fetch_word_from_zhihu,
        fetch_word_from_douban,
        fetch_word_from_sspai,
        fetch_word_from_weibo,
        fetch_word_from_today_song,
    ]

    random.shuffle(sources)

    for fetch_func in sources:
        try:
            name = fetch_func.__name__ if hasattr(fetch_func, '__name__') else "今日歌曲热评"
            print(f"尝试从 {name} 获取...")
            result = fetch_func()
            if result and result.get('word'):
                print(f"✓ 成功：{result['word']}")
                return enrich_with_ai("word", result)
        except Exception as e:
            print(f"× 失败：{e}")
            continue

    print("所有来源均失败，使用本地备选词")
    result = random.choice(FALLBACK_WORDS).copy()
    return enrich_with_ai("word", result)

# ==================== 主函数 ====================

def main():
    global _cached_song
    print(f"=== 每日数据爬虫（AI生成每日一曲）开始运行 [{datetime.now().isoformat()}] ===")
    print(f"AI 状态: {'启用' if ENABLE_AI else '未启用'}")

    # 先获取每日一曲，以便每日一词可以引用其热评
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
