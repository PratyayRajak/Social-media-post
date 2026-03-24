import json
import mimetypes
import os
import time

import requests

LINKEDIN_API_BASE = 'https://api.linkedin.com/rest'
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB per chunk (LinkedIn recommends <= 4MB)


def _get_headers(access_token):
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202602',
    }


def _extract_linkedin_error(error):
    if hasattr(error, 'response') and error.response is not None:
        try:
            data = error.response.json()
            print(f'LinkedIn API full error response: {json.dumps(data, indent=2)}')
            if data.get('errorDetails'):
                details = json.dumps(data['errorDetails'])
                return f'{data.get("message", "Validation error")} - Details: {details}'
            if data.get('message'):
                return data['message']
            if data.get('serviceErrorCode'):
                return f'Error {data["serviceErrorCode"]}: {data.get("message", "Unknown error")}'
        except Exception:
            pass
    return str(error)


def _get_owner_urn():
    org_id = os.environ.get('LI_ORG_ID')
    person_id = os.environ.get('LI_PERSON_ID')
    if org_id:
        return f'urn:li:organization:{org_id}'
    return f'urn:li:person:{person_id}'


def _initialize_upload(access_token, owner_urn, file_size):
    response = requests.post(
        f'{LINKEDIN_API_BASE}/videos?action=initializeUpload',
        json={
            'initializeUploadRequest': {
                'owner': owner_urn,
                'fileSizeBytes': file_size,
                'uploadCaptions': False,
                'uploadThumbnail': False,
            },
        },
        headers=_get_headers(access_token),
    )
    response.raise_for_status()
    data = response.json()['value']
    return {
        'videoUrn': data['video'],
        'uploadToken': data.get('uploadToken', ''),
        'uploadUrls': [
            {
                'uploadUrl': inst['uploadUrl'],
                'firstByte': inst['firstByte'],
                'lastByte': inst['lastByte'],
            }
            for inst in data['uploadInstructions']
        ],
    }


def _initialize_image_upload(access_token, owner_urn):
    response = requests.post(
        f'{LINKEDIN_API_BASE}/images?action=initializeUpload',
        json={
            'initializeUploadRequest': {
                'owner': owner_urn,
            },
        },
        headers=_get_headers(access_token),
    )
    response.raise_for_status()
    data = response.json()['value']
    return {
        'imageUrn': data['image'],
        'uploadUrl': data['uploadUrl'],
    }


def _upload_video_chunks(access_token, video_path, upload_urls, file_size, on_chunk_progress=None):
    total_chunks = len(upload_urls)
    uploaded_part_ids = []

    with open(video_path, 'rb') as f:
        for i, url_info in enumerate(upload_urls):
            chunk_size = url_info['lastByte'] - url_info['firstByte'] + 1
            f.seek(url_info['firstByte'])
            chunk_data = f.read(chunk_size)

            response = requests.put(
                url_info['uploadUrl'],
                data=chunk_data,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'Authorization': f'Bearer {access_token}',
                },
            )
            response.raise_for_status()

            etag = response.headers.get('etag', response.headers.get('ETag', ''))
            uploaded_part_ids.append(etag)

            progress = round(((i + 1) / total_chunks) * 100)
            if on_chunk_progress:
                on_chunk_progress(progress)
            print(f'   LinkedIn: Chunk {i + 1}/{total_chunks} uploaded ({progress}%)')

    return uploaded_part_ids


def _upload_image_binary(access_token, image_path, upload_url):
    content_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'

    with open(image_path, 'rb') as f:
        response = requests.put(
            upload_url,
            data=f,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': content_type,
            },
        )

    response.raise_for_status()


def _finalize_upload(access_token, video_urn, uploaded_part_ids, upload_token):
    response = requests.post(
        f'{LINKEDIN_API_BASE}/videos?action=finalizeUpload',
        json={
            'finalizeUploadRequest': {
                'video': video_urn,
                'uploadedPartIds': uploaded_part_ids,
                'uploadToken': upload_token or '',
            },
        },
        headers=_get_headers(access_token),
    )
    response.raise_for_status()


def _wait_for_processing(access_token, video_urn):
    max_attempts = 60
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        time.sleep(3)

        try:
            from urllib.parse import quote
            response = requests.get(
                f'{LINKEDIN_API_BASE}/videos/{quote(video_urn, safe="")}',
                headers=_get_headers(access_token),
            )
            data = response.json()
            status = data.get('status', '')
            print(f'   LinkedIn: Processing poll #{attempts} - status: {status}')

            if status == 'AVAILABLE':
                return
            if status in ('PROCESSING_FAILED', 'ERROR'):
                raise Exception(f'Video processing failed with status: {status}')
        except Exception as e:
            if 'processing failed' in str(e).lower():
                raise
            print(f'   LinkedIn: Processing poll #{attempts} - waiting...')

    print('   LinkedIn: Processing timeout - proceeding with post creation')


