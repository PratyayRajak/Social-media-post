import os
import time
import requests

GRAPH_API_BASE = 'https://graph.threads.net/v1.0'


def post_to_threads(video_url, caption):
    """Posts a video to Threads (full flow: create container -> poll -> publish)."""
    user_id = os.environ.get('THREADS_USER_ID')
    access_token = os.environ.get('THREADS_ACCESS_TOKEN')

    if not user_id or not access_token:
        return {
            'success': False,
            'error': 'Threads credentials not configured. Go to Settings to add your User ID and Access Token.',
        }

    try:
        # Step 1: Create media container
        container_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/threads',
            params={
                'media_type': 'VIDEO',
                'video_url': video_url,
                'text': (caption[:500] if caption else ''),
                'access_token': access_token,
            },
        )
        container_data = container_res.json()
        container_id = container_data.get('id')
        print(f'Threads: Container created — {container_id}')

        # Step 2: Poll for processing status
        status = 'IN_PROGRESS'
        attempts = 0
        max_attempts = 60

        while status == 'IN_PROGRESS' and attempts < max_attempts:
            time.sleep(5)
            attempts += 1

            status_res = requests.get(
                f'{GRAPH_API_BASE}/{container_id}',
                params={
                    'fields': 'status,error_message',
                    'access_token': access_token,
                },
            )
            status_data = status_res.json()
            status = status_data.get('status', 'IN_PROGRESS')
            error_message = status_data.get('error_message')
            print(f'Threads: Poll #{attempts} — status: {status}{f" ({error_message})" if error_message else ""}')

            if status == 'ERROR':
                err_msg = error_message or 'Unknown error during processing'
                print(f'Threads container ERROR — full status: {status_data}')
                return {'success': False, 'error': f'Threads: Processing failed — {err_msg}'}

        if status != 'FINISHED':
            return {'success': False, 'error': f'Threads: Video processing timed out. Last status: {status}'}

        # Step 3: Publish the container
        publish_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/threads_publish',
            params={'creation_id': container_id, 'access_token': access_token},
        )
        publish_data = publish_res.json()
        media_id = publish_data.get('id')

        return {
            'success': True,
            'mediaId': media_id,
            'threadUrl': f'https://www.threads.net/@me/post/{media_id}',
            'message': f'Video posted to Threads! Media ID: {media_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'Threads posting error: {err_msg}')
        return {'success': False, 'error': f'Threads: {err_msg}'}


def pre_upload_to_threads(video_url, caption, on_progress=None):
    """Pre-upload: Create container and wait until FINISHED. Does NOT publish."""
    user_id = os.environ.get('THREADS_USER_ID')
    access_token = os.environ.get('THREADS_ACCESS_TOKEN')

    if not user_id or not access_token:
        return {'success': False, 'error': 'Threads credentials not configured.'}

    try:
        if on_progress:
            on_progress(5)

        container_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/threads',
            params={
                'media_type': 'VIDEO',
                'video_url': video_url,
                'text': (caption[:500] if caption else ''),
                'access_token': access_token,
            },
        )
        container_data = container_res.json()
        container_id = container_data.get('id')
        print(f'Threads: Container created — {container_id}')
        if on_progress:
            on_progress(10)

        # Poll for processing status
        status = 'IN_PROGRESS'
        attempts = 0
        max_attempts = 60

        while status == 'IN_PROGRESS' and attempts < max_attempts:
            time.sleep(5)
            attempts += 1

            status_res = requests.get(
                f'{GRAPH_API_BASE}/{container_id}',
                params={
                    'fields': 'status,error_message',
                    'access_token': access_token,
                },
            )
            status_data = status_res.json()
            status = status_data.get('status', 'IN_PROGRESS')
            error_message = status_data.get('error_message')
            progress = min(10 + round((attempts / max_attempts) * 85), 95)
            if on_progress:
                on_progress(progress)
            print(f'Threads: Poll #{attempts} — {status} ({progress}%)')

            if status == 'ERROR':
                err_msg = error_message or 'Unknown error during processing'
                print(f'Threads container ERROR — full status: {status_data}')
                return {'success': False, 'error': f'Threads: Processing failed — {err_msg}'}

        if status != 'FINISHED':
            return {'success': False, 'error': f'Threads: Video processing timed out. Last status: {status}'}

        if on_progress:
            on_progress(100)
        return {
            'success': True,
            'containerId': container_id,
            'message': 'Video pre-uploaded to Threads (ready to publish)',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'Threads pre-upload error: {err_msg}')
        return {'success': False, 'error': f'Threads: {err_msg}'}


def publish_threads_video(container_id):
    """Publish a previously pre-uploaded Threads container."""
    user_id = os.environ.get('THREADS_USER_ID')
    access_token = os.environ.get('THREADS_ACCESS_TOKEN')

    try:
        publish_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/threads_publish',
            params={'creation_id': container_id, 'access_token': access_token},
        )
        publish_data = publish_res.json()
        media_id = publish_data.get('id')

        return {
            'success': True,
            'mediaId': media_id,
            'threadUrl': f'https://www.threads.net/@me/post/{media_id}',
            'message': f'Video published on Threads! Media ID: {media_id}',
        }
    except Exception as e:
        err_msg = str(e)
        print(f'Threads publish error: {err_msg}')
        return {'success': False, 'error': f'Threads: {err_msg}'}
