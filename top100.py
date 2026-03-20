import yfinance as yf
import requests
import os

# 从 GitHub Secrets 读取配置
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

# 待监控的股票列表（你可以根据需要添加更多，如：AAPL, TSLA, NVDA 等）
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "TSM", "UNH", "V", "JPM", "NFLX", "AMD"]

def get_stock_data():
    results = []
    print("正在获取行情数据...")
    
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            # 获取 5 年历史数据
            hist = ticker.history(period="5y")
            if hist.empty:
                continue
                
            current_price = hist['Close'].iloc[-1]
            # 计算 5 年内的历史最高价 (ATH)
            ath = hist['High'].max()
            # 计算回撤幅度
            drawdown = ((current_price - ath) / ath) * 100
            
            results.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "ath": round(ath, 2),
                "drawdown": round(drawdown, 2)
            })
        except Exception as e:
            print(f"获取 {symbol} 出错: {e}")
            
    # 按回撤幅度排序（跌得最深的排在前面）
    results.sort(key=lambda x: x['drawdown'])
    return results[:10]

def send_tg_message(data):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("未配置 Telegram Token 或 Chat ID")
        return

    message = "📊 *每日股票回撤榜 (Top 10)*\n\n"
    for i, s in enumerate(data, 1):
        message += f"{i}. *{s['symbol']}*\n"
        message += f"   现价: ${s['price']} | ATH: ${s['ath']}\n"
        message += f"   *回撤: {s['drawdown']}%*\n\n"

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("消息发送成功！")
    else:
        print(f"发送失败: {response.text}")

if __name__ == "__main__":
    top_stocks = get_stock_data()
    if top_stocks:
        send_tg_message(top_stocks)
