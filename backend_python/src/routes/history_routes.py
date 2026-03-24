from flask import Blueprint

from ..controllers.history_controller import delete_history, list_history

history_bp = Blueprint('history', __name__)

history_bp.route('/history', methods=['GET'])(list_history)
history_bp.route('/history/<id>', methods=['DELETE'])(delete_history)
