import json
import os

import requests

ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_VERSION = '2023-06-01'


def _extract_text_from_output(response_json):
    for item in response_json.get('content', []):
        if item.get('type') == 'text':
            text = item.get('text', '')
            if isinstance(text, str) and text.strip():
                return text
    return ''


def _strip_json_fences(text):
    cleaned = text.strip()
    if cleaned.startswith('```'):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        cleaned = '\n'.join(lines).strip()
    return cleaned


def _platform_guidance(platform):
    guidance = {
        'facebook': 'Write a conversational promotional caption. Keep it readable and not overloaded with hashtags.',
        'instagram': 'Write for Instagram. Make it visually engaging, tighter, and optionally include a few relevant hashtags.',
        'youtube': 'Create a strong YouTube title and a fuller YouTube description with a call to action if appropriate.',
        'linkedin': 'Write in a professional tone suitable for LinkedIn. Focus on clarity, credibility, and business relevance.',
    }
    return guidance.get(platform, f'Adapt the copy for {platform}.')


def _build_system_prompt():
    return (
        'You adapt one base social media post into platform-specific copy. '
        'You must return valid JSON only, with no markdown, no code fences, and no extra commentary. '
        'For each platform, preserve the message while adapting tone, format, and length. '
        'Do not invent facts, offers, claims, or links.'
    )


def _build_user_prompt(title, description, media_type, platforms):
    platform_lines = '\n'.join(
        f'- {platform}: {_platform_guidance(platform)}'
        for platform in platforms
    )

    json_shape = {
        platform: {
            'title': 'string',
            'description': 'string',
        }
        for platform in platforms
    }

    return (
        f'Media type: {media_type}\n'
        f'Base title: {title}\n'
        f'Base description: {description}\n'
        'Return a JSON object matching this exact shape:\n'
        f'{json.dumps(json_shape, indent=2)}\n'
        'Platform requirements:\n'
        f'{platform_lines}'
    )


def generate_platform_captions(title, description, media_type, platforms):
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError('Anthropic API key not configured. Add it in Settings first.')

    model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')
    payload = {
        'model': model,
        'max_tokens': 1200,
        'system': _build_system_prompt(),
        'messages': [
            {
                'role': 'user',
                'content': _build_user_prompt(title, description, media_type, platforms),
            }
        ],
    }

    response = requests.post(
        ANTHROPIC_MESSAGES_URL,
        headers={
            'x-api-key': api_key,
            'anthropic-version': ANTHROPIC_VERSION,
            'content-type': 'application/json',
        },
        json=payload,
        timeout=60,
    )

    if response.status_code >= 400:
        try:
            data = response.json()
            message = data.get('error', {}).get('message') or str(data)
        except Exception:
            message = response.text
        raise Exception(f'Anthropic request failed: {message}')

    data = response.json()
    text = _extract_text_from_output(data)
    if not text:
        raise Exception('Anthropic returned no caption content.')

    cleaned = _strip_json_fences(text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise Exception(f'Anthropic returned invalid JSON: {exc}') from exc

    normalized = {}
    for platform in platforms:
        content = parsed.get(platform) or {}
        normalized[platform] = {
            'title': str(content.get('title') or title).strip(),
            'description': str(content.get('description') or description or title).strip(),
        }

    return normalized
