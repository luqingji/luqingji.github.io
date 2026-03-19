def fetch_novel():
    """获取每日一小说 - 由 AI 根据随机风格生成短篇小说（1500-2500字）"""
    print("正在获取每日一小说...")
    styles = [
        {"name": "温情治愈", "desc": "温暖人心的小故事，结局美好，充满希望。"},
        {"name": "悬疑推理", "desc": "带有悬念，引人思考，结局可能出人意料。"},
        {"name": "科幻未来", "desc": "设定在未来或科技背景下，探讨人性与技术。"},
        {"name": "幽默搞笑", "desc": "轻松诙谐，让人会心一笑或捧腹。"},
        {"name": "人生哲理", "desc": "短小精悍，蕴含深刻道理，引人深思。"},
        {"name": "都市情感", "desc": "现代城市中的情感故事，关于爱情、友情或亲情。"},
        {"name": "奇幻冒险", "desc": "奇幻世界或冒险旅程，充满想象力。"},
        {"name": "历史瞬间", "desc": "以历史事件或人物为背景，展现时代切片。"},
        {"name": "微恐怖", "desc": "轻微恐怖氛围，但不过分，结局留有想象空间。"},
        {"name": "动物视角", "desc": "以动物为主角，通过它们的眼睛看世界。"},
        {"name": "反转结局", "desc": "结尾出人意料，颠覆读者预期。"},
        {"name": "文艺唯美", "desc": "注重意境和文字美感，情节淡化，情绪为主。"},
    ]
    if not ENABLE_AI:
        return random.choice(FALLBACK_NOVELS).copy()
    chosen = random.choice(styles)
    print(f"风格：{chosen['name']}")
    prompt = f"""
    请创作一篇短篇小说，要求：
    - 风格：{chosen['name']}（{chosen['desc']}）
    - 标题简洁有吸引力
    - 正文在1500-2500字之间，情节完整，有起承转合
    - 按以下JSON格式输出：
    {{
        "title": "小说标题",
        "content": "小说正文"
    }}
    """
    ai_resp = call_ai(prompt, max_tokens=5000, temperature=0.8)  # 增加 token 上限
    if ai_resp:
        try:
            data = json.loads(ai_resp)
            title = data.get('title', '').strip()
            content = data.get('content', '').strip()
            if title and content:
                print(f"✓ 小说生成成功：{title}")
                return {"title": title, "content": content}
        except Exception as e:
            print(f"× 解析失败: {e}")
    return random.choice(FALLBACK_NOVELS).copy()
