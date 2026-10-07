import json
import os
import time
from datetime import datetime, timedelta
import requests
import re
import yfinance as yf  # 用于获取历史最高价 (ATH)

ATH_CACHE_FILE = "ath_cache.json"

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
    
    for i in range(0, total, chunk_size):
        chunk = symbol_list[i:i + chunk_size]
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
                lines = res.text.strip().split(';')
                for line in lines:
                    if not line.strip():
                        continue
                    match_code = re.search(r'hq_str_(gb_[^=]+)=\"(.*?)\"', line)
                    if match_code:
                        code = match_code.group(1)
                        content = match_code.group(2)
                        sym = code_to_sym.get(code)
                        
                        if content:
                            p = content.split(",")
                            if len(p) > 12 and p[12]:
                                try:
                                    market_cap = float(p[12])
                                    if market_cap >= min_cap:
                                        filtered_symbols.append(sym)
                                        print(f"[Pass] {sym}: ${market_cap / 1e9:.2f}B")
                                except ValueError:
                                    continue
            time.sleep(0.1)
        except Exception as e:
            print(f"[Error] 批量获取市值失败 (Batch {i}-{i+chunk_size}): {e}")
            
    return filtered_symbols

def get_ath_data(symbols):
    """
    获取股票的历史最高价 (ATH)。
    引入缓存机制：检查本地 ath_cache.json，如果距离上次更新不足 30 天，则直接读取缓存，
    否则重新向 Yahoo Finance 请求全量大市值股票的的历史最高价，实现一个月更新一次。
    """
    cache_data = {"last_updated": "", "data": {}}
    
    # 1. 尝试读取本地缓存
    if os.path.exists(ATH_CACHE_FILE):
        try:
            with open(ATH_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as e:
            print(f"读取 ATH 缓存失败: {e}")
            
    last_updated_str = cache_data.get("last_updated")
    need_update = True
    
    if last_updated_str:
        try:
            last_updated_date = datetime.strptime(last_updated_str, "%Y-%m-%d")
            # 判断是否在一个月（30天）以内
            if datetime.now() - last_updated_date < timedelta(days=30):
                print(f"ATH 数据上次更新于 {last_updated_str}，未满 30 天，直接使用缓存。")
                need_update = False
        except ValueError:
            pass

    ath_dict = cache_data.get("data", {})
    
    if need_update:
        print("开始更新大市值股票的 ATH (All-Time High) 数据...")
        for sym in symbols:
            try:
                # 使用 yfinance 获取历史数据求最大高点
                ticker = yf.Ticker(sym)
                # 获取历史行情，history(period="max") 包含上市以来的所有数据
                hist = ticker.history(period="max")
                if not hist.empty:
                    ath_price = float(hist["High"].max())
                    ath_dict[sym] = round(ath_price, 2)
                    print(f"[ATH Updated] {sym}: ${ath_dict[sym]}")
                else:
                    # 如果历史数据为空，保留旧数据或设为 None
                    if sym not in ath_dict:
                        ath_dict[sym] = None
                # 避免请求过于频繁触发限制
                time.sleep(0.2)
            except Exception as e:
                print(f"[Error] 获取 {sym} 的 ATH 失败: {e}")
                
        # 更新缓存文件
        cache_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data": ath_dict
        }
        try:
            with open(ATH_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
            print("Successfully updated ath_cache.json")
        except Exception as e:
            print(f"保存 ATH 缓存失败: {e}")
            
    return ath_dict

def main():
    # 1. 从 SEC 抓取所有股票代码
    symbols = get_sec_symbols()
    
    if not symbols:
        print("未获取到任何 SEC 股票代码，程序终止。")
        return
        
    # 2. 通过新浪财经接口筛选市值在 1000 亿美元以上的代码
    large_cap_symbols = filter_by_market_cap(symbols, min_cap=100_000_000_000)
    
    # 3. 获取或更新 ATH 数据（一个月更新一次）
    ath_data = get_ath_data(large_cap_symbols)
    
    # 4. 组装最终输出数据（包含 symbol 和 ATH）
    stock_list = []
    for s in sorted(large_cap_symbols):
        stock_item = {
            "symbol": s,
            "ath": ath_data.get(s, None)
        }
        stock_list.append(stock_item)
        
    print(f"Total unique stocks with market cap > $100B: {len(stock_list)}")

    # 5. 自动生成 GitHub Actions 需要的 issue_body.md 文件
    body_content = f"```json\n{json.dumps(stock_list, ensure_ascii=False, indent=2)}\n```"
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(body_content)
    print("Successfully generated issue_body.md")

if __name__ == "__main__":
    main()
