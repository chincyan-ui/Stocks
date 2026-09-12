import json
import requests
from bs4 import BeautifulSoup
import yfinance as yf

def get_wiki_symbols(url, selector):
    symbols = set()
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select(selector)
            for row in rows[1:]:
                cols = row.select('td')
                if cols:
                    sym = cols[0].text.strip().replace(' ', '-').replace('.', '-')
                    if sym:
                        symbols.add(sym)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return symbols

def filter_by_market_cap(symbols, min_cap=100_000_000_000):
    """过滤市值在 min_cap（默认1000亿美元）以上的股票"""
    filtered_symbols = []
    print(f"Checking market cap for {len(symbols)} stocks...")
    
    for sym in sorted(list(symbols)):
        try:
            # 获取股票信息
            ticker = yf.Ticker(sym)
            # 部分股票的 info 可能会缺失 marketCap，需做兼容处理
            market_cap = ticker.info.get("marketCap", 0)
            
            if market_cap and market_cap >= min_cap:
                filtered_symbols.append(sym)
                print(f"[Pass] {sym}: ${market_cap / 1e9:.2f}B")
            else:
                print(f"[Skip] {sym}: 市值低于1000亿或获取失败")
        except Exception as e:
            print(f"[Error] 获取 {sym} 市值失败: {e}")
            
    return filtered_symbols

def main():
    # 1. 抓取标普 500 和 纳指 100
    symbols = {"SPCH"}
    
    sp500 = get_wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 'table#constituents tr')
    nd100 = get_wiki_symbols("https://en.wikipedia.org/wiki/Nasdaq-100", 'table#constituents tr')
    
    symbols.update(sp500)
    symbols.update(nd100)
    
    # 2. 筛选市值在 1000 亿美元以上的代码
    large_cap_symbols = filter_by_market_cap(symbols, min_cap=100_000_000_000)
    
    stock_list = [{"symbol": s} for s in sorted(large_cap_symbols)]
    print(f"Total unique stocks with market cap > $100B: {len(stock_list)}")

    # 3. 自动生成 GitHub Actions 需要的 issue_body.md 文件
    body_content = f"```json\n{json.dumps(stock_list, ensure_ascii=False)}\n```"
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(body_content)
    print("Successfully generated issue_body.md")

if __name__ == "__main__":
    main()
