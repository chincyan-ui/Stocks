import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz
import time

# ================= 配置环境 =================
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
AV_KEY = os.getenv('ALPHAVANTAGE_API_KEY')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED)"""
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        recent_df = df.dropna()
        if len(recent_df) < 2: return None, None, []
        oas_list = recent_df.iloc[-7:, 0].tolist()
        return oas_list[-1], oas_list[-1] - oas_list[-2], oas_list
    except:
        return None, None, []

def get_qqq_stats():
    """获取QQQ行情及回撤"""
    try:
        ticker = yf.Ticker("QQQ")
        df = ticker.history(period="2y", auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        ath = df['Close'].max()
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        return {
            "close": float(curr['Close']),
            "change": float((curr['Close'] - prev['Close']) / prev['Close'] * 100),
            "drawdown": float((curr['Close'] / ath - 1) * 100),
            "ath": float(ath)
        }
    except:
        return None

def get_us_active_av():
    """获取美股成交金额排行 (按 Price * Volume 重新排序)"""
    if not AV_KEY:
        return []
    
    url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={AV_KEY}'
    
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=20)
            data = r.json()
            
            if "Note" in data or "Information" in data:
                time.sleep(20)
                continue
                
            raw_active = data.get('most_actively_traded', [])
            if not raw_active:
                return []
            
            # 核心逻辑：计算成交金额并重新排序
            processed_list = []
            for stock in raw_active:
                try:
                    price = float(stock.get('price', 0))
                    volume = float(stock.get('volume', 0))
                    # 成交金额 = 价格 * 成交量
                    turnover = price * volume
                    
                    processed_list.append({
                        "symbol": stock.get('ticker'),
                        "price": price,
                        "change": float(stock.get('change_percentage', "0").strip('%')),
                        "turnover": turnover
                    })
                except:
                    continue
            
            # 按成交金额（turnover）降序排列，取前三
            top_3_by_amount = sorted(processed_list, key=lambda x: x['turnover'], reverse=True)[:3]
            return top_3_by_amount
            
        except Exception as e:
            print(f"Alpha Vantage 请求异常: {e}")
            time.sleep(5)
    return []

def format_amount(amount):
    """格式化成交金额显示 (亿元/百万)"""
    if amount >= 1e9:
        return f"${amount/1e9:.2f}B"
    elif amount >= 1e6:
        return f"${amount/1e6:.1f}M"
    return f"${amount:.0f}"

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=20)

def main():
    tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M')

    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    active_stocks = get_us_active_av()
    
    msg = f"📊 *美股收盘复盘 (成交金额排行版)*\n"
    msg += f"时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        dd_icon = "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"
        
    if oas:
        msg += f"🏛️ *信用利差 (OAS)*: `{oas:.2f}%` (`{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{'→'.join([f'{x:.2f}' for x in oas_list[-5:]])}`\n\n"

    if active_stocks:
        msg += f"🔥 *美股成交金额 Top 3*\n"
        for i, s in enumerate(active_stocks, 1):
            amount_str = format_amount(s['turnover'])
            msg += f"{i}. `{s['symbol']}` | `${s['price']:.2f}` | `{s['change']:+.2f}%` | `{amount_str}`\n"
    else:
        msg += f"⚠️ *美股成交榜单抓取失败*\n"

    msg += "--------------------------------\n"
    if qqq and oas:
        status = "🚀 *策略：强趋势*" if qqq['drawdown'] > -3 and oas < 4.0 else "⚠️ *策略：防范回调*" if qqq['drawdown'] < -10 or oas > 5.0 else "⚖️ *策略：中性震荡*"
        msg += f"💡 {status}"

    send_msg(msg)

if __name__ == "__main__":
    main()
