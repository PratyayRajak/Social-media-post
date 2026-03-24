import os
import time
import base64
import requests

CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks for reliability


def _get_mime_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
    }
    return mime_types.get(ext, 'video/mp4')


def _build_tweet_text(title, description):
    if not description or description == title:
        return _truncate_text(title, 280)
    combined = f'{title}\n\n{description}'
    return _truncate_text(combined, 280)


def _truncate_text(text, max_length):
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def _extract_x_error(error):
    if hasattr(error, 'response') and error.response is not None:
        try:
            data = error.response.json()
            if data.get('detail'):
                if 'credit' in data['detail'].lower():
                    return 'API credits depleted. Your X API free tier credits are used up. Please upgrade your plan at developer.x.com or wait for credits to reset.'
                return data['detail']
            if data.get('errors') and data['errors'][0].get('message'):
                return data['errors'][0]['message']
            if data.get('title'):
                if data['title'] == 'CreditsDepleted':
                    return 'API credits depleted. Your X API free tier credits are used up. Please upgrade your plan at developer.x.com or wait for credits to reset.'
                return data['title']
        except Exception:
            pass
    return str(error)


def _get_oauth1_session():
    """Create an OAuth1 session for X API using requests_oauthlib."""
    from requests_oauthlib import OAuth1Session

    api_key = os.environ.get('X_API_KEY')
    api_secret = os.environ.get('X_API_SECRET')
    access_token = os.environ.get('X_ACCESS_TOKEN')
    access_secret = os.environ.get('X_ACCESS_SECRET')

    return OAuth1Session(
        api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_secret,
    )


def _chunked_media_upload(session, video_path, on_progress=None):
    """Upload media via X API v1.1 chunked media upload (INIT, APPEND, FINALIZE)."""
    file_size = os.path.getsize(video_path)
    mime_type = _get_mime_type(video_path)
    media_upload_url = 'https://upload.twitter.com/1.1/media/upload.json'

    # INIT
    init_data = {
        'command': 'INIT',
        'total_bytes': file_size,
        'media_type': mime_type,
        'media_category': 'tweet_video',
    }
    init_res = session.post(media_upload_url, data=init_data)
    if init_res.status_code in (404, 403):
        raise Exception(
            'X: Media upload not available. Your X API plan may not include media upload access. '
            'Please upgrade your X API plan (Basic or Pro) at developer.x.com.'
        )
    init_res.raise_for_status()
    media_id = init_res.json()['media_id_string']

    if on_progress:
        on_progress(5)
    print(f'   X: Upload initialized, media ID: {media_id}')

    # APPEND
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    with open(video_path, 'rb') as f:
        for segment in range(total_chunks):
            chunk = f.read(CHUNK_SIZE)
            chunk_b64 = base64.b64encode(chunk).decode('utf-8')

            append_data = {
                'command': 'APPEND',
                'media_id': media_id,
                'media_data': chunk_b64,
                'segment_index': segment,
            }
            append_res = session.post(media_upload_url, data=append_data)
            append_res.raise_for_status()

            chunk_progress = 5 + round(((segment + 1) / total_chunks) * 85)
            if on_progress:
                on_progress(chunk_progress)
            print(f'   X: Chunk {segment + 1}/{total_chunks} uploaded ({chunk_progress}%)')

    # FINALIZE
    finalize_data = {'command': 'FINALIZE', 'media_id': media_id}
    finalize_res = session.post(media_upload_url, data=finalize_data)
    finalize_res.raise_for_status()
    finalize_json = finalize_res.json()

    # Wait for processing if needed
    if finalize_json.get('processing_info'):
        _wait_for_processing(session, media_id, on_progress)

    return media_id


def _wait_for_processing(session, media_id, on_progress=None):
    """Wait for X media processing to complete after FINALIZE."""
    media_upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
    attempts = 0
    max_attempts = 60

    while attempts < max_attempts:
        status_res = session.get(media_upload_url, params={'command': 'STATUS', 'media_id': media_id})
        info = status_res.json().get('processing_info')

        if not info or info.get('state') == 'succeeded':
            return
        if info.get('state') == 'failed':
            err_msg = info.get('error', {}).get('message', 'Video processing failed on X')
            raise Exception(err_msg)

        wait_seconds = info.get('check_after_secs', 5)
        if on_progress:
            on_progress(90 + min(attempts, 9))
        time.sleep(wait_seconds)
        attempts += 1

    raise Exception('X video processing timed out')


