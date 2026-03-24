import os
import time
import subprocess
import requests

GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'

_configured_max_mb = int(os.environ.get('IG_MAX_UPLOAD_MB', '100') or '100')
_configured_upload_timeout = int(os.environ.get('IG_UPLOAD_TIMEOUT_MS', str(15 * 60 * 1000)) or str(15 * 60 * 1000))
_configured_transcode_timeout = int(os.environ.get('IG_TRANSCODE_TIMEOUT_MS', str(20 * 60 * 1000)) or str(20 * 60 * 1000))

IG_MAX_UPLOAD_MB = _configured_max_mb if _configured_max_mb > 0 else 100
IG_MAX_UPLOAD_BYTES = IG_MAX_UPLOAD_MB * 1024 * 1024
IG_UPLOAD_TIMEOUT_MS = _configured_upload_timeout if _configured_upload_timeout > 0 else 15 * 60 * 1000
IG_TRANSCODE_TIMEOUT_MS = _configured_transcode_timeout if _configured_transcode_timeout > 0 else 20 * 60 * 1000
IG_FORCE_TRANSCODE = os.environ.get('IG_FORCE_TRANSCODE', 'false').lower() == 'true'


def post_to_instagram(video_path, caption):
    """Posts a video Reel to Instagram using resumable upload."""
    user_id = os.environ.get('IG_USER_ID')
    access_token = os.environ.get('IG_ACCESS_TOKEN')

    if not user_id or not access_token:
        return {
            'success': False,
            'error': 'Instagram credentials not configured. Go to Settings to add your User ID and Access Token.',
        }

    validation = _validate_input_video(video_path)
    if not validation['success']:
        return validation

    prepared_video = None
    try:
        prepared_video = _prepare_video_for_instagram(video_path)
        container_id, upload_uri = _create_resumable_container(user_id, access_token, caption)
        _upload_video_binary(upload_uri, prepared_video['path'], access_token)

        poll_result = _wait_for_instagram_processing(container_id, access_token)
        if not poll_result['success']:
            return poll_result

        publish_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/media_publish',
            params={'creation_id': container_id, 'access_token': access_token},
        )
        publish_data = publish_res.json()

        return {
            'success': True,
            'mediaId': publish_data.get('id'),
            'message': f'Video posted to Instagram! Media ID: {publish_data.get("id")}',
        }
    except Exception as e:
        err_msg = _format_instagram_api_error(e)
        print(f'Instagram posting error: {err_msg}')
        return {'success': False, 'error': f'Instagram: {err_msg}'}
    finally:
        _cleanup_prepared_video(prepared_video)


def post_image_to_instagram(image_url, caption):
    """Posts a photo to Instagram using a public image URL."""
    user_id = os.environ.get('IG_USER_ID')
    access_token = os.environ.get('IG_ACCESS_TOKEN')

    if not user_id or not access_token:
        return {
            'success': False,
            'error': 'Instagram credentials not configured. Go to Settings to add your User ID and Access Token.',
        }

    try:
        container_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/media',
            params={
                'image_url': image_url,
                'caption': caption,
                'access_token': access_token,
            },
        )
        container_data = container_res.json()
        container_id = container_data.get('id')

        if not container_id:
            raise Exception(_extract_processing_error(container_data))

        poll_result = _wait_for_image_container(container_id, access_token)
        if not poll_result['success']:
            return poll_result

        publish_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/media_publish',
            params={'creation_id': container_id, 'access_token': access_token},
        )
        publish_data = publish_res.json()

        if publish_res.status_code != 200 or publish_data.get('error'):
            err = publish_data.get('error', {}).get('message', str(publish_data))
            raise Exception(err)

        media_id = publish_data.get('id')
        return {
            'success': True,
            'mediaId': media_id,
            'message': f'Image posted to Instagram! Media ID: {media_id}',
        }
    except Exception as e:
        err_msg = _format_instagram_api_error(e)
        print(f'Instagram image posting error: {err_msg}')
        return {'success': False, 'error': f'Instagram: {err_msg}'}


def pre_upload_to_instagram(video_path, caption, on_progress=None):
    """Pre-upload: Create container, upload binary, wait until FINISHED. Does NOT publish."""
    user_id = os.environ.get('IG_USER_ID')
    access_token = os.environ.get('IG_ACCESS_TOKEN')

    if not user_id or not access_token:
        return {'success': False, 'error': 'Instagram credentials not configured.'}

    validation = _validate_input_video(video_path)
    if not validation['success']:
        return validation

    prepared_video = None
    try:
        if on_progress:
            on_progress(5)

        prepared_video = _prepare_video_for_instagram(video_path)

        if on_progress:
            on_progress(10)
        container_id, upload_uri = _create_resumable_container(user_id, access_token, caption)

        _upload_video_binary(upload_uri, prepared_video['path'], access_token, on_progress)

        if on_progress:
            on_progress(50)
        poll_result = _wait_for_instagram_processing(container_id, access_token, on_progress)
        if not poll_result['success']:
            return poll_result

        if on_progress:
            on_progress(100)
        return {
            'success': True,
            'containerId': container_id,
            'message': 'Video pre-uploaded to Instagram (ready to publish)',
        }
    except Exception as e:
        err_msg = _format_instagram_api_error(e)
        print(f'Instagram pre-upload error: {err_msg}')
        return {'success': False, 'error': f'Instagram: {err_msg}'}
    finally:
        _cleanup_prepared_video(prepared_video)


