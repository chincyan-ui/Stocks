import cloudscraper
from bs4 import BeautifulSoup
import os
import re

def get_qqq_iv_barchart():
    # 使用 Barchart，它是目前最权威的 IV 数据源之一
    url = "https://www.barchart.com/etfs-funds/quotes/QQQ/overview"
    
    # 创建 scraper 实例，自动处理 Cloudflare 503 挑战
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        print(f"正在通过反爬引擎访问: {url}")
        response = scraper.get(url, timeout=30)
        
        if response.status_code != 200:
            return f"访问失败，状态码: {response.status_code} (网站可能升级了防护)"

        # 在页面搜索 IV Percentile
        # Barchart 的页面比较复杂，我们直接用正则在全文本中抓取关键数字
        # 匹配 "IV Percentile" 后面的百分比
        text = response.text
        match = re.search(r'IV Percentile.*?(\d+\.?\d*)%', text, re.DOTALL)
        
        if match:
            return f"{match.group(1)}%"
        
        # 备选匹配：匹配 "Implied Volatility" 
        iv_rank_match = re.search(r'IV Rank.*?(\d+\.?\d*)%', text, re.DOTALL)
        if iv_rank_match:
            return f"{iv_rank_match.group(1)}% (IV Rank)"
            
        return "未能识别 IV 数据，请检查页面结构"

    except Exception as e:
        return f"爬虫运行异常: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("错误: 环境变量缺失")
        return

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": message,
        "parse_mode": "Markdown"
    }
    
    r = cloudscraper.create_scraper().post(url, data=payload)
    print(f"TG 发送状态: {r.status_code}")

if __name__ == "__main__":
    val = get_qqq_iv_barchart()
    send_telegram(f"📊 *QQQ IV 实时监控*\n\n**当前数值**: `{val}`")
