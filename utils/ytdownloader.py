import argparse
import yt_dlp
from pydub import AudioSegment
import os

def download_video_as_mp3(video_url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',  # Save as <title>.mp3
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            mp3_file = f"{info['title']}.mp3"
            print(f"Downloaded and converted to MP3: {mp3_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description='Download YouTube video as MP3.')
    parser.add_argument('url', type=str, help='YouTube video URL')
    args = parser.parse_args()

    download_video_as_mp3(args.url)

if __name__ == '__main__':
    main()
