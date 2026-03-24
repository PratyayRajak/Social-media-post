import json


def parse_platform_content(raw_value):
    if not raw_value:
        return {}

    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}

    return {}


def resolve_platform_content(platform_content, platform, fallback_title, fallback_description):
    content = platform_content.get(platform) or {}
    title = (content.get('title') or fallback_title or '').strip()
    description = (content.get('description') or fallback_description or '').strip()
    return {
        'title': title,
        'description': description or title,
    }
