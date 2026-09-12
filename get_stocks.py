import json
import time
import requests
import yfinance as yf

def get_sec_symbols():
    """从 SEC 官方接口获取所有公司的股票代码"""
    symbols = set()
    # SEC 强制要求：User-Agent 必须包含应用名称和真实联系邮箱
    headers = {
        "User-Agent": "MyStockCheckerApp chincyan@gmail.com"
    }
    url = "https://www.sec.gov/files/company_tickers.json"
    
    try:
        res = requests.get(url, headers=headers)
        print(f"SEC API Response Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            for item in data.values():
                sym = item.get("ticker")
                if sym:
                    sym = sym.strip().replace(' ', '-').replace('.', '-')
                    symbols.add(sym)
            print(f"Successfully fetched {len(symbols)} symbols from SEC.")
        else:
            print(f"Error fetching SEC data: Status code {res.status_code}")
    except Exception as e:
        print(f"Error fetching SEC tickers: {e}")
        
    return symbols

def filter_by_market_cap(symbols, min_cap=100_000_000_000):
    """使用 fast_info 仅获取市值，大幅提升速度"""
    filtered_symbols = []
    print(f"Checking market cap for {len(symbols)} stocks...")
    
    for sym in sorted(list(symbols)):
        try:
            ticker = yf.Ticker(sym)
            
            # 使用 fast_info 代替 ticker.info，只加载基础盘口与市值，速度极快
            market_cap = ticker.fast_info.get("market_cap", 0)
            
            if market_cap and market_cap >= min_cap:
                filtered_symbols.append(sym)
                print(f"[Pass] {sym}: ${market_cap / 1e9:.2f}B")
            else:
                print(f"[Skip] {sym}: 市值低于1000亿或获取失败")
                
            # 缩短等待时间，因为 fast_info 的开销非常小
            time.sleep(0.1)
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
