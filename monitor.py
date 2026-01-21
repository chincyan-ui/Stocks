import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_FILE = "last_list.txt"

def get_oas_data():
    """获取美银美林高收益债利差及其最近7个交易日趋势"""
    try:
        # 获取足够的数据以确保覆盖7个交易日
        start = datetime.datetime.now() - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, datetime.datetime.now())
        if df.empty: return None, None, []
        
        recent_df = df.tail(7)
        oas_list = recent_df["BAMLH0A0HYM2"].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS数据获取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取QQQ当日的最高、最低价及涨跌幅"""
    try:
        # 下载最近2天数据以确保包含最新完整交易日
        qqq = yf.download("QQQ", period="2d", progress=False)
        if isinstance(qqq.columns, pd.MultiIndex):
            qqq.columns = qqq.columns.get_level_values(0)
            
        latest_data = qqq.iloc[-1]
        high = latest_data['High']
        low = latest_data['Low']
        close = latest_data['Close']
        open_p = latest_data['Open']
        change_pct = (close - open_p) / open_p * 100
        
        return {
            "high": high,
            "low": low,
            "close": close,
            "change": change_pct
        }
    except Exception as e:
        print(f"QQQ数据获取失败: {e}")
        return None

def get_qualified_list():
    """监控池扫描：250日成交额 > 10亿 且 站上MA250"""
    tickers = ["SOXL", "NVDA", "AMD", "TSM", "AVGO", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]
    qualified = []
    threshold = 1e9
    
    for s in tickers:
        try:
            df = yf.download(s, period="300d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            avg_amt = (df['Close'] * df['Volume']).tail(250).mean()
            ma250 = df['Close'].rolling(window=250).mean().iloc[-1]
            current_price = df['Close'].iloc[-1]
            
            if avg_amt > threshold and current_price > ma250:
                qualified.append(s)
        except: continue
    return set(qualified)

def main():
    # 1. 获取宏观数据
    oas, oas_change, oas_list = get_oas_data()
    oas_status = "🟢 风险低" if oas and oas < 5.0 else ("🟡 风险抬升" if oas and oas < 6.5 else "🔴 衰退警报")
    
    # 2. 获取 QQQ 数据
    qqq = get_qqq_stats()
    
    # 3. 获取名单变动
    current_set = get_qualified_list()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_list = set(line.strip() for line in f if line.strip())
    else:
        last_list = set()

    added = current_set - last_list
    removed = last_list - current_set
    stayed = sorted(list(current_set & last_list))

    # 4. 构造 Markdown 报告
    msg = f"📊 *美股量化复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    # QQQ 板块
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"最高: `{qqq['high']:.2f}`\n"
        msg += f"最低: `{qqq['low']:.2f}`\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n\n"

    # 宏观板块
    if oas:
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n"
        msg += f"评估: {oas_status}\n\n"

    # 变动板块
    msg += f"🚀 *量能+趋势双强榜*\n"
    if added:
        for s in sorted(added): msg += f"➕ *新晋:* `{s}`\n"
    if removed:
        for s in sorted(removed): msg += f"➖ *掉出:* ~{s}~\n"
    
    if stayed:
        msg += f"✅ *在榜:* `{', '.join(stayed)}`"
    
    msg += f"\n--------------------------------\n"
    
    # 策略建议
    suggestion = "🚀 *策略：积极持有*" if oas and oas < 5.0 and "SOXL" in current_set else "⚠️ *策略：防守避险*"
    msg += f"💡 {suggestion}"

    # 5. 发送并保存
    send_msg(msg)
    with open(DB_FILE, "w") as f:
        f.write("\n".join(current_set))

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print(text)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
