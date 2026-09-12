from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import yfinance as yf


def get_target_tickers():
  tickers = set()

  # 1. 获取标普 500 (S&P 500) 成分股代码表（维基百科官方表格，极稳定）
  try:
    url_sp500 = (
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )
    df_list = pd.read_html(url_sp500)
    sp500_tickers = df_list[0]["Symbol"].tolist()
    for t in sp500_tickers:
      tickers.add(t.replace(".", "-"))
  except Exception as e:
    print(f"Error fetching S&P 500 tickers: {e}")

  # 2. 获取纳斯达克 100 (Nasdaq 100) 成分股代码表
  try:
    url_ndx = (
        "https://en.wikipedia.org/wiki/Nasdaq-100"
    )
    df_list = pd.read_html(url_ndx)
    # 查找包含 Symbol 或 Ticker 的表格
    for df in df_list:
      for col in ["Company", "Ticker", "Symbol"]:
        if col in df.columns:
          for t in df[col].tolist():
            if isinstance(t, str) and len(t) <= 5:
              tickers.add(t.replace(".", "-"))
          break
  except Exception as e:
    print(f"Error fetching Nasdaq 100 tickers: {e}")

  # 补充一些常见的巨无霸或跨国大市值股以防万复
  extra_stocks = [
      "BRK-B",
      "TSM",
      "NVO",
      "ASML",
      "LLY",
      "V",
      "WMT",
      "JPM",
      "XOM",
      "MA",
      "UNH",
      "PG",
      "JNJ",
      "HD",
      "COST",
      "ABBV",
      "BAC",
      "NFLX",
      "KO",
      "PEP",
  ]
  for t in extra_stocks:
    tickers.add(t)

  return list(tickers)


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


print("正在获取标普500与纳斯达克100核心股票池...")
all_tickers = get_target_tickers()
print(f"共获取到 {len(all_tickers)} 个核心大盘股票代码，开始多线程并发检查市值...")

large_caps = []

# 因为总数精简到了 500 左右，用 5 个线程稳妥请求，极大避免被 Yahoo 封锁
with ThreadPoolExecutor(max_workers=5) as executor:
  futures = {
      executor.submit(fetch_stock_cap, ticker): ticker
      for ticker in all_tickers
  }
  for future in as_completed(futures):
    result = future.result()
    if result:
      large_caps.append(result)
      print(f"[Match] {result[0]}: ${result[1]:,.0f}")

if len(large_caps) < 10:
  raise ValueError(
      "错误：抓取到的千亿市值股票数量异常偏少，可能触发了限制。"
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
