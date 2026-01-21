import os
import requests
import yt_dlp
import time

def download_and_send():
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    # 榜单地址（YouTube Music 华语流行热榜）
    list_url = "https://www.youtube.com/playlist?list=PLDfKAXSi6kUUnn_m6MInV7nS46VAn_7m8" 
    
    # 1. 提取榜单信息
    ydl_opts_info = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        print("正在获取榜单信息...")
        result = ydl.extract_info(list_url, download=False)
        entries = result.get('entries', [])

    # 2. 获取前20个视频的详细播放量并排序，筛选出前10名
    all_videos = []
    for entry in entries[:20]:
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl_detail:
                info = ydl_detail.extract_info(video_url, download=False)
                all_videos.append({
                    'url': video_url,
                    'views': info.get('view_count', 0),
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0)
                })
        except Exception as e:
            continue
    
    # 按播放量降序排序并取前10
    top_10 = sorted(all_videos, key=lambda x: x['views'], reverse=True)[:10]

    # 3. 逐个转码并发送
    for i, item in enumerate(top_10, 1):
        print(f"正在处理第 {i}/10 首: {item['title']}")
        
        file_base = f"song_{i}"
        # yt-dlp 配置：仅音频，转为 mp3，不写入封面
        ydl_opts_dl = {
            'format': 'bestaudio/best',
            'outtmpl': file_base,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'writethumbnail': False, # 明确设置不下载封面图片
            'quiet': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([item['url']])
            
            mp3_path = f"{file_base}.mp3"
            
            if os.path.exists(mp3_path):
                with open(mp3_path, 'rb') as audio:
                    # 播放量显示格式化
                    view_str = f"{item['views'] / 10000:.1f}万" if item['views'] < 10000000 else f"{item['views'] / 1000000:.1f}M"
                    caption = f"🎵 TOP {i}: {item['title']}\n👁️ 播放量: {view_str}"
                    
                    files = {'audio': audio}
                    data = {
                        'chat_id': chat_id, 
                        'caption': caption, 
                        'title': item['title'], # 在播放器显示的标题
                        'parse_mode': 'Markdown'
                    }
                    
                    # 发送音频
                    resp = requests.post(f"https://api.telegram.org/bot{token}/sendAudio", files=files, data=data)
                    if resp.status_code == 200:
                        print(f"✅ 已成功推送")
                    else:
                        print(f"❌ 推送失败: {resp.text}")
                
                # 清理文件
                os.remove(mp3_path)
            
            # 短暂休眠，防止触发 Telegram API 频率限制
            time.sleep(3)
            
        except Exception as e:
            print(f"处理错误: {e}")

if __name__ == "__main__":
    download_and_send()
