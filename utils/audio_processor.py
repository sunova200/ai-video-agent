import yt_dlp
from pydub import AudioSegment
import os
import time
import random

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR,exist_ok = True)


def download_youtube_audio(url: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(2, 8))
            
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }],
                "quiet": False,  # Set to True to suppress output
                "retries": 3,
                "retry_sleep_functions": {"http": lambda n: min(2 ** n, 30)},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                # ✅ Removed js_runtimes to avoid format error
                # If needed later: 'js_runtimes': {'deno': {}, 'node': {}}
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # ✅ Safely extract the downloaded filename
                if 'requested_downloads' in info and info['requested_downloads']:
                    filename = info['requested_downloads'][0]['filepath']
                else:
                    filename = ydl.prepare_filename(info)
                    # Adjust for post-processor conversion to WAV
                    filename = os.path.splitext(filename)[0] + '.wav'
                
                # Verify file exists
                if not os.path.exists(filename):
                    base = os.path.splitext(filename)[0]
                    for ext in ['.wav', '.webm', '.m4a', '.mp3']:
                        candidate = base + ext
                        if os.path.exists(candidate):
                            filename = candidate
                            break
                
                print(f"✅ Downloaded: {filename}")
                return filename
                
        except yt_dlp.utils.DownloadError as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                wait = (attempt + 1) * 60
                print(f"⚠️  Rate limited. Waiting {wait}s before retry {attempt+1}/{max_retries}")
                time.sleep(wait)
                continue
            print(f"❌ Download error: {e}")
            raise
    
    raise Exception(f"Failed after {max_retries} retries")
# data = download_youtube_audio("https://www.youtube.com/watch?v=wuRI-1At6w0")
# data = r"C:\Users\BALAJI\Downloads\MLOps Zero to Hero-part-1\10 - AWS Sagemaker AI\60. Amazon SageMaker Production Setup - Part 2.mp4"

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) #16khz
    audio.export(output_path, format="wav")
    return output_path

# data_final = convert_to_wav(data)



def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000 

    chunks = []

    for i, start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path , format = "wav")

        chunks.append(chunk_path)
    
    return chunks

# print(chunk_audio(data_final))

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks