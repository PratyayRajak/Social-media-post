import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube',
]


def _get_youtube_client():
    """Create an authenticated YouTube API client."""
    client_id = os.environ.get('YT_CLIENT_ID')
    client_secret = os.environ.get('YT_CLIENT_SECRET')
    refresh_token = os.environ.get('YT_REFRESH_TOKEN')

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
    )
    return build('youtube', 'v3', credentials=creds)


def post_to_youtube(video_path, title, description, privacy='public'):
    """Uploads a video to YouTube using the YouTube Data API v3."""
    client_id = os.environ.get('YT_CLIENT_ID')
    client_secret = os.environ.get('YT_CLIENT_SECRET')
    refresh_token = os.environ.get('YT_REFRESH_TOKEN')

    if not client_id or not client_secret or not refresh_token:
        return {
            'success': False,
            'error': 'YouTube credentials not configured. Go to Settings to add your Client ID, Client Secret, and complete OAuth.',
        }

    try:
        youtube = _get_youtube_client()

        media = MediaFileUpload(video_path, resumable=True)
        request = youtube.videos().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description,
                    'categoryId': '22',
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False,
                },
            },
            media_body=media,
        )

        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response.get('id')
        return {
            'success': True,
            'videoId': video_id,
            'videoUrl': f'https://www.youtube.com/watch?v={video_id}',
            'message': f'Video uploaded to YouTube! Video ID: {video_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'YouTube upload error: {err_msg}')

        if 'exceeded the number of videos' in err_msg or 'uploadLimitExceeded' in err_msg:
            return {
                'success': False,
                'error': 'YouTube: Daily upload limit reached. YouTube limits the number of videos you can upload per day. Please wait 24 hours and try again, or request a quota increase at https://console.cloud.google.com/ → YouTube Data API → Quotas.',
            }

        if '403' in err_msg or 'forbidden' in err_msg.lower():
            return {
                'success': False,
                'error': _build_403_help(err_msg),
            }

        if '401' in err_msg or 'invalid_grant' in err_msg.lower():
            return {
                'success': False,
                'error': 'YouTube: Authentication expired. Go to Settings and re-authorize your YouTube account.',
            }

        return {'success': False, 'error': f'YouTube: {err_msg}'}


def _build_403_help(raw_error):
    """Build a helpful error message for YouTube 403 errors."""
    hints = []
    lower = raw_error.lower()

    if 'quotaexceeded' in lower or 'quota' in lower:
        hints.append('Your YouTube Data API daily quota (10,000 units) may be exceeded. Each upload uses ~1,600 units. Wait 24 hours or request a quota increase in Google Cloud Console.')
    if 'forbidden' in lower or 'insufficientpermissions' in lower:
        hints.append('Your OAuth token may lack required permissions. Go to Settings and re-authorize YouTube with full upload permissions.')
    if not hints:
        hints.append('Check that the YouTube Data API is enabled in your Google Cloud Console project.')
        hints.append('If your app is in "Testing" mode in Google Cloud Console, make sure your Google account is added as a test user.')
        hints.append('Your refresh token may have expired — go to Settings and re-authorize YouTube.')

    return 'YouTube 403 Forbidden. Possible causes:\n• ' + '\n• '.join(hints)


def pre_upload_to_youtube(video_path, title, description, on_progress=None):
    """Pre-upload: Upload video as PRIVATE (not visible to anyone)."""
    client_id = os.environ.get('YT_CLIENT_ID')
    client_secret = os.environ.get('YT_CLIENT_SECRET')
    refresh_token = os.environ.get('YT_REFRESH_TOKEN')

    if not client_id or not client_secret or not refresh_token:
        return {'success': False, 'error': 'YouTube credentials not configured.'}

    try:
        youtube = _get_youtube_client()
        file_size = os.path.getsize(video_path)

        if on_progress:
            on_progress(5)

        media = MediaFileUpload(video_path, resumable=True, chunksize=5 * 1024 * 1024)
        request = youtube.videos().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description,
                    'categoryId': '22',
                },
                'status': {
                    'privacyStatus': 'private',
                    'selfDeclaredMadeForKids': False,
                },
            },
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and on_progress:
                progress = int(status.progress() * 95)
                on_progress(min(progress, 95))

        if on_progress:
            on_progress(100)

        video_id = response.get('id')
        print(f'   YouTube: Pre-uploaded as private. Video ID: {video_id}')

        return {
            'success': True,
            'videoId': video_id,
            'videoUrl': f'https://www.youtube.com/watch?v={video_id}',
            'message': 'Video pre-uploaded to YouTube (private)',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'YouTube pre-upload error: {err_msg}')
        return {'success': False, 'error': f'YouTube: {err_msg}'}


def publish_youtube_video(video_id):
    """Publish a pre-uploaded YouTube video by changing privacy to public."""
    try:
        youtube = _get_youtube_client()

        youtube.videos().update(
            part='status',
            body={
                'id': video_id,
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False,
                },
            },
        ).execute()

        return {
            'success': True,
            'videoId': video_id,
            'videoUrl': f'https://www.youtube.com/watch?v={video_id}',
            'message': f'Video published on YouTube! Video ID: {video_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'YouTube publish error: {err_msg}')
        return {'success': False, 'error': f'YouTube: {err_msg}'}


def get_youtube_auth_url():
    """Generate a YouTube OAuth URL for initial authorization."""
    client_id = os.environ.get('YT_CLIENT_ID')
    client_secret = os.environ.get('YT_CLIENT_SECRET')

    if not client_id or not client_secret:
        return None

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': ['http://localhost:5000/auth/youtube/callback'],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = 'http://localhost:5000/auth/youtube/callback'

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
    )
    return auth_url


def exchange_youtube_code(code):
    """Exchange an authorization code for tokens."""
    client_id = os.environ.get('YT_CLIENT_ID')
    client_secret = os.environ.get('YT_CLIENT_SECRET')

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': ['http://localhost:5000/auth/youtube/callback'],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = 'http://localhost:5000/auth/youtube/callback'
    flow.fetch_token(code=code)

    credentials = flow.credentials
    return {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
    }
