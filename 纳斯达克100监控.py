import yfinance as yf
import pandas as pd
import requests
import os
import statistics
from datetime import datetime

# 1. 标的列表
TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALNY", "AMAT", "AMD", 
    "AMGN", "AMZN", "APP", "ARM", "ASML", "AVGO", "AXON", "BKNG", "BKR", "CCEP", 
    "CDNS", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CSX", 
    "CTAS", "CTSH", "DASH", "DDOG", "DXCM", "EA", "EXC", "FANG", "FAST", "FER", 
    "FTNT", "GEHC", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "INSM", "INTC", "INTU", 
    "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "MAR", "MCHP", "MDLZ", "MELI", 
    "META", "MNST", "MPWR", "MRVL", "MSFT", "MSTR", "MU", "NFLX", "NVDA", "NXPI", 
    "ODFL", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM", 
    "REGN", "ROP", "ROST", "SBUX", "SHOP", "SNPS", "STX", "TEAM", "TMUS", "TRI", 
    "TSLA", "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDAY", "WDC", "WMT", "XEL", "ZS"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def format_market_cap(n):
    """格式化市值为易读格式 (T/B)"""
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    elif n >= 1e9:
        return f"${n/1e9:.2f}B"
    return f"${n:,.0f}"

def 综合分析报告():
    print(f"🚀 开始深度分析 (TOP 60 市值排行 + 回撤数据)...")
    
    # --- 1. 获取市值并排序 ---
    print("📊 正在获取实时市值数据...")
    mcap_list = []
    tickers_obj = yf.Tickers(TICKERS)
    for ticker in TICKERS:
        try:
            info = tickers_obj.tickers[ticker].fast_info
            mcap = info.get('market_cap', 0)
            if mcap > 0:
                mcap_list.append({"symbol": ticker, "mcap": mcap, "mcap_str": format_market_cap(mcap)})
        except:
            continue
    
    # 排序并取前 60
    mcap_list.sort(key=lambda x: x['mcap'], reverse=True)
    top_60_data = mcap_list[:60]
    top_60_tickers = [x['symbol'] for x in top_60_data]

    # --- 2. 下载价格并计算回撤 ---
    try:
        data = yf.download(TICKERS, start="2020-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    # 计算当前回撤
    current_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            ath = df['High'].max()
            curr = df['Close'].iloc[-1]
            dd = (curr - ath) / ath * 100
            current_results.append({"symbol": ticker, "dd": dd})
        except: continue

    dd_map = {x['symbol']: x['dd'] for x in current_results}

    # --- 3. 构建消息文本 ---
    消息 = ["📊 **纳指100权重股回撤深度报告**", "---"]
    
    # 第一部分：市值前 60 详情
    消息.append(f"🔝 **市值排行 TOP 60 (及当前回撤)**")
    # 分成两列或单行显示，这里采用单行列表以保证数值清晰
    for i, item in enumerate(top_60_data, 1):
        ticker = item['symbol']
        mcap_val = item['mcap_str']
        drawdown = dd_map.get(ticker, 0)
        # 高亮回撤较大的权重股
        warn = "⚠️" if drawdown <= -20 else "▫️"
        消息.append(f"{i}. {warn} `{ticker:<5}`: **{mcap_val}** (DD: `{drawdown:.2f}%`)")
    
    消息.append("---")

    # 第二部分：整体统计
    all_dds = [x['dd'] for x in current_results]
    top60_dds = [dd_map[t] for t in top_60_tickers if t in dd_map]
    
    消息.append("💡 **市场广度统计**")
    消息.append(f"▫️ 全体平均回撤: `{statistics.mean(all_dds):.2f}%`")
    消息.append(f"▫️ **TOP 60 平均回撤**: `{statistics.mean(top60_dds):.2f}%`")
    消息.append(f"▫️ 全体中位数: `{statistics.median(all_dds):.2f}%`")
    
    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n--- 预览模式 ---")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # 如果文本太长，按 4000 字符切分发送
    MAX_LEN = 4000
    parts = [文本[i:i+MAX_LEN] for i in range(0, len(文本), MAX_LEN)]
    
    for i, part in enumerate(parts):
        payload = {
            "chat_id": CHAT_ID, 
            "text": part if len(parts) == 1 else f"(Part {i+1})\n{part}", 
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(URL, json=payload, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ 发送第 {i+1} 部分失败: {e}")
    
    print(f"✅ 报告已发送 (共 {len(parts)} 条消息)")

if __name__ == "__main__":
    report = 综合分析报告()
    推送到TG(report)
