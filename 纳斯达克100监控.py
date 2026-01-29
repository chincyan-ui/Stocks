import yfinance as yf
import pandas as pd
import requests
import os
import statistics
from datetime import datetime

# ... (TICKERS 列表保持不变) ...

def format_market_cap(n):
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    elif n >= 1e9:
        return f"${n/1e9:.2f}B"
    return f"${n:,.0f}"

def 综合分析报告():
    print(f"🚀 开始深度分析...")
    
    # --- 1. 获取市值 ---
    mcap_list = []
    try:
        tickers_obj = yf.Tickers(TICKERS)
        for ticker in TICKERS:
            try:
                # 获取快照信息
                info = tickers_obj.tickers[ticker].fast_info
                mcap = info.get('market_cap', 0)
                if mcap and mcap > 0:
                    mcap_list.append({"symbol": ticker, "mcap": mcap, "mcap_str": format_market_cap(mcap)})
            except:
                continue
    except Exception as e:
        print(f"⚠️ 市值获取过程出现异常: {e}")

    # 排序并取前 60
    mcap_list.sort(key=lambda x: x['mcap'], reverse=True)
    top_60_data = mcap_list[:60]
    top_60_tickers = [x['symbol'] for x in top_60_data]

    # --- 2. 下载价格数据 ---
    try:
        # 下载最近两年的数据即可，减少负载
        data = yf.download(TICKERS, period="2y", auto_adjust=True, group_by='ticker', threads=True)
    except Exception as e:
        return f"❌ 数据下载失败: {e}"

    if data.empty:
        return "❌ 未下载到任何行情数据，请检查网络或 API。"

    # 计算当前回撤
    current_results = []
    for ticker in TICKERS:
        try:
            # 兼容单只股票和多只股票的 DataFrame 结构
            df = data[ticker].dropna() if len(TICKERS) > 1 else data.dropna()
            if df.empty or 'High' not in df.columns: continue
            
            ath = df['High'].max()
            curr = df['Close'].iloc[-1]
            dd = (curr - ath) / ath * 100
            current_results.append({"symbol": ticker, "dd": dd})
        except:
            continue

    dd_map = {x['symbol']: x['dd'] for x in current_results}

    # --- 3. 构建消息文本 ---
    消息 = ["📊 **纳指100权重股回撤深度报告**", "---"]
    
    if not top_60_data:
        消息.append("⚠️ 未能获取市值排行数据")
    else:
        消息.append(f"🔝 **市值排行 TOP 60 (及当前回撤)**")
        for i, item in enumerate(top_60_data, 1):
            ticker = item['symbol']
            mcap_val = item['mcap_str']
            drawdown = dd_map.get(ticker, 0)
            warn = "⚠️" if drawdown <= -20 else "▫️"
            消息.append(f"{i}. {warn} `{ticker:<5}`: **{mcap_val}** (DD: `{drawdown:.2f}%`)")
    
    消息.append("---")

    # --- 安全计算平均值 ---
    all_dds = [x['dd'] for x in current_results]
    top60_dds = [dd_map[t] for t in top_60_tickers if t in dd_map]
    
    消息.append("💡 **市场广度统计**")
    
    # 增加判断：如果列表为空，返回 "N/A"
    avg_all = f"{statistics.mean(all_dds):.2f}%" if all_dds else "N/A"
    med_all = f"{statistics.median(all_dds):.2f}%" if all_dds else "N/A"
    avg_top60 = f"{statistics.mean(top60_dds):.2f}%" if top60_dds else "N/A"

    消息.append(f"▫️ 全体平均回撤: `{avg_all}`")
    消息.append(f"▫️ **TOP 60 平均回撤**: `{avg_top60}`")
    消息.append(f"▫️ 全体中位数: `{med_all}`")
    
    return "\n".join(消息)

# ... (推送到TG 函数保持不变) ...
