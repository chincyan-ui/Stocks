import os
import requests
import yt_dlp

def get_yt_songs():
    # 使用 yt-dlp 抓取 YouTube Music 华语流行热榜
    # 也可以使用特定的榜单 URL
    list_url = "https://www.youtube.com/playlist?list=PLDfKAXSi6kUUnn_m6MInV7nS46VAn_7m8" # 这是一个华语流行示例榜单
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_ext': True,
    }

    songs_found = []
    threshold = 10000000  # 1000万播放量阈值

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(list_url, download=False)
            if 'entries' in result:
                for entry in result['entries']:
                    if len(songs_found) >= 10: break # 只取10首
                    
                    # 获取详细信息
                    video_id = entry['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    # 再次获取单个视频的精确播放量
                    try:
                        info = ydl.extract_info(video_url, download=False)
                        view_count = info.get('view_count', 0)
                        
                        if view_count >= threshold:
                            title = info.get('title', '未知标题')
                            view_str = f"{view_count / 1000000:.1f}M"
                            songs_found.append(f"🎵 *{title}*\n👁️ 播放量: {view_str}\n🔗 [点击收听]({video_url})")
                    except:
                        continue
        except Exception as e:
            print(f"抓取错误: {e}")

    return songs_found

def send_to_tg(songs):
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not songs:
        text = "今日暂未发现播放量破千万的新中文单曲。"
    else:
        text = "🔥 *今日 YouTube 破千万播放华语金曲推荐* \n\n" + "\n\n".join(songs)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True # 不显示预览图片
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    results = get_yt_songs()
    send_to_tg(results)
