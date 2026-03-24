import os
import time
import random
from werkzeug.utils import secure_filename

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

VIDEO_MIMETYPES = {
    'video/mp4',
    'video/quicktime',      # .mov
    'video/x-msvideo',      # .avi
    'video/x-matroska',     # .mkv
    'video/webm',
}

IMAGE_MIMETYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
}

ALLOWED_MIMETYPES = VIDEO_MIMETYPES | IMAGE_MIMETYPES

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


def _detect_media_type(file_storage, original_name):
    mimetype = (file_storage.mimetype or '').lower()
    ext = os.path.splitext(original_name)[1].lower()

    if mimetype in VIDEO_MIMETYPES or ext in VIDEO_EXTENSIONS:
        return 'video'
    if mimetype in IMAGE_MIMETYPES or ext in IMAGE_EXTENSIONS:
        return 'image'
    return None


def save_upload(file_storage):
    """
    Save an uploaded file (werkzeug FileStorage) to the uploads directory.
    Returns a dict with path, originalname, size info, or raises ValueError.
    """
    if not file_storage or file_storage.filename == '':
        raise ValueError('No video file uploaded.')

    original_name = secure_filename(file_storage.filename)
    media_type = _detect_media_type(file_storage, original_name)

    if file_storage.mimetype not in ALLOWED_MIMETYPES and not media_type:
        raise ValueError(
            f'Unsupported file type: {file_storage.mimetype}. Allowed: MP4, MOV, AVI, MKV, WebM, JPG, PNG, WebP'
        )

    ext = os.path.splitext(original_name)[1]
    if not ext:
        ext = '.jpg' if media_type == 'image' else '.mp4'
    unique_suffix = f'{int(time.time() * 1000)}-{random.randint(0, 10**9)}'
    filename = f'{media_type or "file"}-{unique_suffix}{ext}'
    filepath = os.path.join(UPLOADS_DIR, filename)

    file_storage.save(filepath)
    file_size = os.path.getsize(filepath)

    return {
        'path': filepath,
        'originalname': file_storage.filename,
        'size': file_size,
        'mimetype': file_storage.mimetype,
        'mediaType': media_type,
    }
