from flask import Blueprint

from ..controllers.ai_controller import generate_captions

ai_bp = Blueprint('ai', __name__)

ai_bp.route('/ai/platform-captions', methods=['POST'])(generate_captions)
