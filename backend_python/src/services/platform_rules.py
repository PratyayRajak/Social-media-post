SUPPORTED_MEDIA_BY_PLATFORM = {
    'facebook': {'image', 'video'},
    'instagram': {'image', 'video'},
    'youtube': {'video'},
    'linkedin': {'image', 'video'},
}

PLATFORM_LABELS = {
    'facebook': 'Facebook',
    'instagram': 'Instagram',
    'youtube': 'YouTube',
    'linkedin': 'LinkedIn',
}


def filter_supported_platforms(platforms, media_type):
    return [
        platform
        for platform in platforms
        if media_type in SUPPORTED_MEDIA_BY_PLATFORM.get(platform, set())
    ]


def get_invalid_platforms(platforms, media_type):
    return [
        platform
        for platform in platforms
        if media_type not in SUPPORTED_MEDIA_BY_PLATFORM.get(platform, set())
    ]


def format_invalid_platform_message(invalid_platforms, media_type):
    if not invalid_platforms:
        return None

    labels = [PLATFORM_LABELS.get(platform, platform) for platform in invalid_platforms]
    media_label = 'images' if media_type == 'image' else 'videos'
    return f'{", ".join(labels)} does not support {media_label} in this app yet.'
