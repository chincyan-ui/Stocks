import os
import requests

# --- 配置 ---
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

# 行情数据基础 URL
DATA_URL = "https://data.alpaca.markets/v2/stocks/snapshots"

def send_tg(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TG_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'})

def main():
    # 1. 定义想要监控的热门股票列表（Alpaca 免费版需手动指定列表或循环获取）
    # 提示：你可以放 20-50 个主要科技股
    symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC"]
    
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": SECRET_KEY
    }

    params = {
        "symbols": ",".join(symbols)
    }

    try:
        response = requests.get(DATA_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        stock_stats = []
        for symbol, info in data.items():
            # Alpaca 免费数据来自 IEX 交易所
            daily_bar = info.get('dailyBar', {})
            latest_trade = info.get('latestTrade', {})
            
            price = latest_trade.get('p', 0)  # 最新成交价
            volume = daily_bar.get('v', 0)    # 今日成交量
            amount = price * volume           # 估算当日成交金额
            
            # 计算涨跌（相比昨日收盘）
            prev_close = info.get('prevDailyBar', {}).get('c', 0)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            stock_stats.append({
                'symbol': symbol,
                'price': price,
                'amount': amount,
                'change_pct': change_pct
            })

        # 2. 按成交金额排序并取前 3
        top_3 = sorted(stock_stats, key=lambda x: x['amount'], reverse=True)[:3]

        msg = ["🏔️ **Alpaca 美股成交额榜 (Top 3)**"]
        for i, s in enumerate(top_3, 1):
            msg.append(f"{i}. **{s['symbol']}**")
            msg.append(f"   💰 价格: ${s['price']:.2f} ({s['change_pct']:+.2f}%)")
            msg.append(f"   📊 估算成交额: ${s['amount']/1e8:.2f} 亿")

        send_tg("\n".join(msg))
        print("Alpaca data pushed successfully.")

    except Exception as e:
        send_tg(f"❌ Alpaca 脚本错误: `{str(e)}`")

if __name__ == "__main__":
    main()
