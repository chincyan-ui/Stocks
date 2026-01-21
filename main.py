import requests
import re
import os

def get_qqq_iv_percentile():
    # 目标：Market Chameleon 的 QQQ IV 页面
    url = "https://marketchameleon.com/Overview/QQQ/IV/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers)
    # 查找 IV Percentile 相关数值（注：实际爬取可能需要根据页面结构调整选择器）
    # 这里以简单的正则匹配作为示例
    iv_match = re.search(r'IV Percentile.*?(\d+\.?\d*)%', response.text)
    
    if iv_match:
        return iv_match.group(1)
    return "抓取失败"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    requests.post(url, data=payload)

if __name__ == "__main__":
    iv_val = get_qqq_iv_percentile()
    msg = f"📅 今日 QQQ 最新 IV Percentile: {iv_val}%"
    send_telegram(msg)
