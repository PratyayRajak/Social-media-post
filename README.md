# PostAll

PostAll is a local web app for uploading one image or video, tailoring the content per platform, and publishing to Facebook, Instagram, YouTube, and LinkedIn from one interface.

## Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: Python + Flask

## Requirements

- Python 3.11+
- Node.js 18+

## Quick Start

### Windows

```bat
start_python.bat
```

### macOS / Linux

```bash
chmod +x start_python.sh
./start_python.sh
```

The app opens at `http://localhost:5173` and the backend runs at `http://localhost:5000`.

## Manual Setup

### Backend

```bash
cd backend_python
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python server.py
```

On macOS or Linux:

```bash
cd backend_python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Create `backend_python/.env` from `backend_python/.env.example`, then either:

- fill in the values manually, or
- start the app and save credentials from the Settings page

Credentials are stored locally in `backend_python/.env` and are not meant to be committed.

## Clean GitHub Push

The repository is set up to keep these local-only items out of Git:

- `backend_python/.env`
- `backend_python/venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend_python/data/history.json`
- `backend_python/data/schedules.json`
- `.codex-run/`

## OAuth Notes

- YouTube callback URL: `http://localhost:5000/auth/youtube/callback`
- Instagram and Threads uploads may require `NGROK_AUTHTOKEN` so the backend can expose uploaded media through a public URL
