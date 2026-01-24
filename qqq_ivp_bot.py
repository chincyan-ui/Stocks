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

    def fetch_data(self, period="2y"): # 抓取2年数据，确保计算1年前的IVP时有足够参考
        try:
            ticker = yf.Ticker(self.ticker_symbol)
            df = ticker.history(period=period)
            if df.empty or len(df) < 252:
                raise ValueError(f"数据不足，无法计算一年期百分位")
            return df
        except Exception as e:
            logging.error(f"数据抓取失败: {e}")
            return None

    def calculate_ivp_series(self, df, window=252):
        """
        计算滚动 IV Percentile
        原理：对每一天，计算其在过去 window 天内的百分比排名
        """
        # 使用滚动排名函数 (rolling rank)
        # pct=True 返回 0 到 1 之间的百分比
        ivp_series = df['Close'].rolling(window=window).apply(
            lambda x: (x < x.iloc[-1]).sum() / len(x) * 100
        )
        return ivp_series

    def calculate_metrics(self, df):
        """计算核心指标及最近7天趋势"""
        close = df['Close']
        current_iv = close.iloc[-1]
        
        # 计算整段序列的 IVP 趋势
        ivp_all = self.calculate_ivp_series(df)
        
        # IV Rank (基于最后一年数据)
        last_year_data = close.tail(252)
        min_iv = last_year_data.min()
        max_iv = last_year_data.max()
        iv_rank = (current_iv - min_iv) / (max_iv - min_iv) * 100 if max_iv != min_iv else 0

        # 提取最近 7 天的 IVP 趋势
        recent_ivp = ivp_all.tail(7).copy()
        recent_ivp.index = recent_ivp.index.strftime('%m-%d')
        # 倒序排列：最新日期在前
        trend_data = recent_ivp.sort_index(ascending=False)

        return {
            "current_iv": current_iv,
            "current_ivp": ivp_all.iloc[-1],
            "rank": iv_rank,
            "trend": trend_data
        }

    def format_report(self, metrics):
        """构造结构化消息"""
        ivp = metrics['current_ivp']
        strategy = "✅ IVP 较高，适合卖出期权 (Sell Premium)" if ivp > 60 else \
                   "⚠️ IVP 较低，期权买方较便宜 (Buy Options)" if ivp < 40 else \
                   "⚖️ IVP 处于中性区间，建议观望"

        # 构造最近 7 天 IVP 趋势文本
        trend_text = ""
        for date, val in metrics['trend'].items():
            # 增加一个简单的箭头指示趋势
            trend_text += f"`{date}: {val:>6.1f}%` \n"

        msg = (
            f"📊 **QQQ 波动率报告 ({self.ticker_symbol})**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 当前 IV 数值: `{metrics['current_iv']:.2f}`\n"
            f"🔥 **当前 IVP: {ivp:.2f}%**\n"
            f"📉 **当前 IV Rank: {metrics['rank']:.2f}%**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 **最近 7 天 IV Percentile 趋势**\n"
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
        logging.error("环境变量缺失")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
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
    # 为了计算滚动IVP，需要获取更多历史数据
    data = analyzer.fetch_data(period="2y")
    
    if data is not None:
        metrics = analyzer.calculate_metrics(data)
        report = analyzer.format_report(metrics)
        send_telegram(report)
