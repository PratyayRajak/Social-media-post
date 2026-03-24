from flask import Blueprint
from ..controllers.post_controller import post_video

post_bp = Blueprint('post', __name__)

# POST /api/post-video — Upload video and post to selected platforms
post_bp.route('/post-video', methods=['POST'])(post_video)
