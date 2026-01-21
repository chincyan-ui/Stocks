import cloudscraper
from bs4 import BeautifulSoup
import os
import re

def get_qqq_iv_precise():
    # 切换回 AlphaQuery 的概览页，但使用极其严格的过滤逻辑
    url = "https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile"
    scraper = cloudscraper.create_scraper(browser='chrome')

    try:
        resp = scraper.get(url, timeout=30)
        if resp.status_code != 200:
            return f"访问失败: {resp.status_code}"

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 核心逻辑：先找文本，再找它旁边的数字
        # 1. 寻找页面中所有包含 "IV Percentile" 字样的元素
        elements = soup.find_all(text=re.compile(r'IV Percentile', re.I))
        
        for el in elements:
            # 向上找到父容器，再在父容器里找数字
            parent = el.parent
            # 在父容器及其兄弟节点中搜寻百分比数字或小数
            # 我们要找的是类似 0.25 或 25.4% 这种
            text_around = parent.get_text()
            match = re.search(r'(\d+\.\d+)', text_around)
            if match:
                val = float(match.group(1))
                # 关键过滤：如果数字是 2.12 这种（当前涨跌幅），跳过它
                # IV Percentile 通常不会恰好等于当日涨跌幅
                # 且 AlphaQuery 的原始值通常是小数（如 0.25）
                if 0 < val < 1:
                    return f"{val*100:.2f}%"
                elif 1 <= val <= 100:
                    return f"{val:.2f}%"

        # 方案 B: 备用 Barchart 逻辑，但排除了 2.12 这种价格变动值
        return "未能定位到正确的 IV 字段"

    except Exception as e:
        return f"异常: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": chat_id.strip(), "text": message, "parse_mode": "Markdown"}
    cloudscraper.create_scraper().post(url, data=payload)

if __name__ == "__main__":
    iv_val = get_qqq_iv_precise()
    
    # 增加调试信息，如果数值还是 2.12，我们会知道
    msg = f"📊 *QQQ 数据对齐测试*\n\n"
    msg += f"🔥 **提取到的 IV Percentile**: `{iv_val}`\n\n"
    msg += f"⚠️ *注意：如果该数值与股价涨跌幅一致，请联系修复。*"
    
    send_telegram(msg)
