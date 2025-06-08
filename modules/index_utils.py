from pathlib import Path
import json

INDEX_FILE = Path(__file__).resolve().parent.parent / "thumbnail_index.json"

def get_current_index():
    if not INDEX_FILE.exists():
        return []
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
