from flask import Blueprint
from ..controllers.settings_controller import get_settings, save_settings, youtube_auth

settings_bp = Blueprint('settings', __name__)

# GET /api/settings — Get current credentials (masked)
settings_bp.route('/settings', methods=['GET'])(get_settings)

# POST /api/settings — Save credentials to .env
settings_bp.route('/settings', methods=['POST'])(save_settings)

# POST /api/settings/youtube-auth — Exchange YouTube OAuth code for refresh token
settings_bp.route('/settings/youtube-auth', methods=['POST'])(youtube_auth)
