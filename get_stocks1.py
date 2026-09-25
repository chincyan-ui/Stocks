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
        res = requests.get(url, headers=headers, timeout=10)
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

def filter_by_market_cap(symbols, min_cap=100_000_000_000, chunk_size=50):
    """通过新浪财经接口批量过滤市值在 min_cap（默认1000亿美元）以上的股票"""
    filtered_symbols = []
    symbol_list = sorted(list(symbols))
    total = len(symbol_list)
    print(f"Checking market cap for {total} stocks via Sina API (Batch Mode)...")
    
    headers = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    # 分批处理，每批查询 chunk_size 个股票
    for i in range(0, total, chunk_size):
        chunk = symbol_list[i:i + chunk_size]
        
        # 转换为新浪美股代码格式并拼接
        sina_codes = []
        code_to_sym = {}
        for sym in chunk:
            sina_sym = sym.lower().replace('.', '$').replace('-', '$')
            code = f"gb_{sina_sym}"
            sina_codes.append(code)
            code_to_sym[code] = sym
            
        url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
        
        try:
            res = session.get(url, timeout=5)
            if res.status_code == 200:
                # 解析返回的多行数据
                lines = res.text.strip().split(';')
                for line in lines:
                    if not line.strip():
                        continue
                    # 匹配格式: var hq_str_gb_aapl="...";
                    match_code = re.search(r'hq_str_(gb_[^=]+)=\"(.*?)\"', line)
                    if match_code:
                        code = match_code.group(1)
                        content = match_code.group(2)
                        sym = code_to_sym.get(code)
                        
                        if content:
                            p = content.split(",")
                            # 新浪美股数据中，p[12] 为总市值
                            if len(p) > 12 and p[12]:
                                try:
                                    market_cap = float(p[12])
                                    if market_cap >= min_cap:
                                        filtered_symbols.append(sym)
                                        print(f"[Pass] {sym}: ${market_cap / 1e9:.2f}B")
                                except ValueError:
                                    continue
            # 适当延时，防止请求过于频繁被新浪封禁
            time.sleep(0.1)
        except Exception as e:
            print(f"[Error] 批量获取市值失败 (Batch {i}-{i+chunk_size}): {e}")
            
    return filtered_symbols

def main():
    # 1. 从 SEC 抓取所有股票代码
    symbols = get_sec_symbols()
    
    if not symbols:
        print("未获取到任何 SEC 股票代码，程序终止。")
        return
        
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
