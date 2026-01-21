import os
import requests
import yt_dlp
import time

def download_and_send():
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    # 更换为 YouTube Music 官方“华语流行歌曲热榜”链接 (全球通用且稳定)
    list_url = "https://www.youtube.com/playlist?list=PLeHlpT96Y7S-YFndI_m301_p_A7XG7KzT" 
    
    ydl_opts_info = {'quiet': True, 'extract_flat': True}
    
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        print("正在获取榜单信息...")
        try:
            result = ydl.extract_info(list_url, download=False)
            entries = result.get('entries', [])
            if not entries:
                print("错误：无法获取播放列表条目。")
                return
        except Exception as e:
            print(f"提取列表失败: {e}")
            return

    all_videos = []
    # 增加检测数量到前 30 个，确保筛选出真正的高播放量
    for entry in entries[:30]:
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        try:
            # 获取核心元数据（不下载）
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl_detail:
                info = ydl_detail.extract_info(video_url, download=False)
                view_count = info.get('view_count', 0)
                if view_count: # 确保获取到了播放量
                    all_videos.append({
                        'url': video_url,
                        'views': view_count,
                        'title': info.get('title', 'Unknown Title')
                    })
        except:
            continue
    
    # 按播放量排序并取前 10
    top_10 = sorted(all_videos, key=lambda x: x['views'], reverse=True)[:10]

    for i, item in enumerate(top_10, 1):
        print(f"正在处理第 {i}/10 首: {item['title']}")
        
        file_base = f"song_{i}"
        ydl_opts_dl = {
            'format': 'bestaudio/best',
            'outtmpl': file_base,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'writethumbnail': False,
            'quiet': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([item['url']])
            
            mp3_path = f"{file_base}.mp3"
            
            if os.path.exists(mp3_path):
                with open(mp3_path, 'rb') as audio:
                    view_display = f"{item['views'] / 10000:.1f}万" if item['views'] < 10000000 else f"{item['views'] / 1000000:.1f}M"
                    caption = f"🎵 TOP {i}: {item['title']}\n👁️ 播放量: {view_display}"
                    
                    files = {'audio': audio}
                    data = {
                        'chat_id': chat_id, 
                        'caption': caption, 
                        'title': item['title'],
                        'parse_mode': 'Markdown'
                    }
                    
                    requests.post(f"https://api.telegram.org/bot{token}/sendAudio", files=files, data=data)
                
                os.remove(mp3_path)
            time.sleep(3) # 避开 TG 频率限制
            
        except Exception as e:
            print(f"处理第 {i} 首时出错: {e}")

if __name__ == "__main__":
    download_and_send()
