import os
import requests

# 1. 这里的变量名必须与 GitHub Secrets 严格一致
key_id = os.getenv('ALPACA_API_KEY', '').strip()
secret = os.getenv('ALPACA_SECRET_KEY', '').strip()

def diag():
    # 强制尝试 Paper API 路径
    url = "https://paper-api.alpaca.markets/v2/account"
    
    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret
    }

    print(f"--- 诊断开始 ---")
    print(f"Key ID 长度: {len(key_id)} 位")
    print(f"Secret 长度: {len(secret)} 位")
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            print("✅ 鉴权通过！正在获取行情...")
            # 鉴权通过后尝试行情
            data_url = "https://data.alpaca.markets/v2/stocks/snapshots?symbols=AAPL"
            data_res = requests.get(data_url, headers=headers)
            print(f"行情数据状态: {data_res.status_code}")
            print(f"行情返回: {data_res.text[:100]}")
        else:
            print(f"❌ 依旧 401！")
            print(f"Headers 检查: APCA-API-KEY-ID 是不是拼错了？")
            print(f"API 返回原始信息: {res.text}")
            
    except Exception as e:
        print(f"网络异常: {e}")

if __name__ == "__main__":
    diag()
