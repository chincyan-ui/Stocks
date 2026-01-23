import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz

# ================= 配置环境 =================
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED)"""
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        if df.empty: return None, None, []
        recent_df = df.dropna()
        if len(recent_df) < 2: return None, None, []
        oas_list = recent_df.iloc[-7:, 0].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS获取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取QQQ行情及回撤"""
    try:
        ticker = yf.Ticker("QQQ")
        df = ticker.history(period="2y", auto_adjust=True) 
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        ath = df['Close'].max()
        current_close = curr['Close']
        drawdown = (current_close / ath - 1) * 100
        return {
            "close": float(current_close),
            "change": float((current_close - prev['Close']) / prev['Close'] * 100),
            "ath": float(ath),
            "drawdown": float(drawdown)
        }
    except:
        return None

def get_us_most_active():
    """获取美股成交额前3 (动态筛选 + 核心名单降级)"""
    # 方案 A: 动态 Screener
    try:
        s = yf.Screener()
        s.lookup('most_active')
        quotes = s.response.get('quotes', [])
        if quotes:
            return [{"symbol": q.get('symbol'), "price": q.get('regularMarketPrice'), "change": q.get('regularMarketChangePercent')} for q in quotes[:3]]
    except Exception as e:
        print(f"Screener 接口失效: {e}")

    # 方案 B: 降级方案 - 手动计算核心权重股成交额排序
    print("启动降级方案获取成交排行...")
    core_stocks = ["TSLA", "NVDA", "AAPL", "AMD", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "SMCI"]
    try:
        # 一次性下载最新数据
        data = yf.download(core_stocks, period="1d", group_by='ticker', progress=False)
        rank_list = []
        for ticker in core_stocks:
            ticker_data = data[ticker] if len(core_stocks) > 1 else data
            if ticker_data.empty: continue
            
            close = ticker_data['Close'].iloc[-1]
            volume = ticker_data['Volume'].iloc[-1]
            # 成交额估算 = 收盘价 * 成交量
            turnover = close * volume
            change = (close - ticker_data['Open'].iloc[-1]) / ticker_data['Open'].iloc[-1] * 100
            
            rank_list.append({
                "symbol": ticker,
                "price": float(close),
                "change": float(change),
                "turnover": turnover
            })
        
        # 按成交额降序
        top_3 = sorted(rank_list, key=lambda x: x['turnover'], reverse=True)[:3]
        return top_3
    except Exception as e:
        print(f"降级方案也失败: {e}")
        return []

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print(text); return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=20)
    except:
        pass

def main():
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')

    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    active_stocks = get_us_most_active()
    
    msg = f"📊 *美股收盘复盘报告*\n更新: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        dd_icon = "🔥" if qqq['drawdown'] > -3 else "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} 回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.2f}`)\n\n"
        
    if oas:
        trend = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *信用利差 (OAS)*\n最新: `{oas:.2f}%` ({trend} `{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    if active_stocks:
        msg += f"🔥 *美股成交额 Top 3*\n"
        for i, s in enumerate(active_stocks, 1):
            msg += f"{i}. `{s['symbol']}` | `${s['price']:.2f}` | `{s['change']:+.2f}%`\n"
    else:
        msg += f"⚠️ *美股成交额数据抓取异常*\n"

    msg += f"--------------------------------\n"
    if qqq and oas:
        status = "🚀 *策略：强趋势*" if qqq['drawdown'] > -3 and oas < 4.0 else "⚠️ *策略：防范风险*" if qqq['drawdown'] < -10 or oas > 5.0 else "⚖️ *策略：中性震荡*"
        msg += f"💡 {status}"

    send_msg(msg)

if __name__ == "__main__":
    main()
