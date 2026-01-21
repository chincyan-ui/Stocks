import requests
import re
import os

def get_qqq_iv():
    # 尝试抓取 Barchart 或 AlphaQuery，这些网站对爬虫相对友好
    # 这里我们仍以 Market Chameleon 为例，但大幅增强伪装
    url = "https://marketchameleon.com/Overview/QQQ/IV/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,.*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/'
    }

    try:
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            return f"HTTP 错误: {resp.status_code}"

        # 打印网页前 500 个字符到日志，方便我们分析被拦截时的样子
        print(f"DEBUG - 网页片段: {resp.text[:500]}")

        # 使用更宽松的正则匹配 IV Percentile
        # 匹配文本如: "IV Percentile is 25%" 或 "25% IV Rank"
        match = re.search(r'(\d+\.?\d*)\s*%', resp.text)
        
        if match:
            return f"{match.group(1)}%"
        
        return "无法在页面找到百分比数值"

    except Exception as e:
        return f"脚本运行异常: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    if not token or not chat_id:
        print("错误: 环境变量 TG_TOKEN 或 TG_CHAT_ID 未设置")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    
    r = requests.post(url, data=payload)
    print(f"Telegram 发送状态: {r.status_code}")

if __name__ == "__main__":
    iv_val = get_qqq_iv()
    send_telegram(f"📊 QQQ IV 监测\n最新数值: {iv_val}")
