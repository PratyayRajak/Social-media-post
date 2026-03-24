import json
import os
import threading
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f, indent=2)

_lock = threading.Lock()


def get_history():
    with _lock:
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []


def save_history(items):
    with _lock:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(items, f, indent=2)


def add_history_entry(entry):
    items = get_history()
    entry = {
        'id': hex(int(time.time() * 1000))[2:],
        'createdAt': datetime.utcnow().isoformat() + 'Z',
        **entry,
    }
    items.insert(0, entry)
    save_history(items[:200])
    return entry


def delete_history_entry(entry_id):
    items = get_history()
    filtered = [item for item in items if item.get('id') != entry_id]
    if len(filtered) == len(items):
        return False
    save_history(filtered)
    return True
