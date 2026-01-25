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
        recent_df = df.dropna()
        if recent_df.empty:
            return None, None, []
        oas_list = recent_df.iloc[-7:, 0].tolist()
        current_oas = float(oas_list[-1])
        prev_oas = float(oas_list[-2])
        change = current_oas - prev_oas
        return current_oas, change, oas_list
    except Exception as e:
        print(f"OAS 获取失败: {e}")
        return None, None, []

def get_qqq_stats():
    """获取 QQQ 行情及回撤数据"""
    try:
        ticker = yf.Ticker("QQQ")
        df = ticker.history(period="2y")
        if df.empty:
            return None
        ath = df['Close'].max()
        curr_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change_pct = (curr_price - prev_price) / prev_price * 100
        drawdown = (curr_price / ath - 1) * 100
        return {
            "close": float(curr_price),
            "change": float(change_pct),
            "drawdown": float(drawdown),
            "ath": float(ath)
        }
    except Exception as e:
        print(f"QQQ 获取失败: {e}")
        return None

def send_msg(text):
    """发送 Telegram 消息"""
    if not TOKEN or not CHAT_ID:
        print("错误: 未配置 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        print("消息发送成功")
    except Exception as e:
        print(f"消息发送失败: {e}")

def main():
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    if not qqq:
        print("未获取到当日交易数据，跳过推送。")
        return
    msg = f"📊 *美股收盘简报*\n时间: `{date_str}`\n"
    msg += f"--------------------------------\n"
    dd_val = qqq['drawdown']
    if dd_val > -5:
        dd_icon = "🟢" 
    elif dd_val > -15:
        dd_icon = "🟡"
    else:
        dd_icon = "🔴"
    msg += f"🔹 *QQQ (纳指100)*\n"
    msg += f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)\n"
    msg += f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n\n"
    if oas is not None:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg += f"🏛️ *信用利差 (OAS)*: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)\n"
        recent_trend = " → ".join([f"{x:.2f}" for x in oas_list[-5:]])
        msg += f"趋势: `{recent_trend}`\n"
    msg += "--------------------------------\n"
    msg += "💡 _提示：OAS 异常升高通常预示流动性收紧_"
    send_msg(msg)

if __name__ == "__main__":
    main()
