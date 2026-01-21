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

def get_oas_data():
    """获取美银美林高收益债利差 (FRED) 及其 7 日趋势"""
    try:
        # 抓取过去15天数据以确保剔除节假日后仍有7个交易日
        start = datetime.datetime.now() - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, datetime.datetime.now())
        if df.empty: return None, None, []
        
        # 准确提取最近 7 个交易日
        recent_df = df.dropna().tail(7)
        oas_list = recent_df["BAMLH0A0HYM2"].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS获取失败: {e}")
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
    threshold = 1e9 
    
    print("正在扫描当日成交额...")
    for s in tickers:
        try:
            # 下载最近1天的数据
            df = yf.download(s, period="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty: continue
            latest = df.iloc[-1]
            # 成交额 = 收盘价 * 成交量
            today_amt = latest['Close'] * latest['Volume']
            
            if today_amt > threshold:
                today_list.append(s)
                print(f"✅ {s} 达标: {today_amt/1e9:.2f}B")
        except: continue
    return set(today_list)

def main():
    # 1. 获取数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    today_set = get_today_billion_list()
    
    # 2. 处理 JSON 历史记录
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                history_data = json.load(f)
            except: history_data = {}
    else:
        history_data = {}

    # 3. 计算连续在榜逻辑
    new_data = {}
    repeat_list = [] # 存储 (股票名, 持续天数)
    
    for s in today_set:
        # 如果今天在榜，看看昨天在不在
        count = history_data.get(s, 0) + 1
        new_data[s] = count
        if count >= 2: # 只有重复出现（2天及以上）才加入显示名单
            repeat_list.append((s, count))

    # 按持续天数排序
    repeat_list.sort(key=lambda x: x[1], reverse=True)

    # 4. 构造 Markdown 报告
    msg = f"📊 *美股量化复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"高/低: `{qqq['high']:.2f}` / `{qqq['low']:.2f}`\n\n"

    if oas:
        oas_status = "🟢 风险低" if oas < 5.0 else ("🟡 风险抬升" if oas < 6.5 else "🔴 衰退警报")
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        # 修正点：这里显示全部 7 天趋势
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n"
        msg += f"风险评估: {oas_status}\n\n"

    msg += f"🔥 *资金持续活跃榜 (成交额 > 10亿)*\n"
    if repeat_list:
        for s, days in repeat_list:
            msg += f"💎 `{s}`：已连续达标 `{days}` 天\n"
    else:
        msg += f"⚪ 今日暂无持续活跃(重复入榜)标的\n"
        if today_set:
            msg += f"_(注：今日有 {len(today_set)} 只个股新入榜)_ \n"

    msg += f"\n--------------------------------\n"
    
    # 综合建议
    active_tickers = [s for s, d in repeat_list]
    suggestion = "🚀 *建议策略：积极持有*" if oas and oas < 5.0 and len(active_tickers) > 0 else "⚠️ *建议策略：谨慎观望*"
    msg += f"💡 {suggestion}"

    # 5. 发送并回写 JSON
    send_msg(msg)
    with open(DB_FILE, "w") as f:
        json.dump(new_data, f)

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
