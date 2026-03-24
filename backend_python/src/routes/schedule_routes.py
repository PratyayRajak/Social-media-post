from flask import Blueprint
from ..controllers.schedule_controller import schedule_post, list_schedules, cancel_schedule

schedule_bp = Blueprint('schedule', __name__)

# POST /api/schedule — Schedule a video post
schedule_bp.route('/schedule', methods=['POST'])(schedule_post)

# GET /api/schedules — List all scheduled posts
schedule_bp.route('/schedules', methods=['GET'])(list_schedules)

# DELETE /api/schedules/:id — Cancel a scheduled post
schedule_bp.route('/schedules/<id>', methods=['DELETE'])(cancel_schedule)
