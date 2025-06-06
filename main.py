from fastapi import FastAPI
from transcript import fetch_transcript

app = FastAPI()

@app.get(
    "/video/transcript/{video_id}",
    summary="Get Video Transcript",
    description="Fetches the transcript of a YouTube video with timestamps.",
    tags=["Video"]
)   
def get_video_transcript(video_id: str):
    """Get the full transcript of a YouTube video."""
    try:
        transcript = fetch_transcript(video_id)
        if not transcript:
            print(f"No transcript found or an issue occurred for video ID: {video_id}")
            return []
        return transcript
    except Exception as e:
        print(f"Error fetching transcript for video ID {video_id}: {e}")
        return []