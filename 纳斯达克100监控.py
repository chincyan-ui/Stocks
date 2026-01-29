import yfinance as yf
import pandas as pd
import requests
import os
import statistics
import time
from datetime import datetime

# 1. 标的列表 (Nasdaq 100)
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

# 从环境变量读取配置
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def format_market_cap(n):
    """将市值数字格式化为易读的 T 或 B"""
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    elif n >= 1e9:
        return f"${n/1e9:.2f}B"
    return f"${n:,.0f}"

def 综合分析报告():
    print(f"🚀 任务启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # --- 第一步：获取市值并筛选前 60 ---
    print("📊 正在抓取市值数据...")
    mcap_data = []
    try:
        tickers_obj = yf.Tickers(TICKERS)
        for ticker in TICKERS:
            try:
                # 使用 fast_info 提高速度
                info = tickers_obj.tickers[ticker].fast_info
                mcap = info.get('market_cap', 0)
                if mcap and mcap > 0:
                    mcap_data.append({"symbol": ticker, "mcap": mcap, "mcap_str": format_market_cap(mcap)})
            except:
                continue
    except Exception as e:
        print(f"⚠️ 获取市值基础信息失败: {e}")

    # 按市值降序排列，取前 60
    mcap_data.sort(key=lambda x: x['mcap'], reverse=True)
    top_60_list = mcap_data[:60]
    top_60_tickers = [x['symbol'] for x in top_60_list]

    # --- 第二步：下载行情数据 ---
    print("📈 正在下载历史行情...")
    try:
        # 下载 2024 至今的数据以确保 2025 分析完整且 ATH 准确
        data = yf.download(TICKERS, start="2024-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载中断: {e}"

    if data.empty:
        return "❌ 无法获取行情数据，请检查网络。"

    # --- 第三步：计算 2025 历史快照 ---
    all_dates = data.index
    dates_2025 = all_dates[all_dates.year == 2025]
    snapshot_1029 = None
    TARGET_DATE_STR = "2025-10-29"

    if not dates_2025.empty:
        print("⏳ 正在回溯 2025 历史数据...")
        # 仅针对特定日期进行简单计算以节省性能
        if pd.Timestamp(TARGET_DATE_STR) in dates_2025:
            dds_1029 = []
            for ticker in TICKERS:
                try:
                    hist = data[ticker].loc[:TARGET_DATE_STR].dropna()
                    if len(hist) < 2: continue
                    ath = hist['High'].max()
                    price = hist['Close'].iloc[-1]
                    dds_1029.append((price - ath) / ath * 100)
                except: continue
            if dds_1029:
                snapshot_1029 = {"avg": statistics.mean(dds_1029), "med": statistics.median(dds_1029)}

    # --- 第四步：计算实时回撤 ---
    current_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            ath = df['High'].max()
            curr = df['Close'].iloc[-1]
            drawdown = (curr - ath) / ath * 100
            current_results.append({"symbol": ticker, "current": curr, "drawdown": drawdown})
        except: continue

    dd_map = {x['symbol']: x['drawdown'] for x in current_results}
    all_drawdowns = [x['drawdown'] for x in current_results]
    
    # --- 第五步：构建消息 ---
    消息 = ["📊 **纳指100权重股综合报告**", "---"]
    
    # 1. 历史对比
    if snapshot_1029:
        消息.append(f"📅 **历史回顾 ({TARGET_DATE_STR})**")
        消息.append(f"▫️ 平均回撤: `{snapshot_1029['avg']:.2f}%`")
        消息.append(f"▫️ 中位数: `{snapshot_1029['med']:.2f}%` \n---")

    # 2. 市值前 60 详情
    消息.append(f"🔝 **市值排行 TOP 60 (实时回撤)**")
    if not top_60_list:
        消息.append("⚠️ 暂无市值排行信息")
    else:
        for i, item in enumerate(top_60_list, 1):
            t = item['symbol']
            m_str = item['mcap_str']
            dd = dd_map.get(t, 0)
            tag = "🚨" if dd <= -30 else "⚠️" if dd <= -20 else "▫️"
            消息.append(f"{i}. {tag} `{t:<5}`: **{m_str}** (DD: `{dd:.2f}%`)")
    
    消息.append("---")

    # 3. 统计概览
    if all_drawdowns:
        top60_dds = [dd_map[t] for t in top_60_tickers if t in dd_map]
        消息.append("💡 **当前统计概览**")
        消息.append(f"▫️ 全体平均回撤: **{statistics.mean(all_drawdowns):.2f}%**")
        if top60_dds:
            消息.append(f"▫️ **TOP 60 平均回撤**: **{statistics.mean(top60_dds):.2f}%**")
        消息.append(f"▫️ 全体中位数: `{statistics.median(all_drawdowns):.2f}%` ")
        
        crash_count = len([d for d in all_drawdowns if d <= -50])
        消息.append(f"▫️ 回撤 > 50% 占比: `{ (crash_count/len(all_drawdowns))*100 :.2f}%` ({crash_count}只)")

    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n⚠️ 缺失环境变量: TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID")
        print("--- 报告预览 ---")
        print(文本[:500] + "...")
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # 自动分段发送 (Telegram 限制每条消息 4096 字符)
    MAX_LEN = 4000
    parts = [文本[i:i+MAX_LEN] for i in range(0, len(文本), MAX_LEN)]
    
    for i, part in enumerate(parts):
        payload = {
            "chat_id": CHAT_ID, 
            "text": part if len(parts) == 1 else f"*(Part {i+1}/ {len(parts)})*\n{part}", 
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(URL, json=payload, timeout=30)
            if r.status_code == 200:
                print(f"✅ 报告第 {i+1} 部分发送成功")
            else:
                print(f"❌ 发送失败 (HTTP {r.status_code}): {r.text}")
        except Exception as e:
            print(f"❌ 网络请求异常: {e}")

if __name__ == "__main__":
    report_content = 综合分析报告()
    推送到TG(report_content)
