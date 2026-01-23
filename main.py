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

def get_accurate_top_traded():
    """综合名单补全法：动态榜单 + 核心吸金权重股"""
    # 1. 初始候选池（美股历史上成交额最稳的12只巨头）
    candidate_pool = {"NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "META", "GOOGL", "NFLX", "AVGO", "SMCI", "INTC"}
    
    # 2. 尝试从 Alpha Vantage 获取今日动态活跃股补充进池子
    if AV_KEY:
        url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={AV_KEY}'
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            active_list = data.get('most_actively_traded', [])
            for item in active_list[:10]:
                candidate_pool.add(item.get('ticker'))
        except:
            print("AV接口调用失败，仅使用核心池排序")

    # 3. 使用 yfinance 批量获取候选池的精准盘后/收盘数据
    results = []
    try:
        # yfinance 的 download 接口获取数据比单个 Ticker 更快
        tickers_str = " ".join(candidate_pool)
        data = yf.download(tickers_str, period="1d", group_by='ticker', progress=False)
        
        for ticker in candidate_pool:
            try:
                # 处理单只股票返回格式差异
                df = data[ticker] if len(candidate_pool) > 1 else data
                if df.empty: continue
                
                # 使用典型价格(Typical Price)计算成交额以接近富途的VWAP口径
                # 公式: (High + Low + Close) / 3 * Volume
                tp = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1]) / 3
                vol = df['Volume'].iloc[-1]
                turnover = tp * vol
                
                results.append({
                    "symbol": ticker,
                    "price": float(df['Close'].iloc[-1]),
                    "change": float((df['Close'].iloc[-1] / df['Open'].iloc[-1] - 1) * 100),
                    "turnover": turnover
                })
            except:
                continue
    except Exception as e:
        print(f"yfinance 批量获取失败: {e}")

    # 4. 按成交金额降序排列
    final_top_3 = sorted(results, key=lambda x: x['turnover'], reverse=True)[:3]
    return final_top_3

def format_amount(amount):
    """格式化为美元显示"""
    if amount >= 1e9: return f"${amount/1e9:.2f}B"
    return f"${amount/1e6:.1f}M"

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=20)

def main():
    tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M')

    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    # 核心算法更新
    active_stocks = get_accurate_top_traded()
    
    msg = f"📊 *美股收盘复盘 (吸金榜精修版)*\n时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        dd_icon = "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"
        
    if oas:
        msg += f"🏛️ *利差 (OAS)*: `{oas:.2f}%` (`{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{'→'.join([f'{x:.2f}' for x in oas_list[-5:]])}`\n\n"

    if active_stocks:
        msg += f"🔥 *美股成交金额 Top 3*\n"
        for i, s in enumerate(active_stocks, 1):
            amount_str = format_amount(s['turnover'])
            msg += f"{i}. `{s['symbol']}` | `${s['price']:.2f}` | `{s['change']:+.2f}%` | `{amount_str}`\n"
    
    msg += "--------------------------------\n"
    msg += "💡 _注：采用典型价格(Typical Price)估算成交额_"
    
    send_msg(msg)

if __name__ == "__main__":
    main()
