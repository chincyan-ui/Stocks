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

def get_oas_data() -> Tuple[Optional[float], Optional[float], list]:
    """获取美银美林高收益债利差 (FRED)"""
    try:
        # FRED 数据通常有 2 天左右延迟，取 30 天确保覆盖
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=30)
        # 增加 timeout 防止 GitHub Actions 卡死
        df = web.DataReader("BAMLH0A0HYM2", "fred", start, end)
        recent_df = df.dropna()
        if recent_df.empty or len(recent_df) < 2:
            return None, None, []
            
        oas_list = recent_df.iloc[-7:, 0].tolist()
        current_oas = float(oas_list[-1])
        prev_oas = float(oas_list[-2])
        change = current_oas - prev_oas
        return current_oas, change, oas_list
    except Exception as e:
        print(f"⚠️ OAS 获取失败: {e}")
        return None, None, []

def get_qqq_stats() -> Optional[dict]:
    """获取 QQQ 行情及回撤数据"""
    try:
        ticker = yf.Ticker("QQQ")
        # 1y 数据足够计算 ATH，且加载速度比 2y 快
        df = ticker.history(period="1y")
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
        "disable_web_page_preview": True # 保持消息简洁
    }
    try:
        # 增加 timeout 避免网络波动导致任务僵死
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        print("✅ 消息发送成功")
    except Exception as e:
        print(f"❌ 消息发送失败: {e}")

def main():
    # 设置上海时区
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d %H:%M')
    
    # 获取数据
    oas, oas_change, oas_list = get_oas_data()
    qqq = get_qqq_stats()
    
    if not qqq:
        print("⛔ 无法获取行情数据，跳过推送。")
        return
        
    # 构造更美观的消息格式
    msg = [
        f"📊 *美股收盘简报*",
        f"时间: `{date_str}`",
        "--------------------------------",
        "🔹 *QQQ (纳指100)*"
    ]
    
    # QQQ 回撤状态图标
    dd_val = qqq['drawdown']
    dd_icon = "🟢" if dd_val > -5 else "🟡" if dd_val > -15 else "🔴"
    
    msg.append(f"收盘: `{qqq['close']:.2f}` (`{qqq['change']:+.2f}%`)")
    msg.append(f"{dd_icon} 距高点回撤: `{qqq['drawdown']:.2f}%` (ATH: `{qqq['ath']:.1f}`)\n")
    
    # OAS 数据（如果有）
    if oas is not None:
        trend_icon = "📈" if oas_change > 0 else "📉"
        msg.append(f"🏛️ *信用利差 (OAS)*: `{oas:.2f}%` ({trend_icon} `{oas_change:+.2f}%`)")
        recent_trend = " → ".join([f"{x:.2f}" for x in oas_list[-5:]])
        msg.append(f"趋势: `{recent_trend}`")
    else:
        msg.append("🏛️ *信用利差 (OAS)*: `FRED数据获取延迟`")
        
    msg.append("--------------------------------")
    msg.append("💡 _提示：OAS 异常升高通常预示流动性收紧_")
    
    send_msg("\n".join(msg))

if __name__ == "__main__":
    main()
