import yfinance as yf
import pandas as pd
import requests
import os

# 配置
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def 获取纳指100成分股():
    """从 Wikipedia 实时抓取纳斯达克 100 成分股列表"""
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        df = tables[4] # 对应成分股表格
        return df['Ticker'].tolist()
    except Exception as e:
        print(f"获取列表失败: {e}，使用备用基础列表")
        return ["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST"]

def 计算回撤排行():
    tickers = 获取纳指100成分股()
    print(f"开始分析 {len(tickers)} 只成分股...")
    
    # 批量下载所有股票的历史最高价和最新价 (前复权)
    # 使用 period="max" 确保抓到历史最高点
    data = yf.download(tickers, period="max", auto_adjust=True, group_by='ticker', threads=True)
    
    results = []
    for ticker in tickers:
        try:
            # 获取该股票的 High 和 Close 列
            if ticker not in data.columns.levels[0]: continue
            
            ticker_data = data[ticker]
            # 剔除空值
            ticker_data = ticker_data.dropna()
            
            if ticker_data.empty: continue
            
            # 逻辑：盘中最高价的前复权最大值
            ath_price = ticker_data['High'].max()
            current_price = ticker_data['Close'].iloc[-1]
            
            drawdown = (current_price - ath_price) / ath_price * 100
            
            results.append({
                "symbol": ticker,
                "current": current_price,
                "ath": ath_price,
                "drawdown": drawdown
            })
        except:
            continue

    # 按回撤幅度从大到小排序 (即值越小越靠前)
    results.sort(key=lambda x: x['drawdown'])
    return results[:10] # 取前10名

def 推送报告(top_10):
    lines = ["📊 **纳指 100 回撤最大 Top 10**", "*(基于前复权历史最高点)*", "---"]
    
    for i, item in enumerate(top_10, 1):
        status = "🚨" if item['drawdown'] < -30 else "📉"
        lines.append(f"{i}. **{item['symbol']}**")
        lines.append(f"   ▫️ 距最高位: **{item['drawdown']:.2f}%**")
        lines.append(f"   ▫️ 当前/最高: `{item['current']:.2f}` / `{item['ath']:.2f}`")
    
    msg = "\n".join(lines)
    
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    else:
        print(msg)

if __name__ == "__main__":
    top_list = 计算回撤排行()
    推送报告(top_list)
