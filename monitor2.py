import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd

# 配置环境
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_data():
    """获取美银美林高收益债利差 (FRED)"""
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=15)
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        if df.empty: return None, None, []
        
        recent_df = df.dropna()
        if len(recent_df) < 2: return None, None, []
            
        oas_list = recent_df.iloc[-7:, 0].tolist()
        latest = oas_list[-1]
        prev = oas_list[-2]
        return latest, latest - prev, oas_list
    except Exception as e:
        print(f"OAS数据抓取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取QQQ行情及历史最高点回撤"""
    try:
        ticker = yf.Ticker("QQQ")
        # 修改点：使用 period="max" 获取上市至今的所有历史数据
        df = ticker.history(period="max") 
        
        if df.empty: return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 计算历史最高点 (ATH)
        # 注意：yf 提供的历史数据已根据分红拆股调整过，计算回撤是准确的
        ath = df['Close'].max()
        current_close = curr['Close']
        drawdown = (current_close / ath - 1) * 100
        
        return {
            "high": float(curr['High']),
            "low": float(curr['Low']),
            "close": float(current_close),
            "change": float((current_close - prev['Close']) / prev['Close'] * 100),
            "ath": float(ath),
            "drawdown": float(drawdown)
        }
    except Exception as e:
        print(f"QQQ数据抓取失败: {e}")
        return None

def send_msg(text):
    if not TOKEN or not CHAT_ID: 
        print(f"未配置 Telegram，预览内容:\n{text}")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(f"发送消息失败: {e}")

def main():
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    msg = f"📊 *美股宏观数据复盘 ({date_str})*\n"
    msg += f"--------------------------------\n"
    
    if qqq:
        # 回撤颜色逻辑：针对历史最高点的回撤通常较小，超过 -10% 就属于重要调整
        if qqq['drawdown'] > -3:
            dd_icon = "🔥" # 极强，接近历史新高
        elif qqq['drawdown'] > -10:
            dd_icon = "🟢" # 正常回调
        elif qqq['drawdown'] > -20:
            dd_icon = "🟡" # 技术性调整
        else:
            dd_icon = "🔴" # 熊市区间
        
        msg += f"🔹 *QQQ 指数行情*\n"
        msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
        msg += f"高/低: `{qqq['high']:.2f}` / `{qqq['low']:.2f}`\n"
        msg += f"{dd_icon} *距历史最高点 (ATH): `{qqq['drawdown']:.2f}%`*\n"
        msg += f"  (历史顶点: `{qqq['ath']:.2f}`)\n\n"
        
    if oas:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *宏观信用利差 (OAS)*\n"
        msg += f"最新: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)\n"
        msg += f"7日趋势: `{' → '.join([f'{x:.2f}' for x in oas_list])}`\n\n"

    msg += f"--------------------------------\n"
    
    # 综合判定
    if qqq and oas:
        # 如果回撤在3%以内且利差走低，说明处于极强上升通道
        if qqq['drawdown'] > -3 and oas < 4.0:
            status = "🚀 *策略：处于强趋势，顺势而为*"
        elif qqq['drawdown'] < -10 or oas > 5.0:
            status = "⚠️ *策略：警惕结构性回调风险*"
        else:
            status = "⚖️ *策略：震荡行情，中性持仓*"
        msg += f"💡 {status}"

    send_msg(msg)

if __name__ == "__main__":
    main()
