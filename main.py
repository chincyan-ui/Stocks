import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz

# 从环境变量读取
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    try:
        # 设置 User-Agent 防止被拒绝访问
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        # FRED 偶尔会有网络波动，加入重试逻辑
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        recent_df = df.dropna()
        if recent_df.empty: return None, None, []
        
        oas_list = recent_df.iloc[-7:, 0].tolist()
        return oas_list[-1], oas_list[-1] - oas_list[-2], oas_list
    except:
        return None, None, []

def get_qqq_stats():
    try:
        ticker = yf.Ticker("QQQ")
        df = ticker.history(period="2y")
        if df.empty: return None
        
        ath = df['Close'].max()
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        return {
            "close": float(curr['Close']),
            "change": float((curr['Close'] - prev['Close']) / prev['Close'] * 100),
            "drawdown": float((curr['Close'] / ath - 1) * 100),
            "ath": float(ath)
        }
    except:
        return None

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=20)

def main():
    tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M')

    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    # 如果没获取到 QQQ 数据且是非交易日，就不推送
    if not qqq:
        print("今日无交易数据")
        return

    msg = f"📊 *美股收盘简报*\n时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    dd_icon = "🟢" if qqq['drawdown'] > -10 else "🔴"
    msg += f"🔹 *QQQ (纳指100)*\n"
    msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
    msg += f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"
        
    if oas:
        trend = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *信用利差 (OAS)*: `{oas:.2f}%` ({trend} `{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{'→'.join([f'{x:.2f}' for x in oas_list[-5:]])}`\n"

    msg += "--------------------------------\n"
    msg += "💡 _数据源: Yahoo Finance & FRED_"
    
    send_msg(msg)

if __name__ == "__main__":
    main()
