import json
from pathlib import Path

MEMORY_FILE = Path("memory.json")

def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

def save_memory(data):
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user_history(user_id):
    data = load_memory()
    return data.get(user_id, [])


def append_user_history(user_id, message):
    data = load_memory()

    if user_id not in data:
        data[user_id] = []

    data[user_id].append(message)

    # limit history (tránh dài quá)
    data[user_id] = data[user_id][-5:]

    save_memory(data)