def publish_instagram_video(container_id):
    """Publish a previously pre-uploaded Instagram container."""
    user_id = os.environ.get('IG_USER_ID')
    access_token = os.environ.get('IG_ACCESS_TOKEN')

    try:
        publish_res = requests.post(
            f'{GRAPH_API_BASE}/{user_id}/media_publish',
            params={'creation_id': container_id, 'access_token': access_token},
        )
        publish_data = publish_res.json()

        return {
            'success': True,
            'mediaId': publish_data.get('id'),
            'message': f'Video published on Instagram! Media ID: {publish_data.get("id")}',
        }
    except Exception as e:
        err_msg = _format_instagram_api_error(e)
        print(f'Instagram publish error: {err_msg}')
        return {'success': False, 'error': f'Instagram: {err_msg}'}


def _validate_input_video(video_path):
    if not video_path or not os.path.exists(video_path):
        return {'success': False, 'error': f'Instagram: Video file not found: {video_path}'}
    if os.path.getsize(video_path) <= 0:
        return {'success': False, 'error': 'Instagram: Video file is empty.'}
    return {'success': True}


def _should_transcode_for_instagram(video_path, file_size):
    if IG_FORCE_TRANSCODE:
        return True, 'IG_FORCE_TRANSCODE=true'

    ext = os.path.splitext(video_path)[1].lower()
    if ext != '.mp4':
        return True, f'input extension {ext or "(none)"} is not .mp4'

    if file_size > IG_MAX_UPLOAD_BYTES:
        return True, f'input size {file_size / 1024 / 1024:.1f} MB exceeds {IG_MAX_UPLOAD_MB} MB'

    return False, ''


def _prepare_video_for_instagram(video_path):
    input_size = os.path.getsize(video_path)
    needed, reason = _should_transcode_for_instagram(video_path, input_size)

    if not needed:
        return {'path': video_path, 'isTemp': False}

    temp_output = _build_temp_instagram_path(video_path, 'ig-ready')
    aggressive_output = _build_temp_instagram_path(video_path, 'ig-ready-small')

    print(f'   Instagram: Transcoding for compatibility ({reason})...')
    _transcode_to_instagram_ready(video_path, temp_output, aggressive=False)

    output_path = temp_output
    output_size = os.path.getsize(output_path)

    if output_size > IG_MAX_UPLOAD_BYTES:
        print(f'   Instagram: First transcode is {output_size / 1024 / 1024:.1f} MB; running stronger compression...')
        _transcode_to_instagram_ready(video_path, aggressive_output, aggressive=True)
        _safe_delete_file(temp_output)
        output_path = aggressive_output
        output_size = os.path.getsize(output_path)

    if output_size > IG_MAX_UPLOAD_BYTES:
        _safe_delete_file(output_path)
        raise Exception(
            f'Transcoded Instagram file is {output_size / 1024 / 1024:.1f} MB. '
            f'Keep source shorter or lower quality to stay under {IG_MAX_UPLOAD_MB} MB.'
        )

    print(f'   Instagram: Prepared {output_size / 1024 / 1024:.1f} MB file for upload.')
    return {'path': output_path, 'isTemp': True}


def _build_temp_instagram_path(source_path, label):
    directory = os.path.dirname(source_path)
    stamp = f'{int(time.time() * 1000)}-{os.urandom(4).hex()}'
    return os.path.join(directory, f'{label}-{stamp}.mp4')


def _transcode_to_instagram_ready(input_path, output_path, aggressive):
    crf = '30' if aggressive else '23'
    maxrate = '2500k' if aggressive else '5000k'
    bufsize = '5000k' if aggressive else '10000k'

    args = [
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-vf', "scale='if(gt(iw,1080),1080,iw)':-2",
        '-r', '30',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-profile:v', 'high',
        '-level:v', '4.1',
        '-pix_fmt', 'yuv420p',
        '-crf', crf,
        '-maxrate', maxrate,
        '-bufsize', bufsize,
        '-movflags', '+faststart',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ac', '2',
        '-ar', '48000',
        output_path,
    ]

    timeout_seconds = IG_TRANSCODE_TIMEOUT_MS / 1000
    try:
        subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=True,
        )
    except FileNotFoundError:
        raise Exception('ffmpeg is not installed or not available in PATH.')
    except subprocess.TimeoutExpired:
        raise Exception(f'ffmpeg timed out after {timeout_seconds}s')
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
        raise Exception(f'ffmpeg failed (exit {e.returncode}). {stderr}'.strip())


