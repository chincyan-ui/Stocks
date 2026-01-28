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

def get_history_stats(df: pd.DataFrame, col: str) -> str:
    """通用函数：计算 2010-2026 的历年最高/最低点及日期"""
    stats_msg = []
    df.index = pd.to_datetime(df.index)
    
    for year in range(2010, 2027): 
        year_data = df[df.index.year == year]
        if year_data.empty:
            continue
            
        max_val = year_data[col].max()
        min_val = year_data[col].min()
        
        max_date = year_data[year_data[col] == max_val].index[0].strftime('%m-%d')
        min_date = year_data[year_data[col] == min_val].index[0].strftime('%m-%d')
        
        stats_msg.append(f"`{year}`: 高 `{max_val:.2f}`({max_date}) | 低 `{min_val:.2f}`({min_date})")
    
    return "\n".join(stats_msg)

def get_macro_data():
    """获取 OAS (BAMLH0A0HYM2) 和 10年美债 (DGS10) 数据"""
    try:
        start = datetime.datetime(2010, 1, 1)
        end = datetime.datetime.now()
        # 同时抓取两个指标
        df = web.DataReader(["BAMLH0A0HYM2", "DGS10"], "fred", start, end)
        df = df.dropna()
        
        if df.empty:
            return None
            
        # 提取 OAS 数据
        oas_curr = float(df["BAMLH0A0HYM2"].iloc[-1])
        oas_change = oas_curr - float(df["BAMLH0A0HYM2"].iloc[-2])
        oas_history = get_history_stats(df, "BAMLH0A0HYM2")
        
        # 提取 10Y 美债数据
        tnx_curr = float(df["DGS10"].iloc[-1])
        tnx_change = tnx_curr - float(df["DGS10"].iloc[-2])
        tnx_history = get_history_stats(df, "DGS10")
        
        return {
            "oas": (oas_curr, oas_change, oas_history),
            "tnx": (tnx_curr, tnx_change, tnx_history)
        }
    except Exception as e:
        print(f"⚠️ 宏观数据获取失败: {e}")
        return None

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
    
    macro = get_macro_data()
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
    
    if macro:
        # 1. 展示 10Y 美债
        tnx_val, tnx_chg, tnx_hist = macro['tnx']
        t_icon = "📈" if tnx_chg > 0 else "📉"
        msg.append(f"🇺🇸 *10年美债收益率*: `{tnx_val:.2f}%` ({t_icon} `{tnx_chg:+.2f}%`)")
        
        # 2. 展示 OAS
        oas_val, oas_chg, oas_hist = macro['oas']
        o_icon = "📈" if oas_chg > 0 else "📉"
        msg.append(f"🏛️ *信用利差 (OAS)*: `{oas_val:.2f}%` ({o_icon} `{oas_chg:+.2f}%`)\n")
        
        msg.append("🗓 *10Y美债 历年极值 (2010-2026)*:")
        msg.append(tnx_hist)
        msg.append("\n🗓 *OAS 历年极值 (2010-2026)*:")
        msg.append(oas_hist)
    else:
        msg.append("🏛️ *宏观数据*: `FRED数据获取延迟`")
        
    msg.append("--------------------------------")
    msg.append("💡 _注：QQQ 历史高点采用盘中(High)前复权数值_")
    
    send_msg("\n".join(msg))

if __name__ == "__main__":
    main()
