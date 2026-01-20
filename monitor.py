import yfinance as yf
import requests
import os

# 从系统环境变量中读取敏感信息（为了安全，不直接写在代码里）
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def monitor_soxl():
    # 1. 获取 SOXL 数据
    ticker = "SOXL"
    stock = yf.Ticker(ticker)
    df = stock.history(period="1d")
    
    if df.empty:
        return
    
    # 2. 计算成交额 (收盘价 * 成交量)
    close_price = df['Close'].iloc[0]
    volume = df['Volume'].iloc[0]
    amount = close_price * volume
    threshold = 1e9  # 10亿
    
    # 3. 逻辑判断与消息构造
    status = "✅ 正常" if amount >= threshold else "⚠️ 警报"
    message = (
        f"【SOXL 成交额监控】\n"
        f"当前状态：{status}\n"
        f"今日收盘价：${close_price:.2f}\n"
        f"今日成交额：${amount/1e8:.2f} 亿\n"
        f"监控阈值：$10.00 亿"
    )
    
    # 4. 如果触发警报或每日例行汇报，则发送消息
    # 你可以设置为只要运行就发，或者只有跌破才发
    send_telegram_msg(message)

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    monitor_soxl()
