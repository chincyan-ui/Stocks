import requests
import os

# 1. 尝试读取环境变量
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def test_connection():
    # 打印调试信息（注意：GitHub日志会部分隐藏Secret，这是正常的）
    print(f"--- 调试信息 ---")
    print(f"TOKEN 是否存在: {'Yes' if TOKEN else 'No'}")
    print(f"CHAT_ID 是否存在: {'Yes' if CHAT_ID else 'No'}")
    
    if not TOKEN or not CHAT_ID:
        print("错误：环境变量未成功加载，请检查 GitHub Secrets 配置！")
        return

    # 2. 尝试发送测试消息
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": "🚀 链路测试成功！你的 GitHub Actions 已经可以与 Telegram 通信了。"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ 成功！请检查你的 Telegram 窗口。")
        else:
            print(f"❌ 失败！错误码: {response.status_code}")
            print(f"原因: {response.text}")
    except Exception as e:
        print(f"❌ 网络异常: {e}")

if __name__ == "__main__":
    test_connection()
