import json
import time
import requests
import yfinance as yf

def get_sec_symbols():
    """从 SEC 官方接口获取所有公司的股票代码"""
    symbols = set()
    # SEC 要求 User-Agent 包含有效的联系方式（例如你的应用名和邮箱）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    url = "https://www.sec.gov/files/company_tickers.json"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            # SEC 返回的 json 格式形如: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
            for item in data.values():
                sym = item.get("ticker")
                if sym:
                    # 格式化兼容（将空格或点替换为连字符）
                    sym = sym.strip().replace(' ', '-').replace('.', '-')
                    symbols.add(sym)
            print(f"Successfully fetched {len(symbols)} symbols from SEC.")
        else:
            print(f"Error fetching SEC data: Status code {res.status_code}")
    except Exception as e:
        print(f"Error fetching SEC tickers: {e}")
        
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
            
            # 适当延时，避免请求过于频繁触发限制
            time.sleep(0.5)
        except Exception as e:
            print(f"[Error] 获取 {sym} 市值失败: {e}")
            
    return filtered_symbols

def main():
    # 1. 从 SEC 抓取所有股票代码
    symbols = get_sec_symbols()
    
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
