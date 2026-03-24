import os
import threading
from dotenv import load_dotenv

# Load .env from the backend_python directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from src.app import create_app


def _start_ngrok_tunnel(port):
    """Start ngrok without blocking the backend from booting."""
    try:
        from pyngrok import ngrok as pyngrok_ngrok

        authtoken = os.environ.get('NGROK_AUTHTOKEN')
        if not authtoken:
            print('No NGROK_AUTHTOKEN set - ngrok tunnel not started.')
            print('Instagram & Threads uploads may not work without a public URL.')
            return

        pyngrok_ngrok.set_auth_token(authtoken)

        domain = os.environ.get('NGROK_DOMAIN')
        kwargs = {}
        if domain:
            kwargs['hostname'] = domain

        tunnel = pyngrok_ngrok.connect(port, 'http', **kwargs)
        ngrok_url = tunnel.public_url
        if ngrok_url.startswith('http://'):
            ngrok_url = ngrok_url.replace('http://', 'https://', 1)

        os.environ['PUBLIC_URL'] = ngrok_url
        print(f'Ngrok tunnel active: {ngrok_url}')
        print(f'Instagram & Threads will fetch videos from: {ngrok_url}/uploads/')
    except Exception as e:
        print(f'Ngrok tunnel failed to start: {e}')
        print('Instagram & Threads uploads may not work without a public URL.')


def main():
    port = int(os.environ.get('PORT', 5000))
    app = create_app()

    threading.Thread(target=_start_ngrok_tunnel, args=(port,), daemon=True).start()

    print(f'\nPostAll backend (Python) running on http://localhost:{port}\n')
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
