import os
import time
import requests

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB per chunk
REQUEST_TIMEOUT = 30  # 30s for regular requests
UPLOAD_TIMEOUT = 5 * 60  # 5 min for uploads
MAX_RETRIES = 3

# Cache the page access token so we only fetch it once per server run
_cached_page_token = None


def _with_retry(fn, retries=MAX_RETRIES):
    """Retry wrapper for transient network errors."""
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except requests.exceptions.RequestException as e:
            is_transient = isinstance(e, (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ))
            if is_transient and attempt < retries:
                delay = min(1000 * (2 ** (attempt - 1)), 10000) / 1000
                print(f'   Facebook: Retry {attempt}/{retries} after network error (waiting {delay}s)...')
                time.sleep(delay)
                continue
            raise


def _get_page_access_token(page_id, user_access_token):
    """Get the Page Access Token from a User Access Token."""
    global _cached_page_token
    if _cached_page_token:
        return _cached_page_token

    try:
        res = requests.get(
            f'{GRAPH_API_BASE}/{page_id}',
            params={'fields': 'access_token', 'access_token': user_access_token},
        )
        data = res.json()
        if data.get('access_token'):
            _cached_page_token = data['access_token']
            print('   Facebook: Resolved Page Access Token from User token')
            return _cached_page_token
    except Exception:
        print('   Facebook: Could not get Page token, using provided token directly')

    return user_access_token


def post_to_facebook(video_path, title, description):
    """Posts a video to a Facebook Page using the Graph API."""
    page_id = os.environ.get('FB_PAGE_ID')
    user_token = os.environ.get('FB_ACCESS_TOKEN')

    if not page_id or not user_token:
        return {
            'success': False,
            'error': 'Facebook credentials not configured. Go to Settings to add your Page ID and Access Token.',
        }

    try:
        access_token = _get_page_access_token(page_id, user_token)
        file_size = os.path.getsize(video_path)

        if file_size < 20 * 1024 * 1024:
            return _simple_upload(page_id, access_token, video_path, title, description)
        else:
            return _chunked_upload(page_id, access_token, video_path, title, description, file_size)
    except Exception as e:
        err_msg = str(e)
        print(f'Facebook posting error: {err_msg}')
        return {'success': False, 'error': f'Facebook: {err_msg}'}


