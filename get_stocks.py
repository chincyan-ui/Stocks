import os
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

    # 2. 同步更新到 GitHub Issue
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("REPO")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    # 查找是否存在标题为 "Daily Stock List Data" 的 Issue
    issues_url = f"https://api.github.com/repos/{repo}/issues?state=open"
    res = requests.get(issues_url, headers=headers)
    issue_number = None
    
    if res.status_code == 200:
        for issue in res.json():
            if issue["title"] == "Daily Stock List Data":
                issue_number = issue["number"]
                break
                
    import json
    body_content = f"```json\n{json.dumps(stock_list, ensure_ascii=False)}\n```"

    if issue_number:
        # 更新现有 Issue
        update_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
        requests.patch(update_url, headers=headers, json={"body": body_content})
        print(f"Updated Issue #{issue_number}")
    else:
        # 创建新 Issue
        create_url = f"https://api.github.com/repos/{repo}/issues"
        requests.post(create_url, headers=headers, json={
            "title": "Daily Stock List Data",
            "body": body_content
        })
        print("Created new Issue for stock list")

if __name__ == "__main__":
    main()