def post_to_x(video_path, title, description):
    """Posts a video to X (formerly Twitter) using the X API."""
    api_key = os.environ.get('X_API_KEY')
    api_secret = os.environ.get('X_API_SECRET')
    access_token = os.environ.get('X_ACCESS_TOKEN')
    access_secret = os.environ.get('X_ACCESS_SECRET')

    if not api_key or not api_secret or not access_token or not access_secret:
        return {
            'success': False,
            'error': 'X credentials not configured. Go to Settings to add your API Key, API Secret, Access Token, and Access Secret.',
        }

    try:
        session = _get_oauth1_session()
        file_size = os.path.getsize(video_path)
        print(f'   X: Uploading video {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f} MB)...')

        media_id = _chunked_media_upload(session, video_path)
        print(f'   X: Video uploaded, media ID: {media_id}')

        tweet_text = _build_tweet_text(title, description)

        # Create tweet via v2 API
        tweet_res = session.post(
            'https://api.twitter.com/2/tweets',
            json={
                'text': tweet_text,
                'media': {'media_ids': [media_id]},
            },
        )

        if tweet_res.status_code != 201:
            tweet_data = tweet_res.json()
            detail = tweet_data.get('detail', tweet_data.get('title', ''))
            if 'credit' in detail.lower():
                return {
                    'success': False,
                    'error': 'X: API credits depleted. Your X API free tier credits are used up. Please upgrade your plan at developer.x.com or wait for credits to reset.',
                }
            raise Exception(detail or str(tweet_data))

        tweet_data = tweet_res.json()
        tweet_id = tweet_data['data']['id']
        print(f'   X: Tweet posted! Tweet ID: {tweet_id}')

        return {
            'success': True,
            'tweetId': tweet_id,
            'tweetUrl': f'https://x.com/i/status/{tweet_id}',
            'message': f'Video posted to X! Tweet ID: {tweet_id}',
        }
    except Exception as e:
        err_msg = _extract_x_error(e)
        print(f'X posting error: {err_msg}')
        return {'success': False, 'error': f'X: {err_msg}'}


def pre_upload_to_x(video_path, title, description, on_progress=None):
    """Pre-upload: Upload video to X media endpoint WITHOUT creating a tweet."""
    api_key = os.environ.get('X_API_KEY')
    api_secret = os.environ.get('X_API_SECRET')
    access_token = os.environ.get('X_ACCESS_TOKEN')
    access_secret = os.environ.get('X_ACCESS_SECRET')

    if not api_key or not api_secret or not access_token or not access_secret:
        return {'success': False, 'error': 'X credentials not configured.'}

    try:
        session = _get_oauth1_session()
        if on_progress:
            on_progress(2)

        file_size = os.path.getsize(video_path)
        print(f'   X: Pre-uploading video {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f} MB)...')

        media_id = _chunked_media_upload(session, video_path, on_progress)

        if on_progress:
            on_progress(100)
        print(f'   X: Pre-upload complete! Media ID: {media_id}')

        return {
            'success': True,
            'mediaId': media_id,
            'message': 'Video pre-uploaded to X (ready to tweet)',
        }
    except Exception as e:
        err_msg = _extract_x_error(e)
        print(f'X pre-upload error: {err_msg}')
        return {'success': False, 'error': f'X: {err_msg}'}


def publish_x_tweet(media_id, title, description):
    """Publish a previously pre-uploaded X video by creating a tweet."""
    try:
        session = _get_oauth1_session()
        tweet_text = _build_tweet_text(title, description)

        tweet_res = session.post(
            'https://api.twitter.com/2/tweets',
            json={
                'text': tweet_text,
                'media': {'media_ids': [media_id]},
            },
        )

        if tweet_res.status_code != 201:
            tweet_data = tweet_res.json()
            raise Exception(tweet_data.get('detail', str(tweet_data)))

        tweet_data = tweet_res.json()
        tweet_id = tweet_data['data']['id']

        return {
            'success': True,
            'tweetId': tweet_id,
            'tweetUrl': f'https://x.com/i/status/{tweet_id}',
            'message': f'Video published on X! Tweet ID: {tweet_id}',
        }
    except Exception as e:
        err_msg = _extract_x_error(e)
        print(f'X publish error: {err_msg}')
        return {'success': False, 'error': f'X: {err_msg}'}
