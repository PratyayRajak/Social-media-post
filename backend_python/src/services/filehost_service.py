import os
import requests

TMPFILES_UPLOAD_URL = 'https://tmpfiles.org/api/v1/upload'


def upload_to_temp_host(file_path):
    """
    Upload a media file to a temporary file hosting service (tmpfiles.org).
    Returns a direct download URL that platform APIs can fetch.
    Files auto-expire after ~60 minutes.
    """
    print(f'   FileHost: Uploading {os.path.basename(file_path)} to tmpfiles.org...')

    with open(file_path, 'rb') as f:
        response = requests.post(
            TMPFILES_UPLOAD_URL,
            files={'file': (os.path.basename(file_path), f)},
        )

    data = response.json()
    if data.get('status') != 'success' or not data.get('data', {}).get('url'):
        raise Exception(f'tmpfiles.org upload failed: {data}')

    # Convert page URL to direct download URL
    # tmpfiles.org/12345/video.mp4 -> tmpfiles.org/dl/12345/video.mp4
    page_url = data['data']['url']
    direct_url = page_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/', 1)

    print(f'   FileHost: Upload complete — {direct_url}')
    return direct_url
