import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os
import pandas as pd
import pytz
from typing import Optional, Tuple

# ================= 配置环境 =================
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_oas_history_stats(df: pd.DataFrame) -> str:
    """计算 2010-2026 OAS 的历年最高/最低点及日期"""
    stats_msg = []
    df.index = pd.to_datetime(df.index)
    
    # 修改：循环范围调整为 2010 到 2026
    for year in range(2010, 2027): 
        year_data = df[df.index.year == year]
        if year_data.empty:
            continue
            
        col = "BAMLH0A0HYM2"
        max_val = year_data[col].max()
        min_val = year_data[col].min()
        
        max_date = year_data[year_data[col] == max_val].index[0].strftime('%m-%d')
        min_date = year_data[year_data[col] == min_val].index[0].strftime('%m-%d')
        
        stats_msg.append(f"`{year}`: 高 `{max_val:.2f}`({max_date}) | 低 `{min_val:.2f}`({min_date})")
    
    return "\n".join(stats_msg)

def get_oas_data():
    """获取美银美林高收益债利差 (2010-2026)"""
    try:
        # 修改：起始日期调整为 2010-01-01
        start = datetime.datetime(2010, 1, 1)
        end = datetime.datetime.now()
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        df = df.dropna()
        
        if df.empty:
            return None, None, [], ""
            
        current_oas = float(df.iloc[-1, 0])
        prev_oas = float(df.iloc[-2, 0])
        change = current_oas - prev_oas
        oas_list = df.iloc[-7:, 0].tolist()
        
        history_report = get_oas_history_stats(df)
        return current_oas, change, oas_list, history_report
    except Exception as e:
        print(f"⚠️ OAS 获取失败: {e}")
        return None, None, [], ""

def get_qqq_stats() -> Optional[dict]:
    """获取 QQQ 行情及盘中前复权 ATH"""
    try:
        ticker = yf.Ticker("QQQ")
        df_all = ticker.history(period="max", auto_adjust=True)
        if df_all.empty:
            return None
            
        ath_val = df_all['High'].max()
        ath_date = df_all[df_all['High'] == ath_val].index[-1].strftime('%Y-%m-%d')
        
        curr_price = df_all['Close'].iloc[-1]
        prev_price = df_all['Close'].iloc[-2]
        change_pct = (curr_price - prev_price) / prev_price * 100
        
        drawdown = (curr_price / ath_val - 1) * 100
        
        return {
            "close": float(curr_price),
            "change": float(change_pct),
            "drawdown": float(drawdown),
            "ath_val": float(ath_val),
            "ath_date": ath_date
        }
    except Exception as e:
        print(f"⚠️ QQQ 获取失败: {e}")
        return None

def send_msg(text: str):
    """发送 Telegram 消息"""
    if not TOKEN or not CHAT_ID:
        print("❌ 错误: 未配置环境变量")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        print("✅ 消息发送成功")
    except Exception as e:
        print(f"❌ 消息发送失败: {e}")

def main():
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')
    
    oas, oas_change, oas_list, oas_history = get_oas_data()
    qqq = get_qqq_stats()
    
    if not qqq:
        return
        
    msg = [
        f"📊 *美股收盘简报 (前复权)*",
        f"时间: `{date_str}`",
        "--------------------------------",
        "🔹 *QQQ (纳指100)*",
        f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)"
    ]
    
    dd_val = qqq['drawdown']
    dd_icon = "🟢" if dd_val > -5 else "🟡" if dd_val > -15 else "🔴"
    
    msg.append(f"{dd_icon} 距盘中高点回撤: `{qqq['drawdown']:.2f}%`")
    msg.append(f"历史盘中高点: `{qqq['ath_val']:.2f}`")
    msg.append(f"高点日期: `{qqq['ath_date']}`\n")
    
    if oas is not None:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg.append(f"🏛️ *信用利差 (OAS)*: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)")
        recent_trend = " → ".join([f"{x:.2f}" for x in oas_list[-5:]])
        msg.append(f"近5日趋势: `{recent_trend}`")
        # 修改：文案说明同步更新
        msg.append("\n🗓 *OAS 历年极值 (2010-2026)*:")
        msg.append(oas_history)
    else:
        msg.append("🏛️ *信用利差 (OAS)*: `FRED数据获取延迟`")
        
    msg.append("--------------------------------")
    msg.append("💡 _注：QQQ 历史高点采用盘中(High)前复权数值_")
    
    send_msg("\n".join(msg))

if __name__ == "__main__":
    main()
