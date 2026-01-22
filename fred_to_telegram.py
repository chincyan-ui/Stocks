import os
import requests
import pandas as pd
from datetime import datetime

# 配置环境变量
FRED_API_KEY = os.getenv('FRED_API_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
SERIES_ID = 'BAMLH0A0HYM2'

def get_fred_data():
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={SERIES_ID}&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit=8"
    response = requests.get(url).json()
    df = pd.DataFrame(response['observations'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    return df.dropna()

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def main():
    df = get_fred_data()
    
    # 核心指标
    latest_val = df.iloc[0]['value']
    latest_date = df.iloc[0]['date'].strftime('%Y-%m-%d')
    
    # 7日前的数据 (通常取第6或7个有效交易日)
    prev_val = df.iloc[6]['value'] 
    change = latest_val - prev_val
    
    # 符号美化
    trend_emoji = "📈" if change > 0 else "📉"
    arrow = "⬆️" if change > 0 else "⬇️"

    # 构建 HTML 消息
    msg = (
        f"<b>📊 美银美林高收益债利差 (OAS)</b>\n\n"
        f"📅 <b>最新日期</b>: {latest_date}\n"
        f"💎 <b>最新利差</b>: <code>{latest_val}%</code>\n"
        f"----------------------------------\n"
        f"🔄 <b>7日趋势变化</b>: {trend_emoji} {change:+.2f}%\n"
        f"前值参考: {prev_val}% ({df.iloc[6]['date'].strftime('%m-%d')})\n\n"
        f"💡 <i>利差走高通常意味着市场避险情绪升温。</i>"
    )
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    main()
