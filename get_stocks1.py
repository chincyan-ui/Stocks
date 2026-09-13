import json
import time
import requests
import re

def get_sec_symbols():
    """从 SEC 官方接口获取所有公司的股票代码"""
    symbols = set()
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
                    symbols.add(sym.strip())
            print(f"Successfully fetched {len(symbols)} symbols from SEC.")
        else:
            print(f"Error fetching SEC data: Status code {res.status_code}")
    except Exception as e:
        print(f"Error fetching SEC tickers: {e}")
        
    return symbols

def filter_by_market_cap(symbols, min_cap=100_000_000_000):
    """通过新浪财经接口过滤市值在 min_cap（默认1000亿美元）以上的股票"""
    filtered_symbols = []
    print(f"Checking market cap for {len(symbols)} stocks via Sina API...")
    
    headers = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    for sym in sorted(list(symbols)):
        try:
            # 参照新浪美股代码规则：小写、将点和连字符转为 $（如 BRK.A 或 BRK-A 转换为 brk$a）
            sina_sym = sym.lower().replace('.', '$').replace('-', '$')
            code = f"gb_{sina_sym}"
            
            url = f"http://hq.sinajs.cn/list={code}"
            res = requests.get(url, headers=headers, timeout=5)
            
            if res.status_code == 200:
                match = re.search(r'\"(.*?)\"', res.text)
                if match and match.group(1):
                    p = match.group(1).split(",")
                    # 新浪美股数据中，p[12] 为总市值（单位：美元）
                    if len(p) > 12 and p[12]:
                        market_cap = float(p[12])
                        if market_cap >= min_cap:
                            filtered_symbols.append(sym)
                            print(f"[Pass] {sym}: ${market_cap / 1e9:.2f}B")
                        else:
                            print(f"[Skip] {sym}: 市值低于1000亿")
                    else:
                        print(f"[Skip] {sym}: 未获取到市值数据")
            
            time.sleep(0.2)
        except Exception as e:
            print(f"[Error] 获取 {sym} 市值失败: {e}")
            
    return filtered_symbols

def main():
    # 1. 从 SEC 抓取所有股票代码
    symbols = get_sec_symbols()
    
    # 2. 通过新浪财经接口筛选市值在 1000 亿美元以上的代码
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
