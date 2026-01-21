import cloudscraper
from bs4 import BeautifulSoup
import os
import re

def get_qqq_data():
    # 方案 A: AlphaQuery (结构相对清晰)
    url = "https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile"
    scraper = cloudscraper.create_scraper(browser='chrome')
    
    try:
        resp = scraper.get(url, timeout=30)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 定位具体标签：查找包含 "Indicator" 含义的类名
            # AlphaQuery 的 IV Percentile 数值通常在 indicator-figure-large 类中
            target = soup.find(class_='indicator-figure-large')
            if target:
                val = target.text.strip()
                # 转换 0.2532 为 25.32%
                try:
                    num = float(val)
                    if num < 1:
                        return f"{num*100:.2f}%"
                    return f"{num:.2f}%"
                except:
                    return val

        # 方案 B: 如果 A 失败，尝试从文本中精准截取
        # 寻找 "30-Day IV Percentile is X.XXXX" 这种模式
        match = re.search(r'30-Day IV Percentile is\s*(\d+\.?\d*)', resp.text)
        if match:
            return f"{float(match.group(1))*100:.2f}%"

        return "数据定位失败"
    except Exception as e:
        return f"错误: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    # 使用 Markdown 让消息更美观
    payload = {
        "chat_id": chat_id.strip(),
        "text": message,
        "parse_mode": "Markdown"
    }
    cloudscraper.create_scraper().post(url, data=payload)

if __name__ == "__main__":
    iv_percentile = get_qqq_data()
    
    # 加上时间戳，防止 GitHub Actions 缓存结果
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    msg = (
        f"📊 *QQQ 指数监控*\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 时间: `{now}`\n"
        f"🔥 **IV Percentile**: `{iv_percentile}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔗 [查看源网页](https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile)"
    )
    send_telegram(msg)
