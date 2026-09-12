from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
import yfinance as yf


def get_all_us_tickers():
  # 改用稳定维护的 GitHub 开源美股全量代码文件，避免官方 FTP 在云端超时
  url = "https://raw.githubusercontent.com/nvstly/symbols/main/all_tickers.txt"
  try:
    res = requests.get(url, timeout=15)
    tickers = [
        line.strip().replace(".", "-")
        for line in res.text.splitlines()
        if line.strip() and "^" not in line and "$" not in line
    ]
    return list(set(tickers))
  except Exception as e:
    print(f"Error fetching tickers from mirror: {e}")
    return []


def fetch_stock_cap(ticker):
  try:
    stock = yf.Ticker(ticker)
    market_cap = None
    try:
      market_cap = stock.fast_info.get("market_cap", 0)
    except Exception:
      pass

    if not market_cap:
      market_cap = stock.info.get("marketCap", 0)

    if market_cap and market_cap > 100e9:
      return (ticker, market_cap)
  except Exception:
    pass
  return None


print("正在从稳定镜像源获取全量美股代码...")
all_tickers = get_all_us_tickers()
print(f"共获取到 {len(all_tickers)} 个代码，开始多线程并发检查市值...")

large_caps = []

with ThreadPoolExecutor(max_workers=10) as executor:
  futures = {
      executor.submit(fetch_stock_cap, ticker): ticker
      for ticker in all_tickers
  }
  for future in as_completed(futures):
    result = future.result()
    if result:
      large_caps.append(result)
      print(f"[Match] {result[0]}: ${result[1]:,.0f}")

if len(large_caps) == 0:
  raise ValueError("错误：未抓取到任何市值大于1000亿的股票。")

large_caps.sort(key=lambda x: x[1], reverse=True)

date_str = datetime.now().strftime("%Y-%m-%d")
content = f"### 美股市值 > 1000亿美元股票列表 ({date_str})\n\n"
content += "| 股票代码 | 市值 (美元) |\n| :--- | :--- |\n"
for ticker, cap in large_caps:
  content += f"| {ticker} | ${cap:,.0f} |\n"

with open("issue_body.md", "w", encoding="utf-8") as f:
  f.write(content)
