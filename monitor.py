import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """从 FRED 获取高收益债利差"""
    start = datetime.datetime.now() - datetime.timedelta(days=7)
    end = datetime.datetime.now()
    # BAMLH0A0HYM2: ICE BofA US High Yield Index Option-Adjusted Spread
    df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
    latest_oas = df.iloc[-1][0]
    prev_oas = df.iloc[-2][0]
    return latest_oas, latest_oas - prev_oas

def monitor_all():
    # 1. 获取宏观 OAS 风险指标
    try:
        oas, oas_change = get_oas_data()
        oas_status = "🟢 信用风险低" if oas < 5.0 else ("🟡 风险抬升" if oas < 6.5 else "🔴 衰退预警")
    except:
        oas, oas_change, oas_status = 0, 0, "数据获取失败"

    # 2. 获取个股/ETF 动能 (SOXL)
    symbol = "SOXL"
    stock = yf.Ticker(symbol)
    df_stock = stock.history(period="300d")
    
    latest_close = df_stock['Close'].iloc[-1]
    latest_amt = latest_close * df_stock['Volume'].iloc[-1]
    
    # 计算 250 日连续成交额达标情况
    threshold = 1e9
    df_stock['Amt'] = df_stock['Close'] * df_stock['Volume']
    count = 0
    for amt in reversed(df_stock['Amt']):
        if amt >= threshold: count += 1
        else: break

    # 3. 整合消息内容
    msg = (
        f"🏛️ 【宏观信用风险】\n"
        f"HY OAS 利差: {oas:.2f}% ({oas_change:+.2f}%)\n"
        f"宏观状态: {oas_status}\n\n"
        f"🚀 【{symbol} 动能监控】\n"
        f"今日收盘: ${latest_close:.2f}\n"
        f"今日成交额: ${latest_amt/1e8:.2f} 亿\n"
        f"250日连续达标: {count} 天\n\n"
        f"💡 决策辅助：\n"
        f"{'✅ 双指标看多' if count >= 250 and oas < 5.0 else '⚠️ 建议观望或减仓'}"
    )
    
    send_telegram_msg(msg)

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

if __name__ == "__main__":
    monitor_all()
