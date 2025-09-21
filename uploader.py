"""
Upload a final file to YouTube via OAuth2 interactive flow.
"""
import os
import json
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_youtube_service(client_secrets_file, credentials_store):
    """Get authenticated YouTube service using OAuth2 flow"""
    # Check if credentials file exists and is valid
    if os.path.exists(credentials_store):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(credentials_store, SCOPES)
            if creds.valid:
                return build('youtube', 'v3', credentials=creds)
            elif creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(credentials_store, 'w') as f:
                    f.write(creds.to_json())
                return build('youtube', 'v3', credentials=creds)
        except Exception as e:
            logging.warning(f"Failed to load existing credentials: {e}")
    
    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(credentials_store, 'w') as f:
        f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)


def upload_video_to_youtube(youtube_service, file_path, title, description, tags=None, privacy='public'):
    """Upload video file to YouTube with metadata"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")
    
    body = {
        'snippet': {'title': title, 'description': description, 'tags': tags or ['translated','autodub'], 'categoryId': '22'},
        'status': {'privacyStatus': privacy}
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    try:
        req = youtube_service.videos().insert(part='snippet,status', body=body, media_body=media)
    except Exception as e:
        logging.error(f"Failed to create upload request: {e}")
        raise
        
    resp = None
    try:
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                logging.info('Upload progress: %d%%', int(status.progress()*100))
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        raise
        
    logging.info(f"Upload completed. Video ID: {resp.get('id')}")
    return resp