import yfinance as yf
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def monitor_stocks():
    # 你可以增加更多感兴趣的半导体股票，如 ["SOXL", "NVDA", "AMD"]
    tickers = ["SOXL"] 
    threshold = 1e9  # 10亿美元
    
    for symbol in tickers:
        stock = yf.Ticker(symbol)
        # 获取过去 255 天的数据，计算连续达标天数
        df = stock.history(period="300d") 
        
        if df.empty: continue
        
        # 计算每日成交额
        df['Amount'] = df['Close'] * df['Volume']
        
        # 获取最新一天数据
        latest_amount = df['Amount'].iloc[-1]
        latest_close = df['Close'].iloc[-1]
        
        # 计算连续达标天数 (从今天起往回数)
        count = 0
        for amt in reversed(df['Amount']):
            if amt >= threshold:
                count += 1
            else:
                break
        
        # 构造中文提醒消息
        status_icon = "🔥" if count >= 250 else "👀"
        msg = (
            f"{status_icon} 【{symbol} 量能监控汇报】\n"
            f"----------------------------\n"
            f"今日收盘价: ${latest_close:.2f}\n"
            f"今日成交额: ${latest_amount/1e8:.2f} 亿\n"
            f"连续达标天数: {count} 天\n"
            f"----------------------------\n"
            f"{'✅ 已达成 250 日连续目标！' if count >= 250 else f'⚠️ 距离目标还差 {250-count} 天'}"
        )
        
        send_telegram_msg(msg)

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

if __name__ == "__main__":
    monitor_stocks()
