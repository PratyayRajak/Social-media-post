from flask import jsonify, request

from ..services.ai_caption_service import generate_platform_captions


def generate_captions():
    try:
        data = request.get_json() or {}
        title = str(data.get('title') or '').strip()
        description = str(data.get('description') or '').strip()
        media_type = str(data.get('mediaType') or 'video').strip().lower()
        platforms = data.get('platforms') or []

        if not title:
            return jsonify({'error': 'Title is required.'}), 400

        if not isinstance(platforms, list) or not platforms:
            return jsonify({'error': 'Select at least one platform.'}), 400

        captions = generate_platform_captions(title, description, media_type, platforms)
        return jsonify({
            'success': True,
            'platformContent': captions,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f'AI caption generation error: {e}')
        return jsonify({
            'error': 'Failed to generate platform captions.',
            'message': str(e),
        }), 500
