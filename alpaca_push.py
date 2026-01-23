import os
import requests

# --- 从 GitHub Secrets 获取 ---
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def send_tg(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TG_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'})

def main():
    # 验证 Key 是否有效 (针对 Paper 账户使用 paper-api 域名)
    auth_test_url = "https://paper-api.alpaca.markets/v2/account"
    
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": SECRET_KEY,
        "Content-Type": "application/json"
    }

    # 第一步：先测试鉴权
    test_res = requests.get(auth_test_url, headers=headers)
    if test_res.status_code != 200:
        error_info = f"❌ Alpaca 鉴权失败 (401): 请检查 Paper Key 是否正确。\n响应内容: {test_res.text}"
        print(error_info)
        send_tg(error_info)
        return

    # 第二步：抓取行情数据
    # 注意：Alpaca 免费版行情数据请求地址
    data_url = "https://data.alpaca.markets/v2/stocks/snapshots"
    symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC"]
    
    try:
        res = requests.get(data_url, headers=headers, params={"symbols": ",".join(symbols)})
        res.raise_for_status()
        data = res.json()

        stock_stats = []
        for symbol, info in data.items():
            # 提取价格和成交量
            daily = info.get('dailyBar', {})
            price = info.get('latestTrade', {}).get('p', 0)
            volume = daily.get('v', 0)
            prev_close = info.get('prevDailyBar', {}).get('c', 0)
            
            if price > 0:
                amount = price * volume
                change = ((price - prev_close) / prev_close * 100) if prev_close else 0
                stock_stats.append({
                    'symbol': symbol, 'price': price, 'amount': amount, 'change': change
                })

        # 按成交额排序
        top_3 = sorted(stock_stats, key=lambda x: x['amount'], reverse=True)[:3]

        msg = ["🏔️ **Alpaca (Paper) 美股成交额榜**"]
        for i, s in enumerate(top_3, 1):
            msg.append(f"{i}. **{s['symbol']}**")
            msg.append(f"   💰 价格: ${s['price']:.2f} ({s['change']:+.2f}%)")
            msg.append(f"   📊 估算成交额: ${s['amount']/1e8:.2f} 亿")

        send_tg("\n".join(msg))
        print("Success!")

    except Exception as e:
        send_tg(f"❌ 行情抓取失败: `{str(e)}`")

if __name__ == "__main__":
    main()
