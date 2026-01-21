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
DB_FILE = "last_list.json"  # 更改为JSON格式存储天数

def get_oas_data():
    """获取美银美林高收益债利差 (FRED) 及其 7 日趋势"""
    try:
        start = datetime.datetime.now() - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, datetime.datetime.now())
        if df.empty: return None, None, []
        recent_df = df.tail(7)
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
        df = df.sort_index()
        curr, prev = df.iloc[-1], df.iloc[-2]
        return {
            "high": curr['High'], "low": curr['Low'], 
            "close": curr['Close'], "change": (curr['Close'] - prev['Close']) / prev['Close'] * 100
        }
    except:
        return None

def get_today_billion_list():
    """筛选当日成交额 > 10亿的股票"""
    tickers = ["SOXL", "NVDA", "AMD", "TSM", "AVGO", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]
    today_list = []
    threshold = 1e9  # 10亿美元
    
    print("正在扫描成交额...")
    for s in tickers:
        try:
            # 取最近2天确保包含当日完整数据
            df = yf.download(s, period="2d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            latest = df.iloc[-1]
            # 计算当日成交额 = 当日收盘价 * 当日成交量
            today_amt = latest['Close'] * latest['Volume']
            
            if today_amt > threshold:
                today_list.append(s)
                print(f"✅ {s} 达标: {today_amt/1e9:.2f}B")
        except: continue
    return set(today_list)

def main():
    # 1. 获取基础数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    today_billion_set = get_today_billion_list()
    
    # 2. 读取历史天数记录
    # 格式: {"NVDA": 3, "AAPL": 1}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                history_data = json.load(f)
            except:
                history_data = {}
    else:
        history_data = {}

    # 3. 逻辑比对
    new_data = {}
    stayed_with_days = [] # 记录重复出现的股票及其天数
    
    for s in today_billion_set:
        if s in history_data:
            # 昨天的榜单里也有 -> 重复出现
            count = history_data[s] + 1
            new_data[s] = count
            stayed_with_days.append((s, count))
        else:
            # 昨天不在榜 -> 计为第1天，但不属于“重复出现”
            new_data[s] = 1

    # 按天数降序排序
    stayed_with_days.sort(key=lambda x: x[1], reverse=True)

    # 4. 构造报告
    msg = f"📊 *美股量化复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"高/低: `{qqq['high']:.2f}` / `{qqq['low']:.2f}`\n\n"

    if oas:
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%`趋势: `{'→'.join([f'{x:.1f}' for x in oas_list[-3:]])}`\n\n"

    msg += f"🔥 *持续活跃榜 (成交额 > 10亿)*\n"
    msg += f"备注：仅列出连续2日及以上达标的股票\n"
    
    if stayed_with_days:
        for s, days in stayed_with_days:
            msg += f"💎 `{s}`：已连续达标 `{days}` 天\n"
    else:
        msg += f"⚪ 今日暂无持续活跃标的\n"
        if today_billion_set:
            msg += f"_(注：今日有 {len(today_billion_set)} 只新入榜，需观察明日是否重复)_ \n"

    msg += f"\n--------------------------------\n"
    
    # 策略建议逻辑
    is_active = any(s == "SOXL" for s, d in stayed_with_days)
    suggestion = "🚀 *策略：积极持有*" if oas and oas < 5.0 and is_active else "⚠️ *策略：谨慎观望*"
    msg += f"💡 {suggestion}"

    # 5. 发送并保存新记录
    send_msg(msg)
    with open(DB_FILE, "w") as f:
        json.dump(new_data, f)

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
