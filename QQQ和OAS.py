import datetime
import os
import requests
import pandas as pd
import pytz
import yfinance as yf
import pandas_datareader.data as web
from typing import Tuple, List, Optional, Dict

# ================= 配置环境 =================
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 建议将常数提取出来，方便以后修改
OAS_TICKER = "BAMLH0A0HYM2"
EQUITY_TICKER = "QQQ"

def get_oas_data() -> Tuple[Optional[float], Optional[float], List[float]]:
    """获取美银美林高收益债利差 (FRED)"""
    try:
        # 增加获取天数，确保排除周末后仍有足够数据计算趋势
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=45) 
        
        df = web.DataReader(OAS_TICKER, "fred", start, end)
        recent_df = df.dropna()
        
        if len(recent_df) < 2:
            return None, None, []
        
        # 使用 iloc[-1] 确保获取最新值
        oas_list = recent_df.iloc[:, 0].tolist()
        current_oas = float(oas_list[-1])
        prev_oas = float(oas_list[-2])
        change = current_oas - prev_oas
        
        return current_oas, change, oas_list
    except Exception as e:
        print(f"❌ OAS 获取失败: {e}")
        return None, None, []

def get_qqq_stats() -> Optional[Dict]:
    """获取 QQQ 行情及回撤数据"""
    try:
        ticker = yf.Ticker(EQUITY_TICKER)
        # 增加修复功能，yfinance 有时会返回空数据，使用 auto_adjust
        df = ticker.history(period="2y", auto_adjust=True)
        
        if df.empty or len(df) < 2:
            return None
        
        # 计算历史高点 (ATH)
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
        print(f"❌ QQQ 获取失败: {e}")
        return None

def send_msg(text: str):
    """发送 Telegram 消息"""
    if not TOKEN or not CHAT_ID:
        print("⚠️ 错误: 未配置环境变量 TELEGRAM_TOKEN 或 CHAT_ID")
        return
        
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True # 禁用网页预览，让消息更简洁
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"🚀 消息发送失败: {e}")

def main():
    # 1. 设置时区
    tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M')

    # 2. 并行/顺序获取数据
    qqq = get_qqq_stats()
    oas, oas_change, oas_list = get_oas_data()
    
    # 3. 容错处理：即使 QQQ 失败，如果有 OAS 数据也可以考虑推送，或者维持原逻辑
    if not qqq:
        print("🔴 未获取到核心交易数据，程序终止。")
        return

    # 4. 构建美化模板
    # 使用状态图标逻辑
    dd_val = qqq['drawdown']
    if dd_val > -5:
        dd_icon, status_text = "🟢", "健康"
    elif dd_val > -12:
        dd_icon, status_text = "🟡", "回调"
    else:
        dd_icon, status_text = "🔴", "严重回撤"

    lines = [
        f"📊 *美股收盘简报* | {status_text}",
        f"时间: `{date_str}`",
        "--------------------------------",
        f"🔹 *{EQUITY_TICKER} (纳指100)*",
        f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)",
        f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%`",
        f"   (ATH: `{qqq['ath']:.1f}`)"
    ]
        
    if oas is not None:
        trend_icon = "🔺" if oas_change > 0 else "🔹"
        # 优化趋势展示：只取最近5个交易日
        short_trend = oas_list[-5:]
        trend_str = " → ".join([f"{x:.2f}" for x in short_trend])
        
        lines.append(f"\n🏛️ *信用利差 (OAS)*")
        lines.append(f"当前: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)")
        lines.append(f"趋势: `{trend_str}`")

    lines.append("--------------------------------")
    lines.append("💡 _提示：OAS 走高通常意味着信用环境恶化_")
    
    send_msg("\n".join(lines))

if __name__ == "__main__":
    main()
