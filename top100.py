import requests
from bs4 import BeautifulSoup
import os
import time

# 配置
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def get_nasdaq_100_symbols():
    print("正在从维基百科动态加载最新的纳斯达克100成分股...")
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        table = soup.find('table', {'id': 'constituents'})
        if not table:
            print("未找到 id 为 constituents 的表格")
            return []

        # 1. 动态定位 Ticker 所在的列索引
        headers = [th.text.strip().lower() for th in table.find_all('th')]
        ticker_idx = -1
        for idx, h in enumerate(headers):
            if 'ticker' in h or 'symbol' in h:
                ticker_idx = idx
                break
        
        if ticker_idx == -1:
            ticker_idx = 1 # 如果找不到，默认使用历史经验常规的第二列
            
        # 2. 遍历行提取数据
        symbols = []
        for row in table.find_all('tr')[1:]: # 跳过表头
            cols = row.find_all('td')
            if len(cols) > ticker_idx:
                symbol = cols[ticker_idx].text.strip().replace('.', '-')
                if symbol:
                    symbols.append(symbol)
                    
        print(f"成功加载最新成分股，共计 {len(symbols)} 只股票代码。")
        return symbols
    except Exception as e:
        print(f"解析最新成分股列表失败: {e}")
        return []

def get_stock_details(symbol):
    try:
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        result = data['chart']['result'][0]
        meta = result['meta']
        
        current_price = meta.get('regularMarketPrice')
        volume = meta.get('regularMarketVolume')
        prev_close = meta.get('previousClose')
        market_cap = meta.get('marketCap', 0)
        
        if not current_price or not volume:
            return None
            
        turnover = current_price * volume
        daily_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
        
        highs = [h for h in result['indicators']['quote'][0]['high'] if h is not None]
        ath = max(max(highs), current_price) if highs else current_price
        drawdown = ((current_price - ath) / ath) * 100
        
        return {
            "symbol": symbol,
            "price": current_price,
            "turnover": turnover,
            "drawdown": round(drawdown, 2),
            "market_cap": market_cap,
            "daily_change": round(daily_change, 2)
        }
    except Exception as e:
        return None

def format_amount(num):
    if num is None or num == 0:
        return "N/A"
    if num >= 1e12:
        return f"{num / 1e12:.2f}万亿"
    if num >= 1e8:
        return f"{num / 1e8:.2f}亿"
    if num >= 1e6:
        return f"{num / 1e6:.2f}万"
    return str(round(num, 2))

def main():
    symbols = get_nasdaq_100_symbols()
    if not symbols:
        return

    results = []
    print(f"正在获取标的详情并计算各项指标...")
    for s in symbols:
        data = get_stock_details(s)
        if data:
            results.append(data)
        time.sleep(0.15)

    results.sort(key=lambda x: x['turnover'], reverse=True)
    top_20 = results[:20]

    if not top_20:
        print("未收集到足够的行情数据。")
        return

    msg = "📊 *纳斯达克100 · 交易额 Top20 监控*\n"
    msg += "*(数据按当日交易金额降序排列)*\n\n"
    
    for i, s in enumerate(top_20, 1):
        change_icon = "🔺" if s['daily_change'] >= 0 else "🔻"
        change_sign = "+" if s['daily_change'] > 0 else ""
        
        msg += f"{i}. *{s['symbol']}* (现价: ${s['price']:.2f})\n"
        msg += f" 💰 交易金额: `{format_amount(s['turnover'])}` | 市值: `{format_amount(s['market_cap'])}`\n"
        msg += f" {change_icon} 当日涨跌: `{change_sign}{s['daily_change']}%`\n"
        msg += f" 📉 5年高点回撤: `{s['drawdown']}%`\n\n"

    if TG_TOKEN and TG_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try:
            res = requests.post(tg_url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
            if res.status_code == 200:
                print("✨ 自动推送成功！")
            else:
                print(f"TG 渠道返回错误: {res.text}")
        except Exception as e:
            print(f"TG 通信异常: {e}")
    else:
        print(msg)

if __name__ == "__main__":
    main()
