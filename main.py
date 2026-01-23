import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz

# ================= 配置环境 =================
# 请在 GitHub Secrets 中设置 TELEGRAM_TOKEN 和 TELEGRAM_CHAT_ID
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED数据源)"""
    try:
        # 获取最近30天数据以确保剔除周末后仍有足够样本
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        if df.empty: return None, None, []
        
        recent_df = df.dropna()
        if len(recent_df) < 2: return None, None, []
            
        # 取最后7个交易日的趋势
        oas_list = recent_df.iloc[-7:, 0].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS数据抓取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取 QQQ 行情及距历史最高点(ATH)的回撤"""
    try:
        ticker = yf.Ticker("QQQ")
        # 获取2年数据计算 ATH
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
        print(f"QQQ数据抓取失败: {e}")
        return None

def get_us_most_active():
    """使用 yfinance Screener 动态获取全美股成交最活跃的前3只股票"""
    try:
        s = yf.Screener()
        s.lookup('most_active')
        quotes = s.response.get('quotes', [])[:3]
        return [{"symbol": q.get('symbol'), "price": q.get('regularMarketPrice'), "change": q.get('regularMarketChangePercent')} for q in quotes]
    except Exception as e:
        print(f"活跃股票获取失败: {e}")
        return []

def send_msg(text):
    """发送 Markdown 格式的 Telegram 消息"""
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
        print(f"发送消息失败: {e}")

def main():
    # 设置时区为北京时间
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')

    # 1. 数据采集
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    active_stocks = get_us_most_active()
    
    # 2. 构建消息模板
    msg = f"📊 *美股市场收盘复盘报告*\n"
    msg += f"更新时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    
    # 指数板块
    if qqq:
        dd_icon = "🔥" if qqq['drawdown'] > -3 else "🟢" if qqq['drawdown'] > -10 else "🔴"
        msg += f"🔹 *QQQ (纳指100)*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"{dd_icon} *距历史高点回撤: `{qqq['drawdown']:.2f}%`*\n"
        msg += f"  (ATH: `{qqq['ath']:.2f}`)\n\n"
        
    # 宏观利差板块
    if oas:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)\n"
        msg += f"趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    # 美股成交额榜单
    if active_stocks:
        msg += f"🔥 *今日全美股成交最活跃 (Top 3)*\n"
        for i, s in enumerate(active_stocks, 1):
            msg += f"{i}. `{s['symbol']}` | `${s['price']:.2f}` | `{s['change']:+.2f}%`\n"
        msg += "\n"

    msg += f"--------------------------------\n"
    
    # 综合策略判定 (逻辑来自你第一次的代码)
    if qqq and oas:
        if qqq['drawdown'] > -3 and oas < 4.0:
            status = "🚀 *策略：多头占优，顺势而为*"
        elif qqq['drawdown'] < -10 or oas > 5.0:
            status = "⚠️ *策略：防范结构性回调风险*"
        else:
            status = "⚖️ *策略：震荡整理，保持中性*"
        msg += f"💡 {status}"

    send_msg(msg)

if __name__ == "__main__":
    main()
