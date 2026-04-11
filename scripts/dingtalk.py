#!/usr/bin/env python3
import os
import sys
import requests
import time
import hmac
import hashlib
import base64

def send_dingtalk(message_type):
    webhook = os.environ.get('DINGTALK_WEBHOOK')
    secret = os.environ.get('DINGTALK_SECRET')
    if not webhook or not secret:
        print("钉钉配置缺失，跳过通知")
        return

    timestamp = str(round(time.time() * 1000))
    sign = base64.b64encode(
        hmac.new(secret.encode('utf-8'),
                 (timestamp + '\n' + secret).encode('utf-8'),
                 hashlib.sha256).digest()
    ).decode('utf-8')

    if message_type == 'success':
        summary = os.environ.get('SUMMARY', '')
        article_title = os.environ.get('ARTICLE_TITLE', '')
        question = os.environ.get('QUESTION', '')
        date = os.environ.get('DATE', '')
        text = f"""
## 📮 拾光驿站 · 每日报告

**日期**：{date}

## 📝 每日总结
> {summary}

---

## 📊 今日统计
- **📖 文章**：{article_title}
- **🎵 歌单**：今日推荐6首歌曲
- **📚 小说**：今日更新3篇小说
- **💬 思考题**：{question}

---

> ✨ 拾光驿站，美好的一天从诗意与思考开始。
> [点击查看详情](https://luqingji.github.io)
"""
        title = "📮 拾光驿站 · 每日报告"
    else:
        text = f"## ❌ 拾光驿站 · 每日更新失败\n\n爬虫运行出现问题，请检查 [GitHub Actions 日志](https://github.com/luqingji/luqingji.github.io/actions)。"
        title = "❌ 拾光驿站 · 更新失败"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text
        },
        "at": {
            "isAtAll": False
        }
    }
    url = f"{webhook}?timestamp={timestamp}&sign={sign}"
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print(resp.status_code, resp.text)
    except Exception as e:
        print(f"发送钉钉消息失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_dingtalk(sys.argv[1])
    else:
        send_dingtalk("success")