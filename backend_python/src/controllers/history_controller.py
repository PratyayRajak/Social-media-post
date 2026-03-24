from flask import jsonify, request

from ..services.history_service import delete_history_entry, get_history


def list_history():
    items = get_history()
    return jsonify({'history': items})


def delete_history():
    entry_id = request.view_args.get('id')
    if not entry_id:
        return jsonify({'error': 'History item id is required.'}), 400

    deleted = delete_history_entry(entry_id)
    if not deleted:
        return jsonify({'error': 'History item not found.'}), 404

    return jsonify({'success': True, 'message': 'History item removed.'})
