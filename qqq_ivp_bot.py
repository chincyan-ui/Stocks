import yfinance as yf
import pandas as pd
import requests
import os

def get_ivp_and_send():
    # 1. 获取数据
    # VXN 是纳斯达克100的波动率指数，是计算 QQQ IVP 最权威的参考
    ticker = "^VXN" 
    data = yf.download(ticker, period="1y")
    
    if data.empty:
        print("数据获取失败")
        return

    # 2. 计算 IVP
    current_iv = data['Close'].iloc[-1].item()
    min_iv = data['Close'].min().item()
    max_iv = data['Close'].max().item()
    
    # IVP 公式: (当前值 - 最小值) / (最大值 - 最小值) * 100
    ivp = (current_iv - min_iv) / (max_iv - min_iv) * 100

    # 3. 构造消息内容
    message = (
        f"📊 **QQQ 波动率日报 (基于VXN)**\n\n"
        f"🔹 当前 IV (VXN): `{current_iv:.2f}`\n"
        f"🔹 1年最低: `{min_iv:.2f}`\n"
        f"🔹 1年最高: `{max_iv:.2f}`\n\n"
        f"🔥 **当前 IVP: {ivp:.2f}%**\n"
        f"*(IVP 越高，期权卖方越占优)*"
    )

    # 4. 发送到 Telegram
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("消息发送成功")
    else:
        print(f"发送失败: {response.text}")

if __name__ == "__main__":
    get_ivp_and_send()
