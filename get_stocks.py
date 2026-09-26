import json
import time
import requests
import re
import logging
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 配置日志记录格式，适配 CI/CD 环境
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_sec_symbols():
    """从 SEC 官方接口获取所有公司的股票代码"""
    symbols = set()
    headers = {
        "User-Agent": "MyStockCheckerApp chincyan@gmail.com"
    }
    url = "https://www.sec.gov/files/company_tickers.json"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        logging.info(f"SEC API Response Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            for item in data.values():
                sym = item.get("ticker")
                if sym:
                    symbols.add(sym.strip())
            logging.info(f"Successfully fetched {len(symbols)} symbols from SEC.")
        else:
            logging.error(f"Error fetching SEC data: Status code {res.status_code}")
    except Exception as e:
        logging.error(f"Error fetching SEC tickers: {e}")
        
    return symbols

def _fetch_single_yfinance_cap(sym, min_cap):
    """单只股票的 yfinance 查询子函数（用于多线程调用）"""
    try:
        ticker = yf.Ticker(sym)
        # 使用 fast_info 获取市值
        market_cap = ticker.fast_info.get("market_cap", 0)
        if market_cap and market_cap >= min_cap:
            logging.info(f"[Pass - YF] {sym}: ${market_cap / 1e9:.2f}B")
            return sym
    except Exception as e:
        # 忽略退市或解析异常的股票
        pass
    return None

def filter_by_market_cap_yfinance(symbols, min_cap=100_000_000_000, max_workers=20):
    """【多线程备用方案】使用线程池并发通过 yfinance 获取市值，大幅提升降级查询效率"""
    logging.info(f"Switching to backup data source: yfinance (Multi-threaded, workers={max_workers})...")
    filtered_symbols = []
    symbol_list = sorted(list(symbols))
    
    # 线程安全锁，用于保护共享列表的写入
    lock = threading.Lock()
    
    def worker(sym):
        result = _fetch_single_yfinance_cap(sym, min_cap)
        if result:
            with lock:
                filtered_symbols.append(result)

    # 使用 ThreadPoolExecutor 进行并发处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, sym) for sym in symbol_list]
        # 等待所有线程完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                pass
                
    return filtered_symbols

def filter_by_market_cap(symbols, min_cap=100_000_000_000, chunk_size=50):
    """通过新浪财经接口批量过滤市值，若失败则自动降级使用 yfinance（多线程）"""
    filtered_symbols = []
    symbol_list = sorted(list(symbols))
    total = len(symbol_list)
    logging.info(f"Checking market cap for {total} stocks via Sina API (Batch Mode)...")
    
    headers = {
        "Referer": "http://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    sina_failed = False
    success_batches = 0
    
    # 分批处理，每批查询 chunk_size 个股票
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
                                        logging.info(f"[Pass - Sina] {sym}: ${market_cap / 1e9:.2f}B")
                                except ValueError:
                                    continue
                success_batches += 1
            else:
                logging.warning(f"Sina API returned status code {res.status_code} at batch {i}-{i+chunk_size}")
                sina_failed = True
                break
                
            time.sleep(0.1)
        except Exception as e:
            logging.warning(f"Sina API batch request failed ({i}-{i+chunk_size}): {e}")
            sina_failed = True
            break
            
    # 容灾兜底逻辑：如果新浪接口整体报错、被墙或未能正常拉取到数据，切换至多线程 yfinance
    if sina_failed or (success_batches == 0 and total > 0):
        logging.warning("Sina API is unavailable or blocked. Triggering fallback to multi-threaded yfinance...")
        return filter_by_market_cap_yfinance(symbols, min_cap)
        
    return filtered_symbols

def main():
    # 1. 从 SEC 抓取所有股票代码
    symbols = get_sec_symbols()
    
    if not symbols:
        logging.critical("未获取到任何 SEC 股票代码，程序终止。")
        return
        
    # 2. 筛选市值在 1000 亿美元以上的代码（带主备自动切换）
    large_cap_symbols = filter_by_market_cap(symbols, min_cap=100_000_000_000)
    
    stock_list = [{"symbol": s} for s in sorted(large_cap_symbols)]
    logging.info(f"Total unique stocks with market cap > $100B: {len(stock_list)}")

    # 3. 自动生成 GitHub Actions 需要的 issue_body.md 文件
    body_content = f"```json\n{json.dumps(stock_list, ensure_ascii=False)}\n```"
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(body_content)
    logging.info("Successfully generated issue_body.md")

if __name__ == "__main__":
    main()
