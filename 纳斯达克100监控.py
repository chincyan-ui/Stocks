import yfinance as yf
import pandas as pd
import requests
import os
import statistics
from datetime import datetime

# 1. 核心标的列表 (增加了 TSLA，共 37 只)
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "AVGO", "COST", 
    "PEP", "ADBE", "CSCO", "CMCSA", "NFLX", "INTC", "QCOM", "AMGN", 
    "TXN", "HON", "INTU", "AMAT", "SBUX", "ISRG", "GILD", "MDLZ", 
    "BKNG", "ADI", "VRTX", "REGN", "LRCX", "ADP", "MU", "PYPL", 
    "SNPS", "CDNS", "CTSH", "ASML", "TSLA"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_stats_on_date(data, target_date_str):
    """计算特定日期的回撤平均值和中位数"""
    target_date = pd.Timestamp(target_date_str)
    
    # 寻找数据中最近的有效交易日
    available_dates = data.index
    if target_date not in available_dates:
        valid_dates = available_dates[available_dates <= target_date]
        if valid_dates.empty:
            return None
        target_date = valid_dates[-1]

    dds = []
    for ticker in TICKERS:
        try:
            # 获取截至目标日期（含）的所有历史数据
            hist = data[ticker].loc[:target_date].dropna()
            if len(hist) < 2: continue
            
            ath = hist['High'].max()
            close_on_day = hist['Close'].iloc[-1]
            dd = (close_on_day - ath) / ath * 100
            dds.append(dd)
        except:
            continue
    
    if dds:
        return {
            "date": target_date.strftime('%Y-%m-%d'),
            "avg": statistics.mean(dds),
            "med": statistics.median(dds)
        }
    return None

def 综合分析报告():
    print(f"🚀 开始深度扫描 (含 TSLA 及 2025 特定日期对比)...")
    
    # --- 1. 下载行情数据 (前复权) ---
    try:
        # 下载自2020年起的数据
        data = yf.download(TICKERS, start="2020-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 无法获取行情数据。"

    # --- 2. 计算历史特定日期数据 ---
    stats_0407 = get_stats_on_date(data, "2025-04-07")
    stats_1029 = get_stats_on_date(data, "2025-10-29")

    # --- 3. 计算当前实时数据及 Top 10 ---
    analysis_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            
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

    # 按回撤幅度从大到小排序
    analysis_results.sort(key=lambda x: x['drawdown'])
    all_dds = [x['drawdown'] for x in analysis_results]

    # --- 4. 构建消息文本 ---
    消息 = ["📊 **核心标的回撤深度报告**", "---"]
    
    # 历史回顾
    消息.append("📅 **历史关键点回顾 (2025)**")
    for stat in [stats_0407, stats_1029]:
        if stat:
            消息.append(f"📍 日期: `{stat['date']}`")
            消息.append(f"▫️ 平均回撤: `{stat['avg']:.2f}%` | 中位数: `{stat['med']:.2f}%`")
    消息.append("---")

    # 实时深蹲 Top 10
    消息.append("🔥 **当前回撤 Top 10 (深蹲详情)**")
    top_10 = analysis_results[:10]
    for i, item in enumerate(top_10, 1):
        # 警示图标
        icon = "🆘" if item['drawdown'] <= -40 else "🚨" if item['drawdown'] <= -20 else "📉"
        # 针对 TSLA 做个小标记（可选）
        tsla_tag = " [重点]" if item['symbol'] == "TSLA" else ""
        
        消息.append(f"{i}. {icon} **{item['symbol']}**{tsla_tag}")
        消息.append(f"   回撤: `{item['drawdown']:.2f}%` (ATH: `{item['ath_price']:.2f}` on `{item['ath_date']}`)")

    # 整体统计
    消息.append("---")
    消息.append(f"💡 **当前实时概览 (共 {len(TICKERS)} 只)**")
    if all_dds:
        消息.append(f"▫️ 平均回撤: **{statistics.mean(all_dds):.2f}%**")
        消息.append(f"▫️ 中位数回撤: **{statistics.median(all_dds):.2f}%**")

    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n--- 预览模式 ---")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": 文本, "parse_mode": "Markdown"}
    try:
        r = requests.post(URL, json=payload, timeout=30)
        if r.status_code == 200:
            print("✅ 包含 TSLA 的深度报告已发送")
        else:
            print(f"❌ 发送失败: {r.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

if __name__ == "__main__":
    report_content = 综合分析报告()
    推送到TG(report_content)
