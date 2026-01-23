import yfinance as yf
import akshare as ak
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz

# ================= 配置环境 =================
# 在 GitHub Secrets 中设置这些变量
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED数据源)"""
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
    """获取 QQQ 指数行情及距历史高点回撤"""
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
    except Exception as e:
        print(f"QQQ获取失败: {e}")
        return None

def get_us_active():
    """获取美股全市场成交额最活跃的前3只 (yf Screener)"""
    try:
        s = yf.Screener()
        s.lookup('most_active')
        quotes = s.response['quotes'][:3]
        return [{"symbol": q['symbol'], "price": q['regularMarketPrice'], "change": q['regularMarketChangePercent']} for q in quotes]
    except:
        return []

def get_china_active():
    """使用 AkShare 获取 A 股成交额前3"""
    try:
        df = ak.stock_zh_a_spot_em()
        df_top = df.sort_values(by="成交额", ascending=False).head(3)
        results = []
        for _, row in df_top.iterrows():
            results.append({
                "name": row['名称'],
                "price": row['最新价'],
                "change": row['涨跌幅'],
                "turnover": row['成交额'] / 10**8
            })
        return results
    except:
        return []

def get_hk_active():
    """使用 AkShare 获取港股成交额前3"""
    try:
        df = ak.stock_hk_spot_em()
        df_top = df.sort_values(by="成交额", ascending=False).head(3)
        results = []
        for _, row in df_top.iterrows():
            results.append({
                "name": row['名称'],
                "price": row['最新价'],
                "change": row['涨跌幅'],
                "turnover": row['成交额'] / 10**8
            })
        return results
    except:
        return []

def get_japan_active():
    """获取日股成交额最活跃的前3只"""
    try:
        s = yf.Screener()
        s.lookup('most_active_japan')
        quotes = s.response['quotes'][:3]
        return [{"symbol": q['symbol'], "price": q['regularMarketPrice'], "change": q['regularMarketChangePercent']} for q in quotes]
    except:
        return []

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print(f"--- 预览模式 ---\n{text}")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID, 
            "text": text, 
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }, timeout=20)
    except Exception as e:
        print(f"发送失败: {e}")

def main():
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')
    
    msg = f"🏁 *全球市场收盘复盘 ({date_str})*\n"
    msg += "--------------------------------\n"

    # 1. 宏观数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    if qqq:
        dd_icon = "🔥" if qqq['drawdown'] > -3 else "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"

    if oas:
        trend = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *高收益债利差 (OAS)*\n最新: `{oas:.2f}%` ({trend} `{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    msg += "🔥 *全市场成交额 Top 3*\n"
    
    # 2. 美股排行
    us = get_us_active()
    if us:
        msg += "🇺🇸 *美股:*\n"
        for s in us: msg += f" • `{s['symbol']}` | `{s['change']:+.2f}%` | `${s['price']:.1f}`\n"
    
    # 3. A 股排行
    cn = get_china_active()
    if cn:
        msg += "🇨🇳 *A 股:*\n"
        for s in cn: msg += f" • `{s['name']}` | `{s['change']:+.2f}%` | `{s['turnover']:.1f}亿`\n"

    # 4. 港股排行
    hk = get_hk_active()
    if hk:
        msg += "🇭🇰 *港股:*\n"
        for s in hk: msg += f" • `{s['name']}` | `{s['change']:+.2f}%` | `{s['turnover']:.1f}亿`\n"

    # 5. 日股排行
    jp = get_japan_active()
    if jp:
        msg += "🇯🇵 *日股:*\n"
        for s in jp: msg += f" • `{s['symbol']}` | `{s['change']:+.2f}%` | `{s['price']:.0f}¥`\n"

    msg += "--------------------------------\n"
    
    # 综合判定逻辑
    if qqq and oas:
        if qqq['drawdown'] > -5 and oas < 4.0:
            status = "🚀 *强趋势：市场风险偏好高*"
        elif oas > 5.0:
            status = "⚠️ *预警：流动性压力增大*"
        else:
            status = "⚖️ *中性：保持观察*"
        msg += f"💡 {status}"

    send_msg(msg)

if __name__ == "__main__":
    main()
