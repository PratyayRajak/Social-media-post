import json
import os
import threading
from datetime import datetime

from flask import jsonify, request

from ..middleware.upload import save_upload
from ..services.post_content_service import parse_platform_content
from ..services.platform_rules import format_invalid_platform_message, get_invalid_platforms
from ..services.scheduler_service import (
    add_schedule,
    delete_schedule,
    get_schedules,
    pre_upload_schedule,
)


def _cleanup_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
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


def schedule_post():
    """POST /api/schedule - Schedule media for a future time."""
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
        scheduled_at = request.form.get('scheduledAt', '')

        if not title:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Title is required.'}), 400

        if not scheduled_at:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Scheduled time is required.'}), 400

        try:
            scheduled_date = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        except ValueError:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Invalid date/time format.'}), 400

        if scheduled_date.replace(tzinfo=None) <= datetime.utcnow():
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Scheduled time must be in the future.'}), 400

        selected_platforms = _parse_platforms(platforms_raw)
        if not selected_platforms:
            _cleanup_file(file_info['path'])
            return jsonify({'error': 'Select at least one platform.'}), 400

        media_type = file_info.get('mediaType') or 'video'
        platform_content = parse_platform_content(platform_content_raw)
        invalid_platforms = get_invalid_platforms(selected_platforms, media_type)
        if invalid_platforms:
            _cleanup_file(file_info['path'])
            return jsonify({'error': format_invalid_platform_message(invalid_platforms, media_type)}), 400

        schedule = add_schedule(
            title=title,
            description=description,
            platforms=selected_platforms,
            platform_content=platform_content,
            media_type=media_type,
            media_path=file_info['path'],
            original_name=file_info['originalname'],
            file_size=file_info['size'],
            scheduled_at=scheduled_date.isoformat() if not scheduled_at.endswith('Z') else scheduled_at,
        )

        print(f'\nScheduled {media_type}: "{title}" for {scheduled_date}')
        print(f'   Platforms: {", ".join(selected_platforms)}')
        print(f'   File: {file_info["originalname"]} ({file_info["size"] / 1024 / 1024:.1f} MB)')

        if media_type == 'video':
            print('   Pre-uploading now so it is ready to publish on schedule.\n')
            t = threading.Thread(target=pre_upload_schedule, args=(schedule['id'],), daemon=True)
            t.start()
            message = (
                f'Post scheduled for {scheduled_date}. Video pre-upload has started and will publish at the scheduled time.'
            )
        else:
            print('   Image will publish directly at the scheduled time.\n')
            message = f'Post scheduled for {scheduled_date}. Image will publish at the scheduled time.'

        return jsonify({
            'success': True,
            'message': message,
            'schedule': schedule,
        }), 201
    except Exception as e:
        print(f'Schedule post error: {e}')
        return jsonify({
            'error': 'Failed to schedule post.',
            'message': str(e),
        }), 500


def list_schedules():
    """GET /api/schedules - Get all scheduled posts."""
    schedules = get_schedules()
    priority = {
        'uploading': 0,
        'ready': 1,
        'queued': 2,
        'publishing': 3,
        'completed': 4,
        'failed': 5,
    }
    schedules.sort(key=lambda item: (priority.get(item.get('status'), 99), item.get('scheduledAt', '')))
    return jsonify({'schedules': schedules})


def cancel_schedule():
    """DELETE /api/schedules/:id - Cancel/delete a scheduled post."""
    schedule_id = request.view_args.get('id')
    schedules = get_schedules()
    schedule = next((item for item in schedules if item['id'] == schedule_id), None)

    if not schedule:
        return jsonify({'error': 'Scheduled post not found.'}), 404

    if schedule.get('status') == 'publishing':
        return jsonify({'error': 'Cannot cancel a post that is currently being published.'}), 400

    deleted = delete_schedule(schedule_id)
    if deleted:
        return jsonify({'success': True, 'message': 'Scheduled post cancelled.'})
    return jsonify({'error': 'Failed to cancel scheduled post.'}), 500
