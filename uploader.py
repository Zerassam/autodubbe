"""
Upload a final file to YouTube via OAuth2 interactive flow.
"""
import os
import json
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_youtube_service(client_secrets_file, credentials_store):
    if os.path.exists(credentials_store):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(credentials_store, SCOPES)
        return build('youtube', 'v3', credentials=creds)
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(credentials_store, 'w') as f:
        f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)


def upload_video_to_youtube(youtube_service, file_path, title, description, tags=None, privacy='public'):
    body = {
        'snippet': {'title': title, 'description': description, 'tags': tags or ['translated','autodub'], 'categoryId': '22'},
        'status': {'privacyStatus': privacy}
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    req = youtube_service.videos().insert(part='snippet,status', body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            logging.info('Upload progress: %s', int(status.progress()*100))
    return resp