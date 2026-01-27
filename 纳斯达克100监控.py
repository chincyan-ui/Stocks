import yfinance as yf
import pandas as pd
import requests
import os
import statistics

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

def 综合分析报告():
    print(f"🚀 开始下载数据并分析 (包含 2025 全年回溯)...")
    
    # 下载从 2020 年开始的数据以确保 ATH 计算准确
    try:
        data = yf.download(TICKERS, start="2020-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 下载失败: {e}"

    # --- 第一部分：计算 2025 年极值 ---
    all_dates = data.index
    target_dates_2025 = all_dates[all_dates.year == 2025]
    
    daily_stats_2025 = []
    
    if not target_dates_2025.empty:
        print("⏳ 正在回溯 2025 历史极值...")
        for current_date in target_dates_2025:
            dds = []
            for ticker in TICKERS:
                try:
                    hist = data[ticker].loc[:current_date].dropna()
                    if len(hist) < 2: continue
                    ath = hist['High'].max()
                    price = hist['Close'].iloc[-1]
                    dds.append((price - ath) / ath * 100)
                except: continue
            if dds:
                daily_stats_2025.append({
                    "date": current_date.strftime('%Y-%m-%d'),
                    "avg": statistics.mean(dds),
                    "median": statistics.median(dds)
                })

    # 找出 2025 最惨的一天
    worst_avg_2025 = min(daily_stats_2025, key=lambda x: x['avg']) if daily_stats_2025 else None
    worst_med_2025 = min(daily_stats_2025, key=lambda x: x['median']) if daily_stats_2025 else None

    # --- 第二部分：计算当前实时数据 ---
    current_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            ath = df['High'].max()
            curr = df['Close'].iloc[-1]
            drawdown = (curr - ath) / ath * 100
            current_results.append({"symbol": ticker, "current": curr, "ath": ath, "drawdown": drawdown})
        except: continue

    current_results.sort(key=lambda x: x['drawdown'])
    curr_drawdowns = [x['drawdown'] for x in current_results]
    
    # --- 第三部分：构建消息 ---
    消息 = ["📊 **纳指100回撤深度综合报告**", "---"]
    
    # 1. 2025 极值板块
    if worst_avg_2025:
        消息.append("📅 **2025 年度历史极值 (Max DD)**")
        消息.append(f"▫️ 平均回撤峰值: `{worst_avg_2025['avg']:.2f}%` ({worst_avg_2025['date']})")
        消息.append(f"▫️ 中位数峰值: `{worst_med_2025['median']:.2f}%` ({worst_med_2025['date']})")
        消息.append("---")

    # 2. 当前概览
    消息.append("💡 **当前市场状态**")
    消息.append(f"▫️ 样本数: `{len(current_results)}` 只")
    消息.append(f"▫️ 平均回撤: **{statistics.mean(curr_drawdowns):.2f}%**")
    消息.append(f"▫️ 中位数: **{statistics.median(curr_drawdowns):.2f}%**")
    
    crash_count = len([d for d in curr_drawdowns if d <= -50])
    消息.append(f"▫️ 回撤 > 50% 占比: `{ (crash_count/len(current_results))*100 :.2f}%` ({crash_count}只)")
    消息.append("---")
    
    # 3. 深蹲名单
    消息.append("🔥 **实时深蹲 Top 10**")
    for i, item in enumerate(current_results[:10], 1):
        tag = "🆘" if item['drawdown'] <= -50 else "🚨" if item['drawdown'] <= -30 else "📉"
        消息.append(f"{i}. {tag} **{item['symbol']}**: `{item['drawdown']:.2f}%` (Price: `{item['current']:.2f}`)")

    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print(文本)
        return
    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        r = requests.post(URL, json=payload, timeout=30)
        r.raise_for_status()
        print("✅ 综合报告已发送")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    report = 综合分析报告()
    推送到TG(report)