def _wait_for_image_processing(access_token, image_urn):
    max_attempts = 30
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        time.sleep(2)

        try:
            from urllib.parse import quote
            response = requests.get(
                f'{LINKEDIN_API_BASE}/images/{quote(image_urn, safe="")}',
                headers=_get_headers(access_token),
            )
            data = response.json()
            status = data.get('status', '')
            print(f'   LinkedIn: Image poll #{attempts} - status: {status}')

            if status == 'AVAILABLE':
                return
            if status in ('PROCESSING_FAILED', 'ERROR'):
                raise Exception(f'Image processing failed with status: {status}')
        except Exception as e:
            if 'processing failed' in str(e).lower():
                raise
            print(f'   LinkedIn: Image poll #{attempts} - waiting...')


def _create_post(access_token, owner_urn, video_urn, title, description):
    commentary = f'{title}\n\n{description}' if description and description != title else title

    response = requests.post(
        f'{LINKEDIN_API_BASE}/posts',
        json={
            'author': owner_urn,
            'commentary': commentary,
            'visibility': 'PUBLIC',
            'distribution': {
                'feedDistribution': 'MAIN_FEED',
                'targetEntities': [],
                'thirdPartyDistributionChannels': [],
            },
            'content': {
                'media': {
                    'title': title,
                    'id': video_urn,
                },
            },
            'lifecycleState': 'PUBLISHED',
            'isReshareDisabledByAuthor': False,
        },
        headers=_get_headers(access_token),
    )
    response.raise_for_status()

    return response.headers.get('x-restli-id', '') or response.json().get('id', video_urn)


def _create_image_post(access_token, owner_urn, image_urn, title, description):
    commentary = f'{title}\n\n{description}' if description and description != title else title

    response = requests.post(
        f'{LINKEDIN_API_BASE}/posts',
        json={
            'author': owner_urn,
            'commentary': commentary,
            'visibility': 'PUBLIC',
            'distribution': {
                'feedDistribution': 'MAIN_FEED',
                'targetEntities': [],
                'thirdPartyDistributionChannels': [],
            },
            'content': {
                'media': {
                    'title': title,
                    'id': image_urn,
                },
            },
            'lifecycleState': 'PUBLISHED',
            'isReshareDisabledByAuthor': False,
        },
        headers=_get_headers(access_token),
    )
    response.raise_for_status()

    return response.headers.get('x-restli-id', '') or response.json().get('id', image_urn)


def post_to_linkedin(video_path, title, description):
    """Posts a video to LinkedIn."""
    access_token = os.environ.get('LI_ACCESS_TOKEN')
    org_id = os.environ.get('LI_ORG_ID')
    person_id = os.environ.get('LI_PERSON_ID')

    if not access_token or (not org_id and not person_id):
        return {
            'success': False,
            'error': 'LinkedIn credentials not configured. Go to Settings to add your Access Token and either an Organization ID (for company pages) or Person ID (for personal profiles).',
        }

    owner_urn = _get_owner_urn()

    try:
        file_size = os.path.getsize(video_path)
        print(f'   LinkedIn: Uploading video ({file_size / 1024 / 1024:.1f} MB)...')

        upload_info = _initialize_upload(access_token, owner_urn, file_size)
        video_urn = upload_info['videoUrn']
        print(f'   LinkedIn: Upload initialized - {video_urn}')

        uploaded_part_ids = _upload_video_chunks(access_token, video_path, upload_info['uploadUrls'], file_size)
        print('   LinkedIn: Video chunks uploaded')

        _finalize_upload(access_token, video_urn, uploaded_part_ids, upload_info['uploadToken'])
        print('   LinkedIn: Upload finalized')

        _wait_for_processing(access_token, video_urn)

        post_urn = _create_post(access_token, owner_urn, video_urn, title, description)
        print(f'   LinkedIn: Post created - {post_urn}')

        return {
            'success': True,
            'postId': post_urn,
            'message': f'Video posted to LinkedIn! Post ID: {post_urn}',
        }
    except Exception as e:
        err_msg = _extract_linkedin_error(e)
        print(f'LinkedIn posting error: {err_msg}')

        if 'organization permission' in err_msg.lower() or 'organization as owner' in err_msg.lower():
            return {
                'success': False,
                'error': f'LinkedIn: {err_msg}. Either: (1) Your access token needs the "w_organization_social" permission for Company Page posting - go to LinkedIn Developer Portal -> request "Community Management API" -> generate a new token, OR (2) Use your Person ID instead of Organization ID in Settings to post as your personal profile (requires "w_member_social" scope).',
            }

        return {'success': False, 'error': f'LinkedIn: {err_msg}'}


