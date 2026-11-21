"""YouTube upload (Shorts) — private + publishAt schedule. Quota: 1600/video.

Auth: YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN for the TARGET channel
(narendradhakadai). OAuth app MUST be in Production or the token dies in 7 days.
Use a SEPARATE Google project from the What If autopilot or quota is shared (6/day total).
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
CATEGORY_GAMING = "20"

def get_service():
    creds = Credentials(token=None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                        client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"],
                        token_uri=TOKEN_URI, scopes=SCOPES)
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def upload_short(video_path, title, description, tags, publish_at=None):
    service = get_service()
    body = {"snippet": {"title": title[:100], "description": description[:5000],
                        "tags": tags[:30], "categoryId": CATEGORY_GAMING},
            "status": {"privacyStatus": "private" if publish_at else "public",
                       "selfDeclaredMadeForKids": False}}
    if publish_at:
        body["status"]["publishAt"] = publish_at
    media = MediaFileUpload(video_path, mimetype="video/mp4",
                            chunksize=8 * 1024 * 1024, resumable=True)
    try:
        req = service.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp["id"], "https://youtu.be/" + resp["id"]
    except HttpError as e:
        if publish_at and e.resp.status in (400, 403):
            body["status"].pop("publishAt", None)
            body["status"]["privacyStatus"] = "public"
            media = MediaFileUpload(video_path, mimetype="video/mp4",
                                    chunksize=8 * 1024 * 1024, resumable=True)
            req = service.videos().insert(part="snippet,status", body=body, media_body=media)
            resp = None
            while resp is None:
                _, resp = req.next_chunk()
            return resp["id"], "https://youtu.be/" + resp["id"]
        raise
