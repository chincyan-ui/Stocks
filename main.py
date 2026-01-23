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
AV_KEY = os.getenv('ALPHAVANTAGE_API_KEY') # Alpha Vantage API Key

def get_oas_data():
    """获取美银美林高收益债利差 (FRED)"""
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        recent_df = df.dropna()
        oas_list = recent_df.iloc[-7:, 0].tolist()
        return oas_list[-1], oas_list[-1] - oas_list[-2], oas_list
    except:
        return None, None, []

def get_qqq_stats():
    """获取QQQ行情及回撤"""
    try:
        ticker = yf.Ticker("QQQ")
        df = ticker.history(period="2y", auto_adjust=True)
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
    """使用 Alpha Vantage 获取最准的美股成交额排行"""
    if not AV_KEY:
        print("未配置 Alpha Vantage Key，跳过获取")
        return []
    
    url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={AV_KEY}'
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        # Alpha Vantage 返回的数据包含 most_actively_traded
        # 这是全美市场基于当日成交量和成交额汇总的结果
        most_active = data.get('most_actively_traded', [])
        
        results = []
        for stock in most_active[:3]: # 取前三名
            results.append({
                "symbol": stock.get('ticker'),
                "price": float(stock.get('price', 0)),
                "change": float(stock.get('change_percentage', "0").replace('%', '')),
                "volume": format_volume(stock.get('volume', 0))
            })
        return results
    except Exception as e:
        print(f"Alpha Vantage 获取失败: {e}")
        return []

def format_volume(vol_str):
    """格式化成交量显示"""
    try:
        vol = float(vol_str)
        if vol >= 1e6: return f"{vol/1e6:.1f}M"
        return str(vol)
    except:
        return vol_str

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)

def main():
    tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M')

    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    active_stocks = get_us_active_av() # 使用新的 AV 接口
    
    msg = f"📊 *美股收盘复盘 (Alpha Vantage 数据源)*\n"
    msg += f"时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        dd_icon = "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} 回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"
        
    if oas:
        msg += f"🏛️ *利差 (OAS)*: `{oas:.2f}%` (`{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{'→'.join([f'{x:.2f}' for x in oas_list[-5:]])}`\n\n"

    if active_stocks:
        msg += f"🔥 *成交额巅峰排行 (Top 3)*\n"
        for i, s in enumerate(active_stocks, 1):
            msg += f"{i}. `{s['symbol']}` | `${s['price']:.2f}` | `{s['change']:+.2f}%` (Vol: `{s['volume']}`)\n"
    
    msg += "--------------------------------\n"
    msg += "💡 _Alpha Vantage 提供综合全美交易所成交统计_"
    
    send_msg(msg)

if __name__ == "__main__":
    main()
