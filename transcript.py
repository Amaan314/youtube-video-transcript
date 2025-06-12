import requests
import re
import json
import time
import xml.etree.ElementTree as ET
import yt_dlp
import os
import base64

# from youtube_transcript_api import YouTubeTranscriptApi

# To fetch transcript using YouTubeTranscriptApi, you can uncomment the following code., not always reliable
# def get_transcript(video_id):
#     """Fetch and cache video transcript with timestamps."""
#     # Check if transcript is already cached
#     if video_id in video_cache and "Transcript" in video_cache[video_id]:
#         print(f"Using cached transcript for video ID: {video_id}")
#         return video_cache[video_id]["Transcript"]
    
#     try:
#         transcript = YouTubeTranscriptApi()
#         caption = transcript.fetch(video_id)
#         # print(caption)
#         formatted_lines = []
#         for snippet in caption.snippets:
#             total_seconds = int(snippet.start)
#             hours = total_seconds // 3600
#             minutes = (total_seconds % 3600) // 60
#             seconds = total_seconds % 60
#             timestamp = f"[{hours:02}:{minutes:02}:{seconds:02}]"
#             formatted_line = f"{timestamp} {snippet.text}"
#             formatted_lines.append(formatted_line)
        
#         full_transcript = " ".join(formatted_lines)
        
#         # Initialize cache structure for this video
#         if video_id not in video_cache:
#             video_cache[video_id] = {}
#         video_cache[video_id]["Transcript"] = full_transcript
        
#         return full_transcript
        
#     except Exception as e:
#         print(f"Unexpected error fetching transcript: {e}")
#         return ''

# Manual Approach to fetch YouTube video transcripts, more reliable than YouTubeTranscriptApi, but still sometimes fails.
# def fetch_transcript(video_id, max_retries=6, retry_delay=2):
#     # optionally use headers to mimic a browser request
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
#     }

#     for attempt in range(1, max_retries + 1):
#         try:
#             url = f'https://www.youtube.com/watch?v={video_id}'
#             resp = requests.get(url, headers=headers)
#             html = resp.text

#             # Extract ytInitialPlayerResponse JSON
#             initial_data = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
#             # print("initial data: ",initial_data)
#             if not initial_data:
#                 print(f"Attempt {attempt}: Could not find ytInitialPlayerResponse for video ID: {video_id}")
#                 continue  # retry if response was malformed

#             data = json.loads(initial_data.group(1))
#             captions = data.get('captions')
#             if not captions:
#                 print(f"No captions available for video ID: {video_id}")
#                 return ""  # final condition

#             tracks = captions['playerCaptionsTracklistRenderer'].get('captionTracks', [])
#             if not tracks:
#                 print(f"No caption tracks available for video ID: {video_id}")
#                 return ""  # final condition
#             # transcript_url = tracks[0]['baseUrl']
#             # transcript_xml = requests.get(transcript_url).text
#             transcript_xml = ''
#             for track in tracks:
#                 transcript_url = track['baseUrl']
#                 response = requests.get(transcript_url, headers=headers)
#                 if response.status_code == 200 and response.text.strip():
#                     transcript_xml = response.text
#                     break

#             if not transcript_xml:
#                 print(f"Attempt {attempt}: No valid transcript XML found for video ID: {video_id}")
#                 continue  # retry if transcript didn't load

#             # Parse and build transcript string
#             root = ET.fromstring(transcript_xml)
#             # transcript_lines = []
#             # for elem in root.findall('text'):
#             #     text = elem.text or ''
#             #     transcript_lines.append(text.replace('\n', ' '))
#             transcript = []
#             for elem in root.findall('text'):
#                 start = float(elem.attrib['start'])
#                 dur = float(elem.attrib.get('dur', 0))
#                 text = elem.text or ''
#                 transcript.append({
#                     'start': start,
#                     'duration': dur,
#                     'text': text.replace('\n', ' ')
#                 })

#             # return ' '.join(transcript_lines).strip()
#             print(f"Transcript fetched successfully for video ID: {video_id} on attempt {attempt}")
#             return transcript