def post_image_to_facebook(image_path, caption):
    """Posts an image to a Facebook Page using the Graph API."""
    page_id = os.environ.get('FB_PAGE_ID')
    user_token = os.environ.get('FB_ACCESS_TOKEN')

    if not page_id or not user_token:
        return {
            'success': False,
            'error': 'Facebook credentials not configured. Go to Settings to add your Page ID and Access Token.',
        }

    try:
        access_token = _get_page_access_token(page_id, user_token)

        with open(image_path, 'rb') as f:
            response = requests.post(
                f'{GRAPH_API_BASE}/{page_id}/photos',
                files={'source': f},
                data={
                    'caption': caption,
                    'access_token': access_token,
                },
                timeout=UPLOAD_TIMEOUT,
            )

        data = response.json()
        if response.status_code != 200 or data.get('error'):
            err = data.get('error', {}).get('message', str(data))
            return {'success': False, 'error': f'Facebook: {err}'}

        post_id = data.get('post_id') or data.get('id')
        return {
            'success': True,
            'postId': post_id,
            'message': f'Image posted to Facebook! Post ID: {post_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'Facebook image posting error: {err_msg}')
        return {'success': False, 'error': f'Facebook: {err_msg}'}


def pre_upload_to_facebook(video_path, title, description, on_progress=None):
    """Pre-upload a video to Facebook WITHOUT publishing (published=false)."""
    page_id = os.environ.get('FB_PAGE_ID')
    user_token = os.environ.get('FB_ACCESS_TOKEN')

    if not page_id or not user_token:
        return {'success': False, 'error': 'Facebook credentials not configured.'}

    try:
        access_token = _get_page_access_token(page_id, user_token)
        file_size = os.path.getsize(video_path)

        if file_size < 20 * 1024 * 1024:
            # Simple upload with published=false
            if on_progress:
                on_progress(50)

            with open(video_path, 'rb') as f:
                response = requests.post(
                    f'{GRAPH_API_BASE}/{page_id}/videos',
                    files={'source': f},
                    data={
                        'title': title,
                        'description': description,
                        'published': 'false',
                        'access_token': access_token,
                    },
                )

            data = response.json()
            if response.status_code != 200 or data.get('error'):
                err = data.get('error', {}).get('message', str(data))
                return {'success': False, 'error': f'Facebook: {err}'}

            if on_progress:
                on_progress(100)

            return {
                'success': True,
                'videoId': data.get('id'),
                'message': 'Video pre-uploaded to Facebook (unpublished)',
            }
        else:
            return _chunked_pre_upload(page_id, access_token, video_path, title, description, file_size, on_progress)
    except Exception as e:
        err_msg = str(e)
        print(f'Facebook pre-upload error: {err_msg}')
        return {'success': False, 'error': f'Facebook: {err_msg}'}


def publish_facebook_video(video_id):
    """Publish a previously pre-uploaded (unpublished) Facebook video."""
    page_id = os.environ.get('FB_PAGE_ID')
    user_token = os.environ.get('FB_ACCESS_TOKEN')
    access_token = _get_page_access_token(page_id, user_token)

    try:
        requests.post(
            f'{GRAPH_API_BASE}/{video_id}',
            json={'published': True, 'access_token': access_token},
        )
        return {
            'success': True,
            'postId': video_id,
            'message': f'Video published on Facebook! Post ID: {video_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'Facebook publish error: {err_msg}')
        return {'success': False, 'error': f'Facebook: {err_msg}'}


def _chunked_pre_upload(page_id, access_token, video_path, title, description, file_size, on_progress):
    """Chunked pre-upload (unpublished) with progress tracking."""
    print(f'   Facebook: Pre-uploading (chunked, {file_size / 1024 / 1024:.1f} MB)...')

    # START phase
    start_response = requests.post(
        f'{GRAPH_API_BASE}/{page_id}/videos',
        json={
            'upload_phase': 'start',
            'file_size': file_size,
            'access_token': access_token,
        },
    )
    start_data = start_response.json()
    upload_session_id = start_data['upload_session_id']
    start_video_id = start_data.get('video_id')
    print(f'   Facebook: Upload session started: {upload_session_id}, video_id: {start_video_id}')

    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    chunk_num = 0
    start_offset = 0

    with open(video_path, 'rb') as f:
        while start_offset < file_size:
            chunk_num += 1
            chunk_length = min(CHUNK_SIZE, file_size - start_offset)
            f.seek(start_offset)
            chunk_data = f.read(chunk_length)

            transfer_response = requests.post(
                f'{GRAPH_API_BASE}/{page_id}/videos',
                files={'video_file_chunk': (os.path.basename(video_path), chunk_data, 'application/octet-stream')},
                data={
                    'upload_phase': 'transfer',
                    'upload_session_id': upload_session_id,
                    'start_offset': str(start_offset),
                    'access_token': access_token,
                },
            )

            transfer_data = transfer_response.json()
            start_offset = int(transfer_data.get('start_offset', file_size))
            progress = round((chunk_num / total_chunks) * 95)
            if on_progress:
                on_progress(progress)
            print(f'   Facebook: Chunk {chunk_num}/{total_chunks} ({progress}%)')

    # FINISH with published=false
    finish_response = requests.post(
        f'{GRAPH_API_BASE}/{page_id}/videos',
        json={
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'title': title,
            'description': description,
            'published': False,
            'access_token': access_token,
        },
    )

    finish_data = finish_response.json()
    video_id = finish_data.get('id') or finish_data.get('video_id') or start_video_id
    if on_progress:
        on_progress(100)
    print(f'   Facebook: Pre-upload complete! Video ID: {video_id}')

    return {
        'success': True,
        'videoId': video_id,
        'message': 'Video pre-uploaded to Facebook (unpublished)',
    }


def _simple_upload(page_id, access_token, video_path, title, description):
    """Simple (non-resumable) upload for small video files."""
    def do_upload():
        with open(video_path, 'rb') as f:
            response = requests.post(
                f'{GRAPH_API_BASE}/{page_id}/videos',
                files={'source': f},
                data={
                    'title': title,
                    'description': description,
                    'access_token': access_token,
                },
                timeout=UPLOAD_TIMEOUT,
            )

        data = response.json()
        if data.get('error'):
            raise Exception(data['error'].get('message', str(data)))

        return {
            'success': True,
            'postId': data.get('id'),
            'message': f'Video posted to Facebook! Post ID: {data.get("id")}',
        }

    return _with_retry(do_upload)


def _chunked_upload(page_id, access_token, video_path, title, description, file_size):
    """Chunked (resumable) upload for large video files."""
    print(f'   Facebook: Using chunked upload ({file_size / 1024 / 1024:.1f} MB)...')

    # Phase 1: START
    start_response = requests.post(
        f'{GRAPH_API_BASE}/{page_id}/videos',
        json={
            'upload_phase': 'start',
            'file_size': file_size,
            'access_token': access_token,
        },
    )
    start_data = start_response.json()
    upload_session_id = start_data['upload_session_id']
    start_video_id = start_data.get('video_id')
    print(f'   Facebook: Upload session started: {upload_session_id}, video_id: {start_video_id}')

    # Phase 2: TRANSFER
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    chunk_num = 0
    start_offset = 0

    with open(video_path, 'rb') as f:
        while start_offset < file_size:
            chunk_num += 1
            chunk_length = min(CHUNK_SIZE, file_size - start_offset)
            f.seek(start_offset)
            chunk_data = f.read(chunk_length)

            transfer_response = requests.post(
                f'{GRAPH_API_BASE}/{page_id}/videos',
                files={'video_file_chunk': (os.path.basename(video_path), chunk_data, 'application/octet-stream')},
                data={
                    'upload_phase': 'transfer',
                    'upload_session_id': upload_session_id,
                    'start_offset': str(start_offset),
                    'access_token': access_token,
                },
            )

            transfer_data = transfer_response.json()
            start_offset = int(transfer_data.get('start_offset', file_size))
            print(f'   Facebook: Chunk {chunk_num}/{total_chunks} uploaded (offset: {start_offset})')

    # Phase 3: FINISH
    finish_response = requests.post(
        f'{GRAPH_API_BASE}/{page_id}/videos',
        json={
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'title': title,
            'description': description,
            'access_token': access_token,
        },
    )

    finish_data = finish_response.json()
    post_id = finish_data.get('id') or finish_data.get('video_id') or start_video_id
    print(f'   Facebook: Upload complete! Video ID: {post_id}')

    return {
        'success': True,
        'postId': post_id,
        'message': f'Video posted to Facebook! Post ID: {post_id}',
    }
