import feedparser
import requests
import os
import time
from googletrans import Translator

# 初始化翻译器
translator = Translator()

# 10家具有公信力的媒体 RSS 列表
RSS_FEEDS = {
    "路透社 (Reuters)": "https://www.reutersagency.com/feed/",
    "美联社 (AP News)": "https://rsshub.app/apnews/topics/ap-top-news",
    "BBC News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "纽约时报 (NY Times)": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "华尔街日报 (WSJ)": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "卫报 (The Guardian)": "https://www.theguardian.com/world/rss",
    "彭博社 (Bloomberg)": "https://rsshub.app/bloomberg",
    "半岛电视台 (Al Jazeera)": "https://www.aljazeera.com/xml/rss/all.xml",
    "日经亚洲 (Nikkei Asia)": "https://rsshub.app/nikkei/asia",
    "经济学人 (The Economist)": "https://www.economist.com/world/rss.xml"
}

def translate_text(text):
    try:
        # 尝试翻译为中文
        translated = translator.translate(text, dest='zh-cn')
        return translated.text
    except Exception as e:
        print(f"翻译出错: {e}")
        return "翻译失败"

def fetch_headlines():
    message = "📅 *今日全球主流媒体头条 (含中文对照)* \n"
    message += "--------------------------------\n"
    
    count = 0
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                top_story = feed.entries[0]
                en_title = top_story.title
                link = top_story.link
                
                # 获取翻译
                zh_title = translate_text(en_title)
                
                message += f"🔹 *{name}*\n"
                message += f"原文: {en_title}\n"
                message += f"中文: {zh_title}\n"
                message += f"[查看原文]({link})\n\n"
                
                count += 1
                # 翻译请求过快容易被封IP，稍微等待
                time.sleep(1) 
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    
    print(f"成功抓取 {count} 条新闻")
    return message

def send_to_telegram(text):
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        # 核心设置：禁止网页预览，这样就不会出现图片，只显示纯文字
        "disable_web_page_preview": True 
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("推送成功!")
    else:
        # 如果信息太长（超过4096字符），Telegram会报错，这里做简单处理
        if "message is too long" in response.text:
            print("信息太长，尝试分段发送...")
            # 简单截断处理或再次拆分发送
        print(f"推送失败: {response.text}")

if __name__ == "__main__":
    content = fetch_headlines()
    send_to_telegram(content)
