import requests
from bs4 import BeautifulSoup
import os
import time

# 配置
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def get_nasdaq_100_symbols():
    print("正在从维基百科抓取纳斯达克100成分股列表...")
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 纳斯达克100成分股在第一个名叫 "constituents" 的表格里
        table = soup.find('table', {'id': 'constituents'})
        symbols = []
        for row in table.find_all('tr')[1:]:  # 跳过表头
            cols = row.find_all('td')
            if cols:
                # 维基百科上的股票代码有些带有点号（如BRK.B），雅虎财经通常用短横线（BRK-B）
                symbol = cols[1].text.strip().replace('.', '-')
                symbols.append(symbol)
        print(f"成功获取 {len(symbols)} 个纳斯达克100成分股。")
        return symbols
    except Exception as e:
        print(f"抓取纳斯达克100列表失败: {e}")
        return []

def get_stock_details(symbol):
    try:
        # 请求5年历史K线，用来计算ATH
        api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        result = data['chart']['result'][0]
        meta = result['meta']
        
        # 1. 基础指标提取
        current_price = meta.get('regularMarketPrice')
        volume = meta.get('regularMarketVolume')
        
        # 部分特殊标的可能在盘后缺少当日涨跌幅，我们通过前一日收盘价安全计算
        prev_close = meta.get('previousClose')
        if current_price and prev_close:
            daily_change = ((current_price - prev_close) / prev_close) * 100
        else:
            daily_change = 0.0

        # 雅虎 chart 接口可能不带完整市值，我们通过引用的其他元数据或估算获取（如果缺失则显示为N/A）
        # 注：部分小众接口没有 marketCap，雅虎部分股票此字段在 chart 中可能为 None
        market_cap = meta.get('marketCap', 0)
        
        if not current_price or not volume:
            return None
            
        # 2. 计算交易金额 (现价 * 当日成交量)
        turnover = current_price * volume
        
        # 3. 计算 5 年最大回撤
        highs = [h for h in result['indicators']['quote'][0]['high'] if h is not None]
        ath = max(max(highs), current_price) if highs else current_price
        drawdown = ((current_price - ath) / ath) * 100
        
        return {
            "symbol": symbol,
            "price": current_price,
            "turnover": turnover,              # 用于后续排序
            "drawdown": round(drawdown, 2),
            "market_cap": market_cap,
            "daily_change": round(daily_change, 2)
        }
    except Exception as e:
        # 打印错误方便调试，生产环境可注释掉
        print(f"获取 {symbol} 数据失败: {e}")
        return None

def format_amount(num):
    """格式化大额数字，转换为亿(B)或百万(M)"""
    if num is None or num == 0:
        return "N/A"
    if num >= 1e11:  # 千亿以上
        return f"{num / 1e11:.2f}千亿"
    if num >= 1e8:   # 亿以上
        return f"{num / 1e8:.2f}亿"
    if num >= 1e6:   # 百万以上
        return f"{num / 1e6:.2f}万"
    return str(round(num, 2))

def main():
    symbols = get_nasdaq_100_symbols()
    if not symbols:
        return

    results = []
    print(f"开始获取行情并计算各项指标...")
    for s in symbols:
        data = get_stock_details(s)
        if data:
            results.append(data)
        time.sleep(0.2) # 频率控制

    # 核心逻辑：按交易金额（turnover）从大到小排序
    results.sort(key=lambda x: x['turnover'], reverse=True)
    
    # 筛选前 20 名
    top_20 = results[:20]

    # 构建 TG 消息 (使用 MarkdownV2 格式需要注意特殊字符转义，这里沿用简单 Markdown)
    msg = "📊 *纳斯达克100 · 交易额 Top20 榜单*\n"
    msg += "*(按当日交易金额从大到小排序)*\n\n"
    
    for i, s in enumerate(top_20, 1):
        # 处理涨跌幅符号
        change_icon = "🔺" if s['daily_change'] >= 0 else "🔻"
        change_sign = "+" if s['daily_change'] > 0 else ""
        
        msg += f"{i}. *{s['symbol']}* ({s['price']:.2f})\n"
        msg += f" 💰 交易金额: `{format_amount(s['turnover'])}` | 市值: `{format_amount(s['market_cap'])}`\n"
        msg += f" {change_icon} 当日涨跌: `{change_sign}{s['daily_change']}%`\n"
        msg += f" 📉 5年自ATH回撤: ` {s['drawdown']}% `\n\n"

    # 发送或打印
    if TG_TOKEN and TG_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try:
            res = requests.post(tg_url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
            if res.status_code == 200:
                print("Telegram 推送成功！")
            else:
                print(f"TG 推送返回错误: {res.text}")
        except Exception as e:
            print(f"TG 推送异常: {e}")
    else:
        print("未配置 TG 环境变量，直接控制台打印结果：\n")
        print(msg)

if __name__ == "__main__":
    main()
