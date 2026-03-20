import requests
from bs4 import BeautifulSoup
import os
import time

# 配置
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def get_top_100_symbols():
    print("正在从 CompaniesMarketCap 抓取前100名列表...")
    url = "https://companiesmarketcap.com/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        symbols = []
        # 定位表格中的股票代码
        code_elements = soup.select('div.company-code')
        for code in code_elements:
            symbols.append(code.get_text().strip())
            if len(symbols) >= 100:
                break
        return symbols
    except Exception as e:
        print(f"抓取列表失败: {e}")
        return []

def get_drawdown_data(symbol):
    try:
        # 获取 5 年数据计算 ATH
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        data = res.json()
        
        result = data['chart']['result'][0]
        current_price = result['meta']['regularMarketPrice']
        highs = [h for h in result['indicators']['quote'][0]['high'] if h is not None]
        
        ath = max(max(highs), current_price)
        drawdown = ((current_price - ath) / ath) * 100
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "ath": round(ath, 2),
            "drawdown": round(drawdown, 2)
        }
    except:
        return None

def main():
    symbols = get_top_100_symbols()
    if not symbols:
        return

    results = []
    print(f"开始获取 {len(symbols)} 个股票的详细行情...")
    for s in symbols:
        data = get_drawdown_data(s)
        if data:
            results.append(data)
        time.sleep(0.2) # 防止请求过快被封

    # 按回撤排序 (负数越小表示跌得越多)
    results.sort(key=lambda x: x['drawdown'])
    top_10 = results[:10]

    # 构建 TG 消息
    msg = "📉 *市值 Top100 股票回撤榜 (最大10个)*\n\n"
    for i, s in enumerate(top_10, 1):
        msg += f"{i}. *{s['symbol']}*\n"
        msg += f"   现价: `${s['price']}` | ATH: `${s['ath']}`\n"
        msg += f"   *回撤幅度: {s['drawdown']}%*\n\n"

    # 发送
    if TG_TOKEN and TG_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(tg_url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print("推送成功")
    else:
        print(msg)

if __name__ == "__main__":
    main()
