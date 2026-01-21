import requests
import re
import os

def get_qqq_iv():
    # 使用 AlphaQuery 的股票概览页，这个页面极少变动
    url = "https://www.alphaquery.com/stock/QQQ/volatility-option-statistics/30-day/iv-percentile"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    try:
        print(f"尝试访问: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        
        # 如果 404，尝试备用地址（去掉 30-day）
        if response.status_code == 404:
            print("404 错误，尝试备用接口...")
            url = "https://www.alphaquery.com/stock/QQQ/volatility-option-statistics"
            response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            return f"访问失败，状态码: {response.status_code}"

        # 直接在源代码中用正则表达式找 IV Percentile 附近的数值
        # 匹配模式：寻找 "IV Percentile" 后面跟着的数字
        text = response.text
        # 寻找类似 0.2534 这种格式的数字，它通常紧跟在 IV Percentile 描述之后
        match = re.search(r'IV Percentile.*?(\d+\.\d+)', text, re.DOTALL)
        
        if match:
            raw_val = float(match.group(1))
            # 如果数值小于 1 (如 0.25)，转为百分比 (25%)
            if raw_val < 1:
                return f"{raw_val * 100:.2f}%"
            return f"{raw_val:.2f}%"
        
        return "未能识别 IV 数值"

    except Exception as e:
        return f"脚本错误: {str(e)}"

def send_telegram(message):
    token = os.getenv('TG_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    
    # 最终防御：检查环境变量名是否包含空格或非法字符
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": chat_id.strip(), "text": message, "parse_mode": "Markdown"}
    
    r = requests.post(url, data=payload)
    print(f"TG 返回结果: {r.text}")

if __name__ == "__main__":
    val = get_qqq_iv()
    send_telegram(f"📊 *QQQ IV 报告*\n数值: `{val}`")
