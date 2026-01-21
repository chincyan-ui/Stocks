import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import json

# 配置环境
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_FILE = "last_list.json" 

def get_sp500_tickers():
    """实时从维基百科获取标普500成分股名单"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        table = pd.read_html(url)
        df = table[0]
        # 修正部分代码格式（如用 . 替换 -）
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        # 加入一些成交额极大的常用 ETF
        extra_tickers = ["QQQ", "SPY", "SOXL", "TQQQ", "SQQQ", "TSLL", "IWM"]
        return list(set(tickers + extra_tickers))
    except Exception as e:
        print(f"获取S&P 500名单失败: {e}")
        # 备选基础名单
        return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "LLY"]

def get_oas_data():
    """获取美银美林高收益债利差 (FRED) 及其 7 日趋势"""
    try:
        start = datetime.datetime.now() - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, datetime.datetime.now())
        if df.empty: return None, None, []
        recent_df = df.dropna().tail(7)
        oas_list = recent_df["BAMLH0A0HYM2"].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except:
        return None, None, []

def get_qqq_stats():
    """获取QQQ当日行情"""
    try:
        df = yf.Ticker("QQQ").history(period="5d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        curr, prev = df.iloc[-1], df.iloc[-2]
        return {
            "high": curr['High'], "low": curr['Low'], 
            "close": curr['Close'], "change": (curr['Close'] - prev['Close']) / prev['Close'] * 100
        }
    except:
        return None

def get_today_billion_list(ticker_list):
    """批量筛选当日成交额 > 10亿的股票"""
    today_list = []
    threshold = 1e9 
    
    print(f"正在扫描 {len(ticker_list)} 只股票的成交额...")
    # 批量下载当日数据以提高效率
    data = yf.download(ticker_list, period="1d", progress=False, group_by='ticker')
    
    for ticker in ticker_list:
        try:
            # 处理批量下载后的数据结构
            df = data[ticker] if len(ticker_list) > 1 else data
            if df.empty or 'Close' not in df: continue
            
            latest = df.iloc[-1]
            # 计算成交额 (估算值)
            amt = latest['Close'] * latest['Volume']
            
            if amt > threshold:
                today_list.append(ticker)
        except: continue
        
    print(f"扫描完成，共有 {len(today_list)} 只标的成交额超10亿。")
    return set(today_list)

def main():
    # 1. 获取标普500名单并扫描成交额
    all_tickers = get_sp500_tickers()
    today_set = get_today_billion_list(all_tickers)
    
    # 2. 获取其他宏观/指数数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    # 3. 处理历史记录 (JSON)
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try: history_data = json.load(f)
            except: history_data = {}
    else: history_data = {}

    # 4. 核心逻辑：计算连续在榜天数
    new_data = {}
    repeat_list = []
    
    for s in today_set:
        count = history_data.get(s, 0) + 1
        new_data[s] = count
        if count >= 2: # 至少连续2天出现
            repeat_list.append((s, count))

    # 按天数从大到小排序
    repeat_list.sort(key=lambda x: x[1], reverse=True)

    # 5. 构造报告内容
    msg = f"📊 *美股全市场量化复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"高/低: `{qqq['high']:.2f}` / `{qqq['low']:.2f}`\n\n"

    if oas:
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    msg += f"🔥 *资金持续活跃榜 (成交额 > 10亿)*\n"
    msg += f"范围: S&P500成分股 + 核心ETF\n"
    if repeat_list:
        # 只取前 15 名，避免消息太长
        for s, days in repeat_list[:15]:
            msg += f"💎 `{s}`：持续 `{days}` 天\n"
        if len(repeat_list) > 15:
            msg += f"...等共 `{len(repeat_list)}` 只标的\n"
    else:
        msg += f"⚪ 今日暂无持续活跃(重复入榜)标的\n"

    msg += f"\n--------------------------------\n"
    
    # 建议
    suggestion = "🚀 *策略：积极持有*" if oas and oas < 5.0 and len(repeat_list) > 0 else "⚠️ *策略：谨慎观望*"
    msg += f"💡 {suggestion}"

    # 6. 发送并保存
    send_msg(msg)
    with open(DB_FILE, "w") as f:
        json.dump(new_data, f)

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
