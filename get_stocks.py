from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
import yfinance as yf


def get_all_us_tickers():
  tickers = set()

  # 1. 获取 NASDAQ 上市股票列表
  try:
    url_nasdaq = (
        "http://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    )
    res = requests.get(url_nasdaq, timeout=10)
    for line in res.text.splitlines()[1:-1]:
      parts = line.split("|")
      if len(parts) > 0:
        ticker = parts[0]
        if "." in ticker:
          ticker = ticker.replace(".", "-")
        if "^" not in ticker and "$" not in ticker:
          tickers.add(ticker)
  except Exception as e:
    print(f"Error fetching NASDAQ tickers: {e}")

  # 2. 获取其他交易所（NYSE, AMEX 等）上市股票列表
  try:
    url_other = "http://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    res = requests.get(url_other, timeout=10)
    for line in res.text.splitlines()[1:-1]:
      parts = line.split("|")
      if len(parts) > 4:
        ticker = parts[0]
        if "." in ticker:
          ticker = ticker.replace(".", "-")
        if "^" not in ticker and "$" not in ticker:
          tickers.add(ticker)
  except Exception as e:
    print(f"Error fetching other listed tickers: {e}")

  return list(tickers)


def fetch_stock_cap(ticker):
  try:
    stock = yf.Ticker(ticker)
    # 优先使用 fast_info
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


# 获取全量美股代码
print("正在从 NASDAQ 官方目录下载全量美股代码...")
all_tickers = get_all_us_tickers()
print(f"共获取到 {len(all_tickers)} 个代码，开始多线程并发检查市值...")

large_caps = []

# 使用线程池加速查询并降低单线程阻塞风险
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

# 关键校验：如果没抓到任何数据，直接抛出异常，防止生成空白 Issue
if len(large_caps) == 0:
  raise ValueError(
      "错误：未抓取到任何市值大于1000亿的股票，可能是触发了接口限制。"
  )

# 按市值降序排序
large_caps.sort(key=lambda x: x[1], reverse=True)

# 生成 Markdown 内容
date_str = datetime.now().strftime("%Y-%m-%d")
content = f"### 美股市值 > 1000亿美元股票列表 ({date_str})\n\n"
content += "| 股票代码 | 市值 (美元) |\n| :--- | :--- |\n"
for ticker, cap in large_caps:
  content += f"| {ticker} | ${cap:,.0f} |\n"

with open("issue_body.md", "w", encoding="utf-8") as f:
  f.write(content)
