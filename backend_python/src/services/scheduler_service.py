import json
import os
import random
import string
import threading
import time
from datetime import datetime

from .facebook_service import post_image_to_facebook, pre_upload_to_facebook, publish_facebook_video
from .filehost_service import upload_to_temp_host
from .history_service import add_history_entry
from .instagram_service import post_image_to_instagram, pre_upload_to_instagram, publish_instagram_video
from .linkedin_service import post_image_to_linkedin, pre_upload_to_linkedin, publish_linkedin_video
from .post_content_service import resolve_platform_content
from .youtube_service import pre_upload_to_youtube, publish_youtube_video

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
SCHEDULE_FILE = os.path.join(DATA_DIR, 'schedules.json')

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(SCHEDULE_FILE):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump([], f, indent=2)

_lock = threading.Lock()


def get_public_media_url(media_path):
    public_url = os.environ.get('PUBLIC_URL')
    if public_url:
        filename = os.path.basename(media_path)
        url = f'{public_url}/uploads/{filename}'
        print(f'   Using public URL: {url}')
        return url

    print('   No ngrok tunnel - falling back to tmpfiles.org')
    return upload_to_temp_host(media_path)


def get_schedules():
    with _lock:
        try:
            with open(SCHEDULE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []


def save_schedules(schedules):
    with _lock:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(schedules, f, indent=2)


def update_schedule(schedule_id, updates):
    schedules = get_schedules()
    for i, schedule in enumerate(schedules):
        if schedule['id'] == schedule_id:
            schedules[i].update(updates)
            save_schedules(schedules)
            return schedules[i]
    return None


def add_schedule(title, description, platforms, platform_content, media_type, media_path, original_name, file_size, scheduled_at):
    schedules = get_schedules()

    platform_status = {
        platform: {'phase': 'queued', 'progress': 0, 'uploadId': None, 'error': None}
        for platform in platforms
    }

    schedule_id = hex(int(time.time() * 1000))[2:] + ''.join(
        random.choices(string.ascii_lowercase + string.digits, k=5)
    )

    initial_status = 'uploading' if media_type == 'video' else 'queued'

    new_schedule = {
        'id': schedule_id,
        'title': title,
        'description': description,
        'platforms': platforms,
        'platformContent': platform_content or {},
        'mediaType': media_type,
        'mediaPath': media_path,
        'videoPath': media_path,
        'originalName': original_name,
        'fileSize': file_size,
        'scheduledAt': scheduled_at,
        'status': initial_status,
        'platformStatus': platform_status,
        'overallProgress': 0,
        'results': None,
        'createdAt': datetime.utcnow().isoformat() + 'Z',
    }

    schedules.append(new_schedule)
    save_schedules(schedules)
    return new_schedule


def delete_schedule(schedule_id):
    schedules = get_schedules()
    schedule = next((item for item in schedules if item['id'] == schedule_id), None)
    if not schedule:
        return False

    media_path = schedule.get('mediaPath') or schedule.get('videoPath')
    if schedule.get('status') in ('uploading', 'ready', 'queued') and media_path:
        try:
            if os.path.exists(media_path):
                os.unlink(media_path)
        except Exception:
            pass

    filtered = [item for item in schedules if item['id'] != schedule_id]
    save_schedules(filtered)
    return True


def pre_upload_schedule(schedule_id):
    schedules = get_schedules()
    schedule = next((item for item in schedules if item['id'] == schedule_id), None)
    if not schedule or schedule.get('mediaType', 'video') != 'video':
        return

    print(f'\nPre-uploading: "{schedule["title"]}" to {", ".join(schedule["platforms"])}')

    platforms = schedule['platforms']
    media_path = schedule.get('mediaPath') or schedule.get('videoPath')
    title = schedule['title']
    description = schedule.get('description') or title
    platform_content = schedule.get('platformContent') or {}

    def update_platform_progress(platform, progress):
        current = next((item for item in get_schedules() if item['id'] == schedule_id), None)
        if not current:
            return

        current['platformStatus'][platform]['progress'] = progress
        current['platformStatus'][platform]['phase'] = 'uploading'
        all_progress = [item['progress'] for item in current['platformStatus'].values()]
        current['overallProgress'] = round(sum(all_progress) / len(all_progress))
        update_schedule(
            schedule_id,
            {
                'platformStatus': current['platformStatus'],
                'overallProgress': current['overallProgress'],
            },
        )

    threads = []

    def process_platform(platform):
        try:
            result = None
            content = resolve_platform_content(platform_content, platform, title, description)
            platform_title = content['title']
            platform_description = content['description']

            if platform == 'facebook':
                result = pre_upload_to_facebook(media_path, platform_title, platform_description, lambda p: update_platform_progress('facebook', p))
                upload_id_key = 'videoId'
            elif platform == 'instagram':
                result = pre_upload_to_instagram(media_path, platform_description, lambda p: update_platform_progress('instagram', p))
                upload_id_key = 'containerId'
            elif platform == 'youtube':
                result = pre_upload_to_youtube(media_path, platform_title, platform_description, lambda p: update_platform_progress('youtube', p))
                upload_id_key = 'videoId'
            elif platform == 'linkedin':
                result = pre_upload_to_linkedin(media_path, platform_title, platform_description, lambda p: update_platform_progress('linkedin', p))
                upload_id_key = 'videoUrn'
            else:
                result = {'success': False, 'error': f'Unknown platform: {platform}'}
                upload_id_key = None

            current = next((item for item in get_schedules() if item['id'] == schedule_id), None)
            if not current:
                return

            if result and result.get('success'):
                current['platformStatus'][platform] = {
                    'phase': 'ready',
                    'progress': 100,
                    'uploadId': result.get(upload_id_key) if upload_id_key else None,
                    'error': None,
                }
            else:
                current['platformStatus'][platform] = {
                    'phase': 'failed',
                    'progress': 0,
                    'uploadId': None,
                    'error': result.get('error') if result else 'Unknown error',
                }

            update_schedule(schedule_id, {'platformStatus': current['platformStatus']})
        except Exception as e:
            current = next((item for item in get_schedules() if item['id'] == schedule_id), None)
            if current:
                current['platformStatus'][platform] = {
                    'phase': 'failed',
                    'progress': 0,
                    'uploadId': None,
                    'error': str(e),
                }
                update_schedule(schedule_id, {'platformStatus': current['platformStatus']})

    for platform in platforms:
        t = threading.Thread(target=process_platform, args=(platform,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    updated = next((item for item in get_schedules() if item['id'] == schedule_id), None)
    if not updated:
        return

    all_failed = all(item['phase'] == 'failed' for item in updated['platformStatus'].values())
    some_ready = any(item['phase'] == 'ready' for item in updated['platformStatus'].values())

    if all_failed:
        update_schedule(schedule_id, {'status': 'failed', 'overallProgress': 0})
        print(f'All pre-uploads failed for "{schedule["title"]}"')
    elif some_ready:
        update_schedule(schedule_id, {'status': 'ready', 'overallProgress': 100})
        print(f'Pre-upload complete for "{schedule["title"]}" - ready to publish at {schedule["scheduledAt"]}')


def publish_scheduled_post(schedule):
    schedule_id = schedule['id']
    title = schedule['title']
    description = schedule.get('description') or title
    platform_content = schedule.get('platformContent') or {}
    platforms = schedule['platforms']
    media_type = schedule.get('mediaType', 'video')
    media_path = schedule.get('mediaPath') or schedule.get('videoPath')
    platform_status = schedule.get('platformStatus', {})

    print(f'\nPublishing scheduled {media_type}: "{title}"')
    update_schedule(schedule_id, {'status': 'publishing'})

    public_media_url = None
    if media_type == 'image' and 'instagram' in platforms:
        public_media_url = get_public_media_url(media_path)

    results = []

    for platform in platforms:
        current = next((item for item in get_schedules() if item['id'] == schedule_id), None)
        if current and platform in current['platformStatus']:
            current['platformStatus'][platform]['phase'] = 'publishing'
            update_schedule(schedule_id, {'platformStatus': current['platformStatus']})

        result = None
        try:
            content = resolve_platform_content(platform_content, platform, title, description)
            platform_title = content['title']
            platform_description = content['description']

            if media_type == 'video':
                status = platform_status.get(platform)
                if not status or status.get('phase') != 'ready' or not status.get('uploadId'):
                    phase = status.get('phase', 'unknown') if status else 'unknown'
                    error_text = status.get('error', '') if status else ''
                    suffix = f' - {error_text}' if error_text else ''
                    result = {
                        'platform': platform,
                        'success': False,
                        'error': f'{platform}: Not ready to publish ({phase}){suffix}',
                    }
                elif platform == 'facebook':
                    result = {'platform': platform, **publish_facebook_video(status['uploadId'])}
                elif platform == 'instagram':
                    result = {'platform': platform, **publish_instagram_video(status['uploadId'])}
                elif platform == 'youtube':
                    result = {'platform': platform, **publish_youtube_video(status['uploadId'])}
                elif platform == 'linkedin':
                    result = {'platform': platform, **publish_linkedin_video(status['uploadId'], platform_title, platform_description)}
                else:
                    result = {'platform': platform, 'success': False, 'error': f'Unknown platform: {platform}'}
            else:
                if platform == 'facebook':
                    result = {'platform': platform, **post_image_to_facebook(media_path, platform_description)}
                elif platform == 'instagram':
                    result = {'platform': platform, **post_image_to_instagram(public_media_url, platform_description)}
                elif platform == 'linkedin':
                    result = {'platform': platform, **post_image_to_linkedin(media_path, platform_title, platform_description)}
                else:
                    result = {
                        'platform': platform,
                        'success': False,
                        'error': f'{platform} does not support scheduled images in this app yet.',
                    }

            results.append(result)

            after_publish = next((item for item in get_schedules() if item['id'] == schedule_id), None)
            if after_publish and platform in after_publish['platformStatus']:
                after_publish['platformStatus'][platform]['phase'] = 'published' if result.get('success') else 'failed'
                after_publish['platformStatus'][platform]['progress'] = 100 if result.get('success') else 0
                after_publish['platformStatus'][platform]['error'] = None if result.get('success') else result.get('error')
                update_schedule(schedule_id, {'platformStatus': after_publish['platformStatus']})
        except Exception as e:
            results.append({'platform': platform, 'success': False, 'error': str(e)})

    all_succeeded = results and all(item.get('success') for item in results)
    update_schedule(
        schedule_id,
        {
            'status': 'completed' if all_succeeded else 'failed',
            'results': results,
        },
    )

    add_history_entry({
        'source': 'scheduled',
        'title': title,
        'description': schedule.get('description', ''),
        'mediaType': media_type,
        'originalName': schedule.get('originalName'),
        'fileSize': schedule.get('fileSize'),
        'platforms': platforms,
        'results': results,
        'success': bool(all_succeeded),
        'partial': bool(results) and any(item.get('success') for item in results) and not all_succeeded,
        'scheduledAt': schedule.get('scheduledAt'),
        'scheduleId': schedule_id,
    })

    if media_path:
        def cleanup():
            time.sleep(60)
            try:
                if os.path.exists(media_path):
                    os.unlink(media_path)
                    print(f'   Cleaned up: {os.path.basename(media_path)}')
            except Exception:
                pass

        threading.Thread(target=cleanup, daemon=True).start()


def check_scheduled_posts():
    schedules = get_schedules()
    now = datetime.utcnow()

    for schedule in schedules:
        media_type = schedule.get('mediaType', 'video')
        current_status = schedule.get('status')
        if media_type == 'video' and current_status != 'ready':
            continue
        if media_type == 'image' and current_status != 'queued':
            continue

        scheduled_time = datetime.fromisoformat(schedule['scheduledAt'].replace('Z', '+00:00')).replace(tzinfo=None)
        if scheduled_time <= now:
            publish_scheduled_post(schedule)


_scheduler_thread = None
_scheduler_running = False


def _scheduler_loop():
    global _scheduler_running
    while _scheduler_running:
        try:
            check_scheduled_posts()
        except Exception as e:
            print(f'Scheduler error: {e}')
        time.sleep(15)


def start_scheduler():
    global _scheduler_thread, _scheduler_running
    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    print('Scheduler started - checking every 15 seconds')
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()

    try:
        check_scheduled_posts()
    except Exception:
        pass


def stop_scheduler():
    global _scheduler_running
    _scheduler_running = False
