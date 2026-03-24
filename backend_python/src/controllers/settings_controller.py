import os
from flask import request, jsonify

from ..services.youtube_service import get_youtube_auth_url, exchange_youtube_code

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '.env')


def _mask_token(token):
    if not token or len(token) < 12:
        return '••••••••' if token else ''
    return token[:6] + '••••••••' + token[-4:]


def _write_env_file():
    content = f"""# PostAll Credentials
# Updated: {__import__('datetime').datetime.utcnow().isoformat()}Z

# Facebook
FB_PAGE_ID={os.environ.get('FB_PAGE_ID', '')}
FB_ACCESS_TOKEN={os.environ.get('FB_ACCESS_TOKEN', '')}

# Instagram
IG_USER_ID={os.environ.get('IG_USER_ID', '')}
IG_ACCESS_TOKEN={os.environ.get('IG_ACCESS_TOKEN', '')}

# YouTube
YT_CLIENT_ID={os.environ.get('YT_CLIENT_ID', '')}
YT_CLIENT_SECRET={os.environ.get('YT_CLIENT_SECRET', '')}
YT_REFRESH_TOKEN={os.environ.get('YT_REFRESH_TOKEN', '')}

# LinkedIn
LI_ORG_ID={os.environ.get('LI_ORG_ID', '')}
LI_PERSON_ID={os.environ.get('LI_PERSON_ID', '')}
LI_ACCESS_TOKEN={os.environ.get('LI_ACCESS_TOKEN', '')}

# AI
ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', '')}
ANTHROPIC_MODEL={os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')}

# Ngrok
NGROK_AUTHTOKEN={os.environ.get('NGROK_AUTHTOKEN', '')}
NGROK_DOMAIN={os.environ.get('NGROK_DOMAIN', '')}

# Server
PORT={os.environ.get('PORT', '5000')}
# PUBLIC_URL is set dynamically by ngrok at runtime
"""
    with open(ENV_PATH, 'w') as f:
        f.write(content)
    print('💾 Settings saved to .env')


def get_settings():
    """GET /api/settings — Returns current credentials (tokens masked)."""
    settings = {
        'facebook': {
            'pageId': os.environ.get('FB_PAGE_ID', ''),
            'accessToken': _mask_token(os.environ.get('FB_ACCESS_TOKEN')),
            'configured': bool(os.environ.get('FB_PAGE_ID') and os.environ.get('FB_ACCESS_TOKEN')),
        },
        'instagram': {
            'userId': os.environ.get('IG_USER_ID', ''),
            'accessToken': _mask_token(os.environ.get('IG_ACCESS_TOKEN')),
            'configured': bool(os.environ.get('IG_USER_ID') and os.environ.get('IG_ACCESS_TOKEN')),
        },
        'youtube': {
            'clientId': _mask_token(os.environ.get('YT_CLIENT_ID')),
            'clientSecret': _mask_token(os.environ.get('YT_CLIENT_SECRET')),
            'refreshToken': _mask_token(os.environ.get('YT_REFRESH_TOKEN')),
            'configured': bool(os.environ.get('YT_CLIENT_ID') and os.environ.get('YT_CLIENT_SECRET') and os.environ.get('YT_REFRESH_TOKEN')),
            'authUrl': get_youtube_auth_url(),
        },
        'x': {
            'apiKey': _mask_token(os.environ.get('X_API_KEY')),
            'apiSecret': _mask_token(os.environ.get('X_API_SECRET')),
            'accessToken': _mask_token(os.environ.get('X_ACCESS_TOKEN')),
            'accessSecret': _mask_token(os.environ.get('X_ACCESS_SECRET')),
            'configured': bool(os.environ.get('X_API_KEY') and os.environ.get('X_API_SECRET') and os.environ.get('X_ACCESS_TOKEN') and os.environ.get('X_ACCESS_SECRET')),
        },
        'linkedin': {
            'orgId': os.environ.get('LI_ORG_ID', ''),
            'personId': os.environ.get('LI_PERSON_ID', ''),
            'accessToken': _mask_token(os.environ.get('LI_ACCESS_TOKEN')),
            'configured': bool(os.environ.get('LI_ACCESS_TOKEN') and (os.environ.get('LI_ORG_ID') or os.environ.get('LI_PERSON_ID'))),
        },
        'ai': {
            'apiKey': _mask_token(os.environ.get('ANTHROPIC_API_KEY')),
            'model': os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest'),
            'configured': bool(os.environ.get('ANTHROPIC_API_KEY')),
        },
    }
    return jsonify(settings)


def save_settings():
    """POST /api/settings — Save credentials to .env file and update process env."""
    try:
        data = request.get_json()

        env_map = {
            'fbPageId': 'FB_PAGE_ID',
            'fbAccessToken': 'FB_ACCESS_TOKEN',
            'igUserId': 'IG_USER_ID',
            'igAccessToken': 'IG_ACCESS_TOKEN',
            'ytClientId': 'YT_CLIENT_ID',
            'ytClientSecret': 'YT_CLIENT_SECRET',
            'liOrgId': 'LI_ORG_ID',
            'liPersonId': 'LI_PERSON_ID',
            'liAccessToken': 'LI_ACCESS_TOKEN',
            'anthropicApiKey': 'ANTHROPIC_API_KEY',
            'anthropicModel': 'ANTHROPIC_MODEL',
        }

        for key, env_var in env_map.items():
            if key in data and data[key] is not None:
                os.environ[env_var] = str(data[key])

        _write_env_file()

        return jsonify({
            'success': True,
            'message': 'Settings saved successfully!',
            'youtube': {
                'authUrl': get_youtube_auth_url(),
            },
        })
    except Exception as e:
        print(f'Save settings error: {e}')
        return jsonify({'error': 'Failed to save settings.', 'message': str(e)}), 500


def youtube_auth():
    """POST /api/settings/youtube-auth — Exchange YouTube OAuth code for refresh token."""
    try:
        data = request.get_json()
        code = data.get('code', '')

        if not code:
            return jsonify({'error': 'Authorization code is required.'}), 400

        tokens = exchange_youtube_code(code)

        if tokens.get('refresh_token'):
            os.environ['YT_REFRESH_TOKEN'] = tokens['refresh_token']
            _write_env_file()

            return jsonify({
                'success': True,
                'message': 'YouTube authorized successfully! Refresh token saved.',
            })
        else:
            return jsonify({
                'error': 'No refresh token received. Try revoking access at myaccount.google.com/permissions and re-authorizing.',
            }), 400
    except Exception as e:
        print(f'YouTube auth error: {e}')
        return jsonify({
            'error': 'Failed to exchange YouTube authorization code.',
            'message': str(e),
        }), 500
