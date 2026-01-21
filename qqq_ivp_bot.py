import yfinance as yf
import pandas as pd
import requests
import os

def get_iv_metrics():
    # 使用 ^VXN 作为 QQQ 的隐含波动率替代指标（最为权威且免费）
    ticker_symbol = "^VXN"
    
    # 获取过去 252 个交易日的数据（约等于 1 年）
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1y")
    
    if df.empty:
        return "❌ 无法获取数据，请检查网络或 yfinance 状态。"

    # 获取当前最新 IV 值
    current_iv = df['Close'].iloc[-1]
    
    # --- 计算 IV Rank (IVR) ---
    # 公式: (当前值 - 最小值) / (最大值 - 最小值)
    min_iv = df['Close'].min()
    max_iv = df['Close'].max()
    iv_rank = (current_iv - min_iv) / (max_iv - min_iv) * 100

    # --- 计算 IV Percentile (IVP) ---
    # 公式: (过去一年中低于当前值的交易日数 / 总交易日数)
    # 这通常是你在 Barchart/MarketChameleon 看到 70%+ 的原因
    days_below = (df['Close'] < current_iv).sum()
    total_days = len(df)
    iv_percentile = (days_below / total_days) * 100

    # 构造消息
    msg = (
        f"📊 **QQQ 波动率报告 (VXN 基准)**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕒 当前 IV 数值: `{current_iv:.2f}`\n\n"
        f"🔥 **IV Percentile: {iv_percentile:.2f}%**\n"
        f"*(过去一年中有 {iv_percentile:.1f}% 的时间 IV 低于现在)*\n\n"
        f"📉 **IV Rank: {iv_rank:.2f}%**\n"
        f"*(当前 IV 处于一年内高低区间的位置)*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 **交易提示:**\n"
        f"{'✅ IVP较高，适合卖出期权 (Sell Premium)' if iv_percentile > 60 else '⚠️ IVP较低，期权买方较便宜 (Buy Options)'}"
    )
    return msg

def send_telegram(text):
    # 从环境变量获取密钥（GitHub Actions 安全设置）
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not token or not chat_id:
        print("错误: 未找到 TG_BOT_TOKEN 或 TG_CHAT_ID 环境变量")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ 消息发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    report_text = get_iv_metrics()
    send_telegram(report_text)
