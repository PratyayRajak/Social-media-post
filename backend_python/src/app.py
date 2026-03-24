import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from markupsafe import escape

from .routes.post_routes import post_bp
from .routes.settings_routes import settings_bp
from .routes.schedule_routes import schedule_bp
from .routes.ai_routes import ai_bp
from .routes.history_routes import history_bp
from .services.scheduler_service import start_scheduler


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

    # Serve uploads folder statically (needed for Instagram to fetch videos)
    uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(os.path.abspath(uploads_dir), filename)

    # Register route blueprints
    app.register_blueprint(post_bp, url_prefix='/api')
    app.register_blueprint(settings_bp, url_prefix='/api')
    app.register_blueprint(schedule_bp, url_prefix='/api')
    app.register_blueprint(ai_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')

    # Start the post scheduler
    start_scheduler()

    # Health check
    @app.route('/api/health')
    def health():
        public_url = os.environ.get('PUBLIC_URL')
        return jsonify({
            'status': 'ok',
            'message': 'PostAll backend is running 🎬',
            'publicUrl': public_url,
            'ngrokActive': bool(public_url),
        })

    # YouTube OAuth callback route
    @app.route('/auth/youtube/callback')
    def youtube_callback():
        code = request.args.get('code', '')
        if code:
            escaped_code = escape(code)
            return f'''
            <html>
              <body style="font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#0f172a;color:white;">
                <div style="text-align:center;">
                  <h1>✅ YouTube Authorization Successful!</h1>
                  <p>Authorization code received. Copy this code and use it in the Settings page:</p>
                  <code style="background:#1e293b;padding:12px 24px;border-radius:8px;font-size:14px;display:block;margin:16px 0;word-break:break-all;">{escaped_code}</code>
                  <p>You can close this window now.</p>
                </div>
              </body>
            </html>
            '''
        else:
            return 'No authorization code received.'

    # Error handling
    @app.errorhandler(Exception)
    def handle_error(e):
        print(f'Server Error: {e}')
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
        }), 500

    return app
