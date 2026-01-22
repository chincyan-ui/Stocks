import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

# 配置环境
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED)"""
    try:
        start = datetime.datetime.now() - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, datetime.datetime.now())
        if df.empty: return None, None, []
        
        col = df.columns[0]
        recent_df = df.dropna().tail(7)
        oas_list = recent_df[col].tolist()
        
        if len(oas_list) < 2: return None, None, []
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS数据抓取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取QQQ当日行情"""
    try:
        df = yf.Ticker("QQQ").history(period="5d")
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        curr, prev = df.iloc[-1], df.iloc[-2]
        return {
            "high": curr['High'], "low": curr['Low'], 
            "close": curr['Close'], "change": (curr['Close'] - prev['Close']) / prev['Close'] * 100
        }
    except:
        return None

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print("未配置 Telegram Token 或 ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"发送消息失败: {e}")

def main():
    # 1. 获取数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    # 2. 构造报告内容
    msg = f"📊 *美股宏观数据复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"高/低: `{qqq['high']:.2f}` / `{qqq['low']:.2f}`\n\n"
        
    if oas:
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    msg += f"--------------------------------\n"
    
    # 策略建议
    if oas:
        suggestion = "🚀 *策略：积极持有*" if oas < 5.0 else "⚠️ *策略：风险防御*"
        msg += f"💡 {suggestion}"

    # 3. 发送消息
    send_msg(msg)

if __name__ == "__main__":
    main()