def _cleanup_prepared_video(prepared_video):
    if not prepared_video or not prepared_video.get('isTemp'):
        return
    _safe_delete_file(prepared_video['path'])


def _safe_delete_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f'Instagram temp cleanup error: {e}')


def _create_resumable_container(user_id, access_token, caption):
    print('   Instagram: Creating resumable upload container...')
    container_res = requests.post(
        f'{GRAPH_API_BASE}/{user_id}/media',
        params={
            'media_type': 'REELS',
            'upload_type': 'resumable',
            'caption': caption,
            'access_token': access_token,
        },
    )
    data = container_res.json()
    container_id = data.get('id')
    upload_uri = data.get('uri')
    print(f'   Instagram: Container created - {container_id}')

    if not upload_uri:
        raise Exception('No upload URI returned from Instagram.')

    return container_id, upload_uri


def _upload_video_binary(upload_uri, video_path, access_token, on_progress=None):
    file_size = os.path.getsize(video_path)
    print(f'   Instagram: Uploading {file_size / 1024 / 1024:.1f} MB directly...')

    with open(video_path, 'rb') as f:
        file_data = f.read()

    response = requests.post(
        upload_uri,
        data=file_data,
        headers={
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(file_size),
        },
        timeout=IG_UPLOAD_TIMEOUT_MS / 1000,
    )

    if on_progress:
        on_progress(50)


def _wait_for_instagram_processing(container_id, access_token, on_progress=None):
    print('   Instagram: Upload complete, waiting for processing...')

    status = 'IN_PROGRESS'
    attempts = 0
    max_attempts = 180  # Up to ~15 minutes with progressive intervals

    while status == 'IN_PROGRESS' and attempts < max_attempts:
        # Progressive polling: 3s for first 20, 5s for next 40, 10s after that
        if attempts < 20:
            time.sleep(3)
        elif attempts < 60:
            time.sleep(5)
        else:
            time.sleep(10)
        attempts += 1

        try:
            status_res = requests.get(
                f'{GRAPH_API_BASE}/{container_id}',
                params={
                    'fields': 'status_code,status',
                    'access_token': access_token,
                },
                timeout=30,
            )
            status_data = status_res.json()
        except requests.RequestException as e:
            print(f'   Instagram: Poll #{attempts} - network error: {e}')
            continue

        status = status_data.get('status_code', 'IN_PROGRESS')
        status_detail = status_data.get('status')

        progress = min(50 + round((attempts / max_attempts) * 45), 95)
        if on_progress:
            on_progress(progress)

        if status_detail:
            print(f'   Instagram: Poll #{attempts} - {status} ({status_detail})')
        else:
            print(f'   Instagram: Poll #{attempts} - {status}')

        if status == 'ERROR':
            return {'success': False, 'error': f'Instagram: Processing failed - {_extract_processing_error(status_detail)}'}

    if status != 'FINISHED':
        return {'success': False, 'error': f'Instagram: Video processing timed out after {attempts} polls. Last status: {status}. Try a shorter or smaller video, or set IG_TRANSCODE_TIMEOUT_MS higher.'}

    return {'success': True}


def _wait_for_image_container(container_id, access_token):
    status = 'IN_PROGRESS'
    attempts = 0
    max_attempts = 30

    while status == 'IN_PROGRESS' and attempts < max_attempts:
        time.sleep(2)
        attempts += 1

        status_res = requests.get(
            f'{GRAPH_API_BASE}/{container_id}',
            params={
                'fields': 'status_code,status',
                'access_token': access_token,
            },
        )
        status_data = status_res.json()
        status = status_data.get('status_code', 'FINISHED')
        status_detail = status_data.get('status')

        if status_detail:
            print(f'   Instagram: Image poll #{attempts} - {status} ({status_detail})')

        if status == 'ERROR':
            return {'success': False, 'error': f'Instagram: Processing failed - {_extract_processing_error(status_detail)}'}

    if status not in ('FINISHED', 'PUBLISHED'):
        return {'success': False, 'error': f'Instagram: Image processing timed out. Last status: {status}'}

    return {'success': True}


def _extract_processing_error(status_detail):
    if isinstance(status_detail, str):
        return status_detail
    if isinstance(status_detail, dict):
        if status_detail.get('error', {}).get('message'):
            return status_detail['error']['message']
        if status_detail.get('error_message'):
            return status_detail['error_message']
        return str(status_detail)
    return 'Unknown processing error'


def _format_instagram_api_error(error):
    if hasattr(error, 'response') and error.response is not None:
        try:
            data = error.response.json()
            return data.get('error', {}).get('message', str(error))
        except Exception:
            pass
    return str(error)
