import feedparser
import requests
import os

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

def fetch_headlines():
    message = "📅 *今日全球主流媒体头条* \n"
    message += "--------------------------------\n"
    
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                top_story = feed.entries[0]
                title = top_story.title
                link = top_story.link
                message += f"🔹 *{name}*\n[{title}]({link})\n\n"
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    
    return message

def send_to_telegram(text):
    # 从 GitHub Secrets 中读取变量
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Success!")
    else:
        print(f"Failed: {response.text}")

if __name__ == "__main__":
    content = fetch_headlines()
    send_to_telegram(content)
