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

def get_yearly_stats(df: pd.DataFrame, col_name: str) -> str:
    """计算多年份的最高/最低点及日期"""
    stats_msg = []
    # 确保索引是日期格式
    df.index = pd.to_datetime(df.index)
    
    # 遍历 2020 到 2025
    for year in range(2020, 2026):
        year_data = df[df.index.year == year]
        if year_data.empty:
            continue
            
        # 找到最高点和最低点
        max_val = year_data[col_name].max()
        min_val = year_data[col_name].min()
        
        max_date = year_data[year_data[col_name] == max_val].index[0].strftime('%m-%d')
        min_date = year_data[year_data[col_name] == min_val].index[0].strftime('%m-%d')
        
        stats_msg.append(f"`{year}`: 高 `{max_val:.2f}`({max_date}) | 低 `{min_val:.2f}`({min_date})")
    
    return "\n".join(stats_msg)

def get_oas_data():
    """获取美银美林高收益债利差 (FRED) 及其历史统计"""
    try:
        start = datetime.datetime(2020, 1, 1)
        end = datetime.datetime.now()
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        df = df.dropna()
        
        if df.empty:
            return None, None, [], ""
            
        current_oas = float(df.iloc[-1, 0])
        prev_oas = float(df.iloc[-2, 0])
        change = current_oas - prev_oas
        oas_list = df.iloc[-7:, 0].tolist()
        
        # 计算 2020-2025 统计
        history_report = get_yearly_stats(df, "BAMLH0A0HYM2")
        
        return current_oas, change, oas_list, history_report
    except Exception as e:
        print(f"⚠️ OAS 获取失败: {e}")
        return None, None, [], ""

def get_qqq_stats():
    """获取 QQQ 行情及 2020-2025 历史统计"""
    try:
        ticker = yf.Ticker("QQQ")
        # 抓取 2020 至今的数据
        df = ticker.history(start="2020-01-01")
        if df.empty:
            return None
            
        ath = df['Close'].max()
        curr_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        
        change_pct = (curr_price - prev_price) / prev_price * 100
        drawdown = (curr_price / ath - 1) * 100
        
        # 计算 2020-2025 统计
        history_report = get_yearly_stats(df, "Close")
        
        return {
            "close": float(curr_price),
            "change": float(change_pct),
            "drawdown": float(drawdown),
            "ath": float(ath),
            "history": history_report
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
        f"📊 *美股收盘及历史对比*",
        f"时间: `{date_str}`",
        "--------------------------------",
        "🔹 *QQQ (纳指100)*",
        f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)",
        f"距高点回撤: `{qqq['drawdown']:.2f}%`",
        "\n🗓 *QQQ 历年极值 (2020-2025)*:",
        qqq['history'],
        "--------------------------------",
        "🏛️ *信用利差 (OAS)*"
    ]
    
    if oas is not None:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg.append(f"当前: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)")
        msg.append("\n🗓 *OAS 历年极值 (2020-2025)*:")
        msg.append(oas_history)
    else:
        msg.append("`FRED数据获取延迟`")
        
    msg.append("--------------------------------")
    msg.append("💡 _注：括号内为发生月-日_")
    
    send_msg("\n".join(msg))

if __name__ == "__main__":
    main()