def post_image_to_linkedin(image_path, title, description):
    """Posts an image to LinkedIn."""
    access_token = os.environ.get('LI_ACCESS_TOKEN')
    org_id = os.environ.get('LI_ORG_ID')
    person_id = os.environ.get('LI_PERSON_ID')

    if not access_token or (not org_id and not person_id):
        return {
            'success': False,
            'error': 'LinkedIn credentials not configured. Go to Settings to add your Access Token and either an Organization ID (for company pages) or Person ID (for personal profiles).',
        }

    owner_urn = _get_owner_urn()

    try:
        print(f'   LinkedIn: Uploading image ({os.path.basename(image_path)})...')

        upload_info = _initialize_image_upload(access_token, owner_urn)
        image_urn = upload_info['imageUrn']
        _upload_image_binary(access_token, image_path, upload_info['uploadUrl'])
        _wait_for_image_processing(access_token, image_urn)

        post_urn = _create_image_post(access_token, owner_urn, image_urn, title, description)
        print(f'   LinkedIn: Image post created - {post_urn}')

        return {
            'success': True,
            'postId': post_urn,
            'message': f'Image posted to LinkedIn! Post ID: {post_urn}',
        }
    except Exception as e:
        err_msg = _extract_linkedin_error(e)
        print(f'LinkedIn image posting error: {err_msg}')
        return {'success': False, 'error': f'LinkedIn: {err_msg}'}


def pre_upload_to_linkedin(video_path, title, description, on_progress=None):
    """Pre-upload: Upload video to LinkedIn WITHOUT creating a post."""
    access_token = os.environ.get('LI_ACCESS_TOKEN')
    org_id = os.environ.get('LI_ORG_ID')
    person_id = os.environ.get('LI_PERSON_ID')

    if not access_token or (not org_id and not person_id):
        return {'success': False, 'error': 'LinkedIn credentials not configured.'}

    owner_urn = _get_owner_urn()

    try:
        file_size = os.path.getsize(video_path)
        if on_progress:
            on_progress(5)

        print(f'   LinkedIn: Pre-uploading video ({file_size / 1024 / 1024:.1f} MB)...')

        upload_info = _initialize_upload(access_token, owner_urn, file_size)
        video_urn = upload_info['videoUrn']
        if on_progress:
            on_progress(10)

        def chunk_progress(progress):
            if on_progress:
                on_progress(10 + round(progress * 0.8))

        uploaded_part_ids = _upload_video_chunks(
            access_token,
            video_path,
            upload_info['uploadUrls'],
            file_size,
            chunk_progress,
        )

        if on_progress:
            on_progress(92)
        _finalize_upload(access_token, video_urn, uploaded_part_ids, upload_info['uploadToken'])
        if on_progress:
            on_progress(95)

        _wait_for_processing(access_token, video_urn)
        if on_progress:
            on_progress(100)

        print(f'   LinkedIn: Pre-upload complete! Video URN: {video_urn}')

        return {
            'success': True,
            'videoUrn': video_urn,
            'message': 'Video pre-uploaded to LinkedIn (ready to post)',
        }
    except Exception as e:
        err_msg = _extract_linkedin_error(e)
        print(f'LinkedIn pre-upload error: {err_msg}')

        if 'organization permission' in err_msg.lower() or 'organization as owner' in err_msg.lower():
            return {
                'success': False,
                'error': f'LinkedIn: {err_msg}. Your access token needs the "w_organization_social" permission. Go to LinkedIn Developer Portal -> request "Community Management API" -> generate a new token.',
            }

        return {'success': False, 'error': f'LinkedIn: {err_msg}'}


def publish_linkedin_video(video_urn, title, description):
    """Publish a previously pre-uploaded LinkedIn video by creating a post."""
    access_token = os.environ.get('LI_ACCESS_TOKEN')

    try:
        owner_urn = _get_owner_urn()
        post_urn = _create_post(access_token, owner_urn, video_urn, title, description)

        return {
            'success': True,
            'postId': post_urn,
            'message': f'Video published on LinkedIn! Post ID: {post_urn}',
        }
    except Exception as e:
        err_msg = _extract_linkedin_error(e)
        print(f'LinkedIn publish error: {err_msg}')
        return {'success': False, 'error': f'LinkedIn: {err_msg}'}
