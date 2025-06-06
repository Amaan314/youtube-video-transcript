import requests
import re
import json
import time
import xml.etree.ElementTree as ET

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
def fetch_transcript(video_id, max_retries=6, retry_delay=2):
    # optionally use headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    for attempt in range(1, max_retries + 1):
        try:
            url = f'https://www.youtube.com/watch?v={video_id}'
            resp = requests.get(url, headers=headers)
            html = resp.text

            # Extract ytInitialPlayerResponse JSON
            initial_data = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
            # print("initial data: ",initial_data)
            if not initial_data:
                print(f"Attempt {attempt}: Could not find ytInitialPlayerResponse for video ID: {video_id}")
                continue  # retry if response was malformed

            data = json.loads(initial_data.group(1))
            captions = data.get('captions')
            if not captions:
                print(f"No captions available for video ID: {video_id}")
                return ""  # final condition

            tracks = captions['playerCaptionsTracklistRenderer'].get('captionTracks', [])
            if not tracks:
                print(f"No caption tracks available for video ID: {video_id}")
                return ""  # final condition
            # transcript_url = tracks[0]['baseUrl']
            # transcript_xml = requests.get(transcript_url).text
            transcript_xml = ''
            for track in tracks:
                transcript_url = track['baseUrl']
                response = requests.get(transcript_url, headers=headers)
                if response.status_code == 200 and response.text.strip():
                    transcript_xml = response.text
                    break

            if not transcript_xml:
                print(f"Attempt {attempt}: No valid transcript XML found for video ID: {video_id}")
                continue  # retry if transcript didn't load

            # Parse and build transcript string
            root = ET.fromstring(transcript_xml)
            # transcript_lines = []
            # for elem in root.findall('text'):
            #     text = elem.text or ''
            #     transcript_lines.append(text.replace('\n', ' '))
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

            # return ' '.join(transcript_lines).strip()
            print(f"Transcript fetched successfully for video ID: {video_id} on attempt {attempt}")
            return transcript

        except Exception as e:
            print(f"Error fetching transcript for video ID {video_id} on attempt {attempt}: {e}")
            time.sleep(retry_delay * attempt)
