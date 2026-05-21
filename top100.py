import os
import time
import requests
import pandas as pd

# 配置
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def get_nasdaq_100_symbols():
    print("正在从维基百科动态加载最新的纳斯达克100成分股...")
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        # 使用 pandas 直接解析网页中的所有 Table
        tables = pd.read_html(url)
        
        # 寻找包含 Ticker 或 Symbol 列表的那个成分股表格
        df = None
        for t in tables:
            # 将列名统一转为小写方便匹配
            columns = [str(col).lower() for col in t.columns]
            if any('ticker' in col or 'symbol' in col for col in columns):
                df = t
                break
                
        if df is None:
            print("未能定位到成分股表格，请检查维基百科结构。")
            return []
            
        # 找到包含股票代码的那一列
        ticker_col = [col for col in df.columns if 'ticker' in str(col).lower() or 'symbol' in str(col).lower()][0]
        
        # 提取并清洗股票代码（转换雅虎财经兼容的格式，如将 BF.B 转换为 BF-B）
        symbols = df[ticker_col].astype(str).str.strip().str.replace('.', '-', regex=False).tolist()
        print(f"成功加载最新成分股，共计 {len(symbols)} 只股票代码。")
        return symbols
    except Exception as e:
        print(f"解析最新成分股列表失败: {e}")
        return []

def get_stock_details(symbol):
    try:
        # 请求5年历史K线，整合单日行情与历史ATH数据
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        result = data['chart']['result'][0]
        meta = result['meta']
        
        current_price = meta.get('regularMarketPrice')
        volume = meta.get('regularMarketVolume')
        prev_close = meta.get('previousClose')
        market_cap = meta.get('marketCap', 0)
        
        # 核心指标安全校验
        if not current_price or not volume:
            return None
            
        # 1. 计算交易金额 (现价 * 当日成交量)
        turnover = current_price * volume
        
        # 2. 计算当日涨跌幅
        daily_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
        
        # 3. 计算 5 年自最高位（ATH）的回撤比例
        highs = [h for h in result['indicators']['quote'][0]['high'] if h is not None]
        ath = max(max(highs), current_price) if highs else current_price
        drawdown = ((current_price - ath) / ath) * 100
        
        return {
            "symbol": symbol,
            "price": current_price,
            "turnover": turnover,
            "drawdown": round(drawdown, 2),
            "market_cap": market_cap,
            "daily_change": round(daily_change, 2)
        }
    except Exception as e:
        # 如个别退市或刚更换代码的标的报错，静默跳过不干扰整体运行
        return None

def format_amount(num):
    """优雅地格式化巨额美金单位"""
    if num is None or num == 0:
        return "N/A"
    if num >= 1e12:
        return f"{num / 1e12:.2f}万亿"
    if num >= 1e8:
        return f"{num / 1e8:.2f}亿"
    if num >= 1e6:
        return f"{num / 1e6:.2f}万"
    return str(round(num, 2))

def main():
    symbols = get_nasdaq_100_symbols()
    if not symbols:
        return

    results = []
    print(f"正在获取标的详情并计算回撤、交易量指标...")
    for s in symbols:
        data = get_stock_details(s)
        if data:
            results.append(data)
        time.sleep(0.15) # 稳健的频控，防止被雅虎拉黑

    # 核心需求：按“交易金额”从大到小进行降序排序
    results.sort(key=lambda x: x['turnover'], reverse=True)
    
    # 精确拦截交易金额前 20 的活跃标的
    top_20 = results[:20]

    if not top_20:
        print("未收集到足够的行情数据。")
        return

    # 构建美化版的 Telegram 报表
    msg = "📊 *纳斯达克100 · 交易额 Top20 监控*\n"
    msg += "*(数据按当日交易金额降序排列)*\n\n"
    
    for i, s in enumerate(top_20, 1):
        change_icon = "🔺" if s['daily_change'] >= 0 else "🔻"
        change_sign = "+" if s['daily_change'] > 0 else ""
        
        msg += f"{i}. *{s['symbol']}* (现价: ${s['price']:.2f})\n"
        msg += f" 💰 交易金额: `{format_amount(s['turnover'])}` | 市值: `{format_amount(s['market_cap'])}`\n"
        msg += f" {change_icon} 当日涨跌: `{change_sign}{s['daily_change']}%`\n"
        msg += f" 📉 5年高点回撤: `{s['drawdown']}%`\n\n"

    # 发送通道选择
    if TG_TOKEN and TG_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try:
            res = requests.post(tg_url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
            if res.status_code == 200:
                print("✨ 纳指100 最新情报已成功推送到 Telegram！")
            else:
                print(f"TG 渠道返回错误: {res.text}")
        except Exception as e:
            print(f"TG 通信异常: {e}")
    else:
        print("未检测到 TG 机器人配置，直接在控制台输出：\n")
        print(msg)

if __name__ == "__main__":
    main()
