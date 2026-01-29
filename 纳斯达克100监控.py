import yfinance as yf
import pandas as pd
import requests
import os
import statistics
from datetime import datetime

# 1. 核心标的列表 (37 只)
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
    available_dates = data.index
    if target_date not in available_dates:
        valid_dates = available_dates[available_dates <= target_date]
        if valid_dates.empty: return None
        target_date = valid_dates[-1]

    dds = []
    for ticker in TICKERS:
        try:
            hist = data[ticker].loc[:target_date].dropna()
            if len(hist) < 2: continue
            ath = hist['High'].max()
            close_on_day = hist['Close'].iloc[-1]
            dds.append((close_on_day - ath) / ath * 100)
        except: continue
    
    if dds:
        return {"date": target_date.strftime('%Y-%m-%d'), "avg": statistics.mean(dds), "med": statistics.median(dds)}
    return None

def 综合分析报告():
    print(f"🚀 开始全量深度扫描 (按回撤排序)...")
    
    try:
        # 下载 2020 年至今的前复权数据
        data = yf.download(TICKERS, start="2020-01-01", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 无法获取行情数据。"

    # --- A. 计算历史特定日期基准 ---
    stats_0407 = get_stats_on_date(data, "2025-04-07")
    stats_1029 = get_stats_on_date(data, "2025-10-29")

    # --- B. 计算所有标的实时回撤背景 ---
    full_results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].dropna()
            if df.empty: continue
            
            # 找到前复权最高价及其发生的日期
            ath_price = df['High'].max()
            ath_date = df['High'].idxmax().strftime('%Y-%m-%d')
            curr_price = df['Close'].iloc[-1]
            drawdown = (curr_price - ath_price) / ath_price * 100
            
            full_results.append({
                "symbol": ticker,
                "current": curr_price,
                "ath_price": ath_price,
                "ath_date": ath_date,
                "drawdown": drawdown
            })
        except: continue

    # --- C. 按回撤幅度从大到小排序 ---
    full_results.sort(key=lambda x: x['drawdown'])
    all_dds = [x['drawdown'] for x in full_results]

    # --- D. 构建长消息文本 ---
    消息 = ["📊 **全标的深度回撤清单 (按幅度排序)**", "---"]
    
    # 1. 历史基准对比
    消息.append("📅 **2025 历史基准对比**")
    for stat in [stats_0407, stats_1029]:
        if stat:
            消息.append(f"`{stat['date']}`: 平均 `{stat['avg']:.1f}%` | 中位 `{stat['med']:.1f}%`")
    消息.append("---")

    # 2. 全量列表详情
    消息.append("🔍 **各股回撤背景详述**")
    for i, item in enumerate(full_results, 1):
        # 图标逻辑：深蹲程度
        icon = "🆘" if item['drawdown'] <= -50 else "🚨" if item['drawdown'] <= -30 else "📉" if item['drawdown'] <= -15 else "▫️"
        
        detail = [
            f"{i}. {icon} **{item['symbol']}**: `{item['drawdown']:.2f}%`",
            f"   现价: `{item['current']:.2f}`",
            f"   历史高点: `{item['ath_price']:.2f}` ({item['ath_date']})",
            ""
        ]
        消息.extend(detail)

    # 3. 统计总结
    消息.append("---")
    消息.append(f"💡 **整体统计 (37只标的)**")
    消息.append(f"▫️ 平均回撤: **{statistics.mean(all_dds):.2f}%**")
    消息.append(f"▫️ 中位回撤: **{statistics.median(all_dds):.2f}%**")

    return "\n".join(消息)

def 推送到TG(文本):
    if not TOKEN or not CHAT_ID:
        print("\n--- 预览模式 (环境变量未配置) ---")
        print(文本)
        return

    URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # 自动切分：由于 37 只股票详情非常长，必须按 4000 字符切分发送
    MAX_CHAR = 4000
    if len(文本) > MAX_CHAR:
        parts = []
        # 按行切分，防止切断 Markdown 语法
        lines = 文本.split('\n')
        current_part = ""
        for line in lines:
            if len(current_part) + len(line) + 1 < MAX_CHAR:
                current_part += line + '\n'
            else:
                parts.append(current_part)
                current_part = line + '\n'
        parts.append(current_part)
    else:
        parts = [文本]

    for i, part in enumerate(parts):
        header = f"*(Part {i+1}/{len(parts)})*\n" if len(parts) > 1 else ""
        payload = {
            "chat_id": CHAT_ID, 
            "text": header + part, 
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(URL, json=payload, timeout=30)
            if r.status_code != 200:
                print(f"❌ 第 {i+1} 部分推送失败: {r.text}")
        except Exception as e:
            print(f"❌ 网络异常: {e}")

if __name__ == "__main__":
    report_content = 综合分析报告()
    推送到TG(report_content)
