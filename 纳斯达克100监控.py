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

def 综合分析报告():
    print(f"🚀 开始分析任务 (Top 10 深蹲详情)...")
    
    # --- 1. 下载行情数据 (使用 auto_adjust=True 获取前复权数据) ---
    try:
        # 下载较长时间范围以确保找到真正的历史最高价 (ATH)
        data = yf.download(TICKERS, start="2020-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 无法获取行情数据。"

    # --- 2. 计算回撤及最高价详情 ---
    analysis_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            
            # 找到前复权最高价及其发生的日期
            ath_price = df['High'].max()
            ath_date = df['High'].idxmax().strftime('%Y-%m-%d')
            
            curr_price = df['Close'].iloc[-1]
            drawdown = (curr_price - ath_price) / ath_price * 100
            
            analysis_results.append({
                "symbol": ticker,
                "current": curr_price,
                "ath_price": ath_price,
                "ath_date": ath_date,
                "drawdown": drawdown
            })
        except: continue

    # 按回撤从大到小排序 (跌得最惨的在前)
    analysis_results.sort(key=lambda x: x['drawdown'])
    
    # --- 3. 构建消息内容 ---
    消息 = ["📊 **纳指100回撤最大 Top 10 深度分析**", "---"]
    
    # 只取前 10 只回撤最大的
    top_10 = analysis_results[:10]
    
    for i, item in enumerate(top_10, 1):
        line = [
            f"{i}. 🔥 **{item['symbol']}**",
            f"▫️ 当前回撤: `{item['drawdown']:.2f}%`",
            f"▫️ 现价: `{item['current']:.2f}`",
            f"▫️ 历史最高价(前复权): `{item['ath_price']:.2f}`",
            f"▫️ 最高价日期: `{item['ath_date']}`",
            ""
        ]
        消息.extend(line)

    # 统计信息
    all_dds = [x['drawdown'] for x in analysis_results]
    消息.append("---")
    消息.append("💡 **全样本概览**")
    消息.append(f"▫️ 样本总数: `{len(analysis_results)}` 只")
    消息.append(f"▫️ 平均回撤: `{statistics.mean(all_dds):.2f}%` ")
    消息.append(f"▫️ 中位数: `{statistics.median(all_dds):.2f}%` ")

    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n--- 预览模式 ---")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": 文本, 
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(URL, json=payload, timeout=30)
        if r.status_code == 200:
            print("✅ 报告发送成功")
        else:
            print(f"❌ 发送失败: {r.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

if __name__ == "__main__":
    report_content = 综合分析报告()
    推送到TG(report_content)