#         except Exception as e:
#             print(f"Error fetching transcript for video ID {video_id} on attempt {attempt}: {e}")
#             time.sleep(retry_delay * attempt)

# Decode and save the cookie file to /tmp only once
COOKIE_PATH = "/tmp/cookies.txt"

def ensure_cookie_file():
    if not os.path.exists(COOKIE_PATH):
        b64_data = os.getenv("YT_COOKIES_B64")
        if b64_data:
            try:
                with open(COOKIE_PATH, "wb") as f:
                    f.write(base64.b64decode(b64_data))
            except Exception as e:
                print(f"Error decoding cookies: {e}")
        else:
            print("YT_COOKIES_B64 not set in environment.")

ensure_cookie_file()  # Run at import time or app startup


def parse_subtitle_content(subtitle_content, ext):
  root = ET.fromstring(subtitle_content)
  transcript = []
  for elem in root.findall('text'):
      start = float(elem.attrib['start'])
      dur = float(elem.attrib.get('dur', 0))
      text = elem.text or ''
      transcript.append({
          'start': start,
          'duration': dur,
          'text': text.replace('\n', ' ')
    })
  return transcript

def fetch_transcript(video_id, preferred_langs=['en-orig', 'en']):
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'quiet': True,
        'no_warnings': True,
        'log_warnings': False,
        'format': 'bestaudio/best',
        'cookiefile': COOKIE_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            
            all_caption_tracks = {}

            if 'subtitles' in info_dict:
                for lang, tracks in info_dict['subtitles'].items():
                    if lang not in all_caption_tracks:
                        all_caption_tracks[lang] = []
                    all_caption_tracks[lang].extend(tracks)
            
            if 'automatic_captions' in info_dict:
                for lang, tracks in info_dict['automatic_captions'].items():
                    if lang not in all_caption_tracks:
                        all_caption_tracks[lang] = []
                    all_caption_tracks[lang].extend(tracks)

            best_transcript_url = None
            best_transcript_ext = None

            def find_first_non_json_track(tracks):
                for track in tracks:
                    ext = track.get('ext')
                    if ext not in ['json', 'json3']:
                        return track
                return None # No suitable non-json track found

            # 1. Try preferred languages first
            for p_lang in preferred_langs:
                if p_lang in all_caption_tracks:
                    best_track = find_first_non_json_track(all_caption_tracks[p_lang])
                    if best_track:
                        best_transcript_url = best_track['url']
                        best_transcript_ext = best_track['ext']
                        print(f"Found preferred language '{p_lang}' track with extension '{best_transcript_ext}'.")
                        break
                if best_transcript_url:
                    break
            
            # 2. If no suitable track found in preferred languages, try any other available language
            if not best_transcript_url:
                for lang, tracks in all_caption_tracks.items():
                    if 'live_chat' in lang or lang in preferred_langs: 
                        continue 
                    best_track = find_first_non_json_track(tracks)
                    if best_track:
                        best_transcript_url = best_track['url']
                        best_transcript_ext = best_track['ext']
                        print(f"Found any language '{lang}' track with extension '{best_transcript_ext}'.")
                        break

            if best_transcript_url and best_transcript_ext:
                try:
                    print(f"Attempting to download transcript from: {best_transcript_url}")
                    response = requests.get(best_transcript_url, stream=True)
                    response.raise_for_status()
                    subtitle_content = response.text
                    return parse_subtitle_content(subtitle_content, best_transcript_ext)
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching subtitle content from URL {best_transcript_url}: {e}")
                    return []
            else:
                print(f"No suitable non-json/json3 transcript URL found for {youtube_url} after checking all options.")
                all_langs_found = set(all_caption_tracks.keys())
                if all_langs_found:
                    print(f"Available caption languages found in info_dict (including potentially json/live_chat): {', '.join(all_langs_found)}")
                else:
                    print("No caption tracks found at all in the info_dict.")
                return []

    except yt_dlp.utils.DownloadError as e:
        print(f"Error with yt-dlp (e.g., video not found, geo-restricted): {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during yt-dlp extraction: {e}")
        return []
