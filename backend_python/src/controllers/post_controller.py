import json
import os
import threading

from flask import jsonify, request

from ..middleware.upload import save_upload
from ..services.facebook_service import post_image_to_facebook, post_to_facebook
from ..services.filehost_service import upload_to_temp_host
from ..services.history_service import add_history_entry
from ..services.instagram_service import post_image_to_instagram, post_to_instagram
from ..services.linkedin_service import post_image_to_linkedin, post_to_linkedin
from ..services.post_content_service import parse_platform_content, resolve_platform_content
from ..services.platform_rules import format_invalid_platform_message, get_invalid_platforms
from ..services.youtube_service import post_to_youtube


def _get_public_media_url(media_path):
    public_url = os.environ.get('PUBLIC_URL')
    if public_url:
        filename = os.path.basename(media_path)
        url = f'{public_url}/uploads/{filename}'
        print(f'   Using public URL: {url}')
        return url

    print('   No ngrok tunnel - falling back to tmpfiles.org')
    return upload_to_temp_host(media_path)


def _cleanup_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            print(f'   Cleaned up: {os.path.basename(file_path)}')
    except Exception as e:
        print(f'Cleanup error: {e}')


def _parse_platforms(platforms_raw):
    if isinstance(platforms_raw, str):
        try:
            return json.loads(platforms_raw)
        except (json.JSONDecodeError, ValueError):
            return [p.strip() for p in platforms_raw.split(',') if p.strip()]
    if isinstance(platforms_raw, list):
        return platforms_raw
    return []


def post_video():
    """POST /api/post-video - Upload media and post to selected platforms."""
    try:
        media_file = request.files.get('media') or request.files.get('video')
        try:
            file_info = save_upload(media_file)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        platforms_raw = request.form.get('platforms', '[]')
        platform_content_raw = request.form.get('platformContent', '{}')

        if not title:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Title is required.'}), 400

        selected_platforms = _parse_platforms(platforms_raw)
        if not selected_platforms:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Select at least one platform.'}), 400

        media_type = file_info.get('mediaType') or 'video'
        invalid_platforms = get_invalid_platforms(selected_platforms, media_type)
        if invalid_platforms:
            _cleanup_file(file_info['path'])
            return jsonify({'error': format_invalid_platform_message(invalid_platforms, media_type)}), 400

        media_path = file_info['path']
        caption = description or title
        platform_content = parse_platform_content(platform_content_raw)
        public_media_url = None

        if media_type == 'image' and 'instagram' in selected_platforms:
            public_media_url = _get_public_media_url(media_path)

        print(f'\nPosting {media_type} to: {", ".join(selected_platforms)}')
        print(f'   Title: {title}')
        print(f'   File:  {file_info["originalname"]} ({file_info["size"] / 1024 / 1024:.1f} MB)\n')

        results = [None] * len(selected_platforms)

        def run_platform(idx, platform):
            content = resolve_platform_content(platform_content, platform, title, caption)
            platform_title = content['title']
            platform_description = content['description']

            if media_type == 'video':
                if platform == 'facebook':
                    result = post_to_facebook(media_path, platform_title, platform_description)
                elif platform == 'instagram':
                    result = post_to_instagram(media_path, platform_description)
                elif platform == 'youtube':
                    result = post_to_youtube(media_path, platform_title, platform_description)
                elif platform == 'linkedin':
                    result = post_to_linkedin(media_path, platform_title, platform_description)
                else:
                    result = {'success': False, 'error': f'Unknown platform: {platform}'}
            else:
                if platform == 'facebook':
                    result = post_image_to_facebook(media_path, platform_description)
                elif platform == 'instagram':
                    result = post_image_to_instagram(public_media_url, platform_description)
                elif platform == 'linkedin':
                    result = post_image_to_linkedin(media_path, platform_title, platform_description)
                else:
                    result = {'success': False, 'error': f'{platform} does not support images in this app yet.'}

            result['platform'] = platform
            results[idx] = result

        threads = []
        for idx, platform in enumerate(selected_platforms):
            t = threading.Thread(target=run_platform, args=(idx, platform))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        for result in results:
            if result:
                icon = 'OK' if result.get('success') else 'FAIL'
                summary = result.get('message') if result.get('success') else result.get('error')
                print(f'{icon} {result["platform"]}: {summary}')

        _cleanup_file(media_path)

        all_succeeded = all(result.get('success') for result in results if result)
        any_succeeded = any(result.get('success') for result in results if result)

        add_history_entry({
            'source': 'instant',
            'title': title,
            'description': description,
            'mediaType': media_type,
            'originalName': file_info.get('originalname'),
            'fileSize': file_info.get('size'),
            'platforms': selected_platforms,
            'results': results,
            'success': all_succeeded,
            'partial': any_succeeded and not all_succeeded,
        })

        return jsonify({
            'success': all_succeeded,
            'partial': any_succeeded and not all_succeeded,
            'results': results,
            'mediaType': media_type,
        })
    except Exception as e:
        print(f'Post media error: {e}')
        if 'file_info' in locals() and file_info:
            _cleanup_file(file_info.get('path'))
        return jsonify({
            'error': 'Failed to post media.',
            'message': str(e),
        }), 500
