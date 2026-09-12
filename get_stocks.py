import json
import requests
from bs4 import BeautifulSoup

def get_wiki_symbols(url, selector):
    symbols = set()
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select(selector)
            for row in rows[1:]:
                cols = row.select('td')
                if cols:
                    sym = cols[0].text.strip().replace(' ', '-').replace('.', '-')
                    if sym:
                        symbols.add(sym)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return symbols

def main():
    # 1. 抓取标普 500 和 纳指 100
    symbols = {"IONQ", "TQQQ", "SPCX", "SPCH"}
    
    sp500 = get_wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 'table#constituents tr')
    nd100 = get_wiki_symbols("https://en.wikipedia.org/wiki/Nasdaq-100", 'table#constituents tr')
    
    symbols.update(sp500)
    symbols.update(nd100)
    
    stock_list = [{"symbol": s} for s in sorted(list(symbols))]
    print(f"Total unique stocks: {len(stock_list)}")

    # 2. 自动生成 GitHub Actions 需要的 issue_body.md 文件
    body_content = f"```json\n{json.dumps(stock_list, ensure_ascii=False)}\n```"
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(body_content)
    print("Successfully generated issue_body.md")

if __name__ == "__main__":
    main()
