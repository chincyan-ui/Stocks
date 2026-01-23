import requests
import os

# 修改后的环境变量名称
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # 已修改

def get_precise_top_3():
    """获取 Polygon.io 精确成交额数据"""
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?apikey={POLYGON_API_KEY}"
    
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data.get('status') != 'OK':
            print(f"数据源状态异常: {data.get('status')}")
            return None
        
        results = []
        for ticker in data.get('tickers', []):
            day = ticker.get('day', {})
            volume = day.get('v', 0)    # 当日总成交量
            vwap = day.get('vw', 0)     # 成交量加权平均价 (最具权威的计算基准)
            
            if volume > 0 and vwap > 0:
                dollar_volume = volume * vwap
                results.append({
                    'symbol': ticker.get('ticker'),
                    'dollar_volume': dollar_volume,
                    'price': ticker.get('lastQuote', {}).get('p', day.get('c', 0)),
                    'change_p': ticker.get('todaysChangePerc', 0)
                })
        
        # 按成交额降序排列，取前三名
        return sorted(results, key=lambda x: x['dollar_volume'], reverse=True)[:3]
    except Exception as e:
        print(f"数据抓取失败: {e}")
        return None

def send_telegram(stocks):
    """发送格式化消息到 Telegram"""
    if not stocks:
        return

    message = "🏛 **Polygon.io 机构级数据推送**\n"
    message += "📅 *美股当日成交额 Top 3*\n\n"
    
    for i, s in enumerate(stocks, 1):
        bn_val = s['dollar_volume'] / 1e9
        message += (f"{i}. **{s['symbol']}**\n"
                    f"   💰 成交额: `${bn_val:.2f}B` (VWAP计价)\n"
                    f"   📈 最新价: `${s['price']:.2f}`\n"
                    f"   📊 涨跌幅: `{s['change_p']:.2f}%` \n\n")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # 使用更新后的变量名 TELEGRAM_CHAT_ID
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        res = requests.post(url, data=payload)
        res.raise_for_status()
        print("Telegram 推送成功！")
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    top_3 = get_precise_top_3()
    if top_3:
        send_telegram(top_3)
