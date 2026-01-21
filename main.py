import cloudscraper
import re
import os
import json

def get_qqq_iv_barchart():
    # 使用 Barchart 的 QQQ 概览页
    url = "https://www.barchart.com/etfs-funds/quotes/QQQ/technical-analysis"
    
    # 模拟真实浏览器
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        # 1. 访问主页获取 Cookie
        scraper.get("https://www.barchart.com/")
        
        # 2. 访问技术分析页
        resp = scraper.get(url, timeout=30)
        
        if resp.status_code != 200:
            return f"访问失败: {resp.status_code}"

        # Barchart 的数据存储在 window.siteData 这种脚本块中
        # 我们用正则提取隐含波动率相关的数据
        # 匹配示例: "ivPercentile":25.4
        match = re.search(r'"ivPercentile":\s*([\d\.]+)', resp.text)
        
        if match:
            iv_val = match.group(1)
            return f"{iv_val}%"
        
        # 备选匹配方式
        match_alt = re.search(r'IV Percentile.*?(\d+\.\d+)%', resp.text, re.IGNORECASE | re.DOTALL)
        if match_alt:
            return f"{match_alt.group(1)}%"

        return "定位失败: 网站结构可能已更新"

    except Exception as e:
        return f"异常: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": message,
        "parse_mode": "Markdown"
    }
    cloudscraper.create_scraper().post(url, data=payload)

if __name__ == "__main__":
    iv_val = get_qqq_iv_barchart()
    
    from datetime import datetime
    # 转换为北京时间（如果你在 GitHub Actions 运行，默认是 UTC）
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    msg = (
        f"📊 *QQQ 波动率监控 (Barchart)*\n"
        f"━━━━━━━━━━━━━━\n"
        f"⏰ 时间: `{now}`\n"
        f"💎 **IV Percentile**: `{iv_val}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔗 [Barchart 详情](https://www.barchart.com/etfs-funds/quotes/QQQ/technical-analysis)"
    )
    send_telegram(msg)
