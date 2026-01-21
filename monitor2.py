import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

# 配置环境
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_FILE = "last_list.txt"

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
    except Exception as e:
        print(f"OAS数据获取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取QQQ当日行情(最高/最低/涨跌幅)"""
    try:
        qqq_ticker = yf.Ticker("QQQ")
        df = qqq_ticker.history(period="5d")
        if df.empty: return None

        # 核心修复：强制拍平多级索引
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.sort_index()

        current_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        high = df['High'].iloc[-1]
        low = df['Low'].iloc[-1]
        change_pct = (current_close - prev_close) / prev_close * 100

        return {
            "high": high, "low": low, "close": current_close, "change": change_pct
        }
    except Exception as e:
        print(f"QQQ获取失败: {e}")
        return None

def get_qualified_list():
    """监控池扫描：250日平均成交额 > 10亿 且 站上MA250"""
    tickers = ["SOXL", "NVDA", "AMD", "TSM", "AVGO", "MSFT", "AAPL", "GOOGL", "AMZN", "META"]
    qualified = []
    threshold = 1e9  # 10亿美元
    
    print("开始扫描名单...")
    for s in tickers:
        try:
            # 获取足够的数据量（约1年半）
            df = yf.download(s, period="400d", progress=False)
            
            # 核心修复 1：处理多级索引
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if len(df) < 250:
                print(f"跳过 {s}: 数据不足 250 天")
                continue
            
            # 核心修复 2：确保 Close 和 Volume 是数值型，并计算每日成交额
            df['Daily_Amt'] = df['Close'] * df['Volume']
            
            # 计算过去 250 个交易日的平均成交额（比 .all() 更稳健）
            avg_amt_250 = df['Daily_Amt'].tail(250).mean()
            
            # 计算 MA250
            ma250 = df['Close'].rolling(window=250).mean().iloc[-1]
            current_price = df['Close'].iloc[-1]
            
            # 判定条件：均量 > 10亿 且 价格 > 年线
            if avg_amt_250 > threshold and current_price > ma250:
                qualified.append(s)
                print(f"✅ {s} 入榜 (均量: {avg_amt_250/1e9:.2f}B)")
            else:
                print(f"❌ {s} 未达标 (均量: {avg_amt_250/1e9:.2f}B)")
        except Exception as e:
            print(f"扫描 {s} 出错: {e}")
            continue
            
    return set(qualified)

def main():
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    current_set = get_qualified_list()
    
    # 名单记录处理
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_list = set(line.strip() for line in f if line.strip())
    else:
        last_list = set()

    added = current_set - last_list
    removed = last_list - current_set
    stayed = sorted(list(current_set & last_list))

    # 构造 Markdown 报告
    msg = f"📊 *美股量化复盘 ({datetime.datetime.now().strftime('%Y-%m-%d')})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"最高: `{qqq['high']:.2f}` | 最低: `{qqq['low']:.2f}`\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n\n"

    if oas:
        oas_status = "🟢 风险低" if oas < 5.0 else ("🟡 风险抬升" if oas < 6.5 else "🔴 衰退警报")
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({oas_change:+.2f}%)\n"
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n"
        msg += f"评估: {oas_status}\n\n"

    msg += f"🚀 *250日/10亿/MA250 榜单*\n"
    if added:
        for s in sorted(added): msg += f"➕ *新晋:* `{s}`\n"
    if removed:
        for s in sorted(removed): msg += f"➖ *掉出:* ~{s}~\n"
    if stayed:
        msg += f"✅ *持续在榜:* `{', '.join(stayed)}`"
    if not current_set:
        msg += "⚪ *当前暂无符合条件的标的*"
    
    msg += f"\n--------------------------------\n"
    
    suggestion = "🚀 *策略：积极持有*" if oas and oas < 5.0 and "SOXL" in current_set else "⚠️ *策略：谨慎观望*"
    msg += f"💡 {suggestion}"

    send_msg(msg)
    with open(DB_FILE, "w") as f:
        f.write("\n".join(current_set))

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print(text)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    main()
