import yfinance as yf
import pandas as pd
import requests
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VolatilityAnalyzer:
    def __init__(self, ticker_symbol="^VXN"):
        self.ticker_symbol = ticker_symbol

    def fetch_data(self, period="1y"):
        """获取历史数据"""
        try:
            ticker = yf.Ticker(self.ticker_symbol)
            df = ticker.history(period=period)
            if df.empty or len(df) < 10:
                raise ValueError(f"获取的 {self.ticker_symbol} 数据不足")
            return df
        except Exception as e:
            logging.error(f"数据抓取失败: {e}")
            return None

    def calculate_metrics(self, df):
        """计算核心指标"""
        close = df['Close']
        current_iv = close.iloc[-1]
        
        # IV Rank
        min_iv = close.min()
        max_iv = close.max()
        iv_rank = (current_iv - min_iv) / (max_iv - min_iv) * 100 if max_iv != min_iv else 0

        # IV Percentile
        days_below = (close < current_iv).sum()
        iv_percentile = (days_below / len(close)) * 100

        # 获取最近 7 天数据用于趋势展示
        # 只保留日期和收盘价，并按日期倒序排列（最新的在最上面）
        recent_7_days = df.tail(7).copy()
        recent_7_days.index = recent_7_days.index.strftime('%m-%d')
        trend_data = recent_7_days['Close'].sort_index(ascending=False)

        return {
            "current": current_iv,
            "rank": iv_rank,
            "percentile": iv_percentile,
            "trend": trend_data
        }

    def format_report(self, metrics):
        """构造结构化 Markdown 消息"""
        p = metrics['percentile']
        strategy = "✅ IVP 较高，适合卖出期权 (Sell Premium)" if p > 60 else \
                   "⚠️ IVP 较低，期权买方较便宜 (Buy Options)" if p < 40 else \
                   "⚖️ IVP 处于中性区间，建议观望"

        # 构造最近 7 天趋势文本
        trend_text = ""
        for date, value in metrics['trend'].items():
            trend_text += f"`{date}: {value:>6.2f}`\n"

        msg = (
            f"📊 **QQQ 波动率报告 ({self.ticker_symbol})**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 当前 IV 数值: `{metrics['current']:.2f}`\n\n"
            f"🔥 **IV Percentile: {p:.2f}%**\n"
            f"📉 **IV Rank: {metrics['rank']:.2f}%**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 **最近 7 天趋势 (VXN)**\n"
            f"{trend_text}"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 **交易提示:**\n"
            f"{strategy}"
        )
        return msg

def send_telegram(text):
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not all([token, chat_id]):
        logging.error("环境变量缺失: 请检查 TG_BOT_TOKEN 和 TG_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # 使用 Markdown 格式确保等宽字体对齐
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    
    with requests.Session() as session:
        try:
            resp = session.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logging.info("消息推送成功")
        except Exception as e:
            logging.error(f"消息推送失败: {e}")

if __name__ == "__main__":
    analyzer = VolatilityAnalyzer("^VXN")
    data = analyzer.fetch_data()
    
    if data is not None:
        metrics = analyzer.calculate_metrics(data)
        report = analyzer.format_report(metrics)
        send_telegram(report)
    else:
        # 如果获取数据失败，尝试发送通知
        send_telegram("❌ 波动率数据更新失败，请检查 yfinance 数据源或网络连接。")
