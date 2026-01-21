import requests
from bs4 import BeautifulSoup
import os
import sys

def get_qqq_iv_alphaquery():
    # AlphaQuery QQQ 30天 IV Percentile 页面
    url = "https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"正在访问: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return f"Error: 网页访问失败，状态码 {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # AlphaQuery 的数值通常在 class 为 indicator-figure-large 的 div 中
        indicator = soup.find('div', class_='indicator-figure-large')
        
        if indicator:
            iv_value = indicator.text.strip()
            # 转换成百分比格式 (如果是 0.2532 -> 25.32%)
            try:
                percent_val = float(iv_value) * 100
                return f"{percent_val:.2f}%"
            except ValueError:
                return iv_value
        else:
            return "Error: 未能找到 IV 数值标签"

    except Exception as e:
        return f"脚本运行异常: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    if not token or not chat_id:
        print("错误: 环境变量 TG_TOKEN 或 TG_CHAT_ID 未设置，请检查 GitHub Secrets")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            print("Telegram 消息发送成功！")
        else:
            print(f"Telegram 发送失败: {r.text}")
    except Exception as e:
        print(f"发送过程发生异常: {e}")

if __name__ == "__main__":
    iv_val = get_qqq_iv_alphaquery()
    
    # 构造推送内容
    content = f"🔔 *QQQ IV Percentile 提醒*\n\n"
    content += f"📈 **最新数值**: `{iv_val}`\n"
    content += f"🔗 [点击查看详情](https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile)"
    
    send_telegram(content)
