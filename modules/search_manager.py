import inspect
if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        from inspect import getfullargspec
        spec = getfullargspec(func)
        return spec.args, spec.varargs, spec.varkw, spec.defaults
    inspect.getargspec = getargspec

import os
import re
import json
import time
import threading
import gc
import logging
from pathlib import Path
import chardet
import pymorphy2
import rapidfuzz
morph = pymorphy2.MorphAnalyzer()

from modules.settings_manager import load_settings
from modules.mistral_client import parallel_rank_frames
from modules.index_utils import get_current_index

# Директория для новых чанков
CACHE_DIR = Path("Cache")
CACHE_DIR.mkdir(exist_ok=True)

BLOCKS_PER_FILE = 100

# Патч для совместимости inspect.getargspec
def fake_getargspec(func):
    spec = inspect.getfullargspec(func)
    return (spec.args, spec.varargs, spec.varkw, spec.defaults)

if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = fake_getargspec
else:
    try:
        inspect.getargspec(lambda a, b: None)
    except Exception:
        inspect.getargspec = fake_getargspec

# Логгер
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Глобальные
_index = {}
_last_files = set()
_search_thread = None
_stop_event = threading.Event()

# Словарь синонимов (можно расширять)
SYNONYMS = {
    'танк': ['бронетехника', 'танки', 'танковый'],
    'самолёт': ['самолет', 'авиация', 'аэроплан'],
    'солдат': ['военный', 'пехотинец', 'бойцы', 'бойцы', 'армеец'],
    'война': ['боевые действия', 'битва', 'сражение', 'конфликт'],
    # ...добавляйте свои синонимы...
}

def normalize_word(word):
    parses = morph.parse(word)
    if not parses:
        return word.lower()
    return parses[0].normal_form

def normalize_text(text):
    words = re.findall(r"\b\w{2,}\b", text.lower())
    normed = set(normalize_word(w) for w in words)
    print(f"DEBUG: исходный текст: {text}\nDEBUG: нормализованные слова: {normed}\n")
    return normed

def expand_synonyms(terms):
    expanded = set(terms)
    for t in terms:
        for syn in SYNONYMS.get(t, []):
            expanded.add(syn)
    return expanded

def save_index_chunks(index_data):
    items = list(index_data.items())
    for i in range(0, len(items), BLOCKS_PER_FILE):
        chunk = dict(items[i:i + BLOCKS_PER_FILE])
        chunk_path = CACHE_DIR / f"index_{i // BLOCKS_PER_FILE:03}.json"
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)

def load_index():
    global _index
    _index.clear()
    if not CACHE_DIR.exists():
        logger.warning("Папка Cache не найдена. Индекс не загружен.")
        return
    for file in sorted(CACHE_DIR.glob("index_*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                part = json.load(f)
                _index.update(part)
        except Exception as e:
            logger.error(f"Ошибка при загрузке {file}: {e}")

def read_file_with_detect(path):
    if not os.path.exists(path):
        return ""
    raw = open(path, 'rb').read()
    if not raw:
        return ""
    enc = chardet.detect(raw)['encoding'] or 'utf-8'
    return raw.decode(enc, errors='replace')


def build_index(thumbnails_dir="thumbnails"):
    idx = {}
    logger.info("Начинаем построение индекса...")
    
    # Проверяем существование папки
    thumbnails_path = Path(thumbnails_dir)
    if not thumbnails_path.exists():
        logger.warning(f"Папка {thumbnails_dir} не существует, создаем...")
        thumbnails_path.mkdir(parents=True, exist_ok=True)
        return idx
    
    try:
        for root, _, files in os.walk(thumbnails_dir):
            loc_json = os.path.join(root, "descriptions_loc.json")
            loc_data = {}
            if os.path.exists(loc_json):
                try:
                    loc_data = json.loads(read_file_with_detect(loc_json))
                    logger.debug(f"Загружен descriptions_loc.json из {root}")
                except Exception as e:
                    logger.error(f"Ошибка при чтении descriptions_loc.json в {root}: {e}")
                    
            for fn in files:
                if fn.lower().endswith(".webp"):
                    try:
                        rel = os.path.relpath(os.path.join(root, fn), thumbnails_dir)
                        stem = Path(fn).stem
                        parts = [stem]
                        
                        # Проверяем наличие описания в loc_data
                        key = stem if stem in loc_data else f"{stem}.webp"
                        if key in loc_data:
                            v = loc_data[key]
                            parts.append(os.path.basename(v.get("source", v) if isinstance(v, dict) else v))
                        
                        # Проверяем наличие pixtral.json
                        pix = os.path.join(root, f"{stem}_pixtral.json")
                        if os.path.exists(pix):
                            try:
                                data = json.loads(read_file_with_detect(pix))
                                description = data.get("description", "") or data.get("text", "")
                                if description:
                                    parts.append(description)
                                    logger.debug(f"Добавлено описание для {fn}")
                            except Exception as e:
                                logger.error(f"Ошибка при чтении {pix}: {e}")
                        else:
                            logger.debug(f"Файл {pix} не найден")
                        
                        text = " ".join(parts)
                        if text.strip():  # Добавляем в индекс только если есть текст
                            idx[rel] = (text, list(normalize_text(text)))
                            logger.debug(f"Добавлен в индекс: {rel}")
                        else:
                            logger.warning(f"Пропущен файл {rel} - нет текстового описания")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке файла {fn}: {e}")
                        continue
    except Exception as e:
        logger.error(f"Ошибка при построении индекса: {e}")
    
    logger.info(f"Индекс построен, содержит {len(idx)} элементов")
    return idx

def search_in_index(query):
    if not query.strip():
        return list(_index.keys())
    terms = normalize_text(query)
    return [p for p, (_, norm) in _index.items() if any(any(t in n for n in norm) for t in terms)]

def smart_keyword_search(query, fuzz_threshold=90, min_score=1):
    if not query.strip():
        return list(_index.keys())
    terms = normalize_text(query)
    terms = expand_synonyms(terms)
    results = []
    for p, (text, norm) in _index.items():
        score = 0
        for t in terms:
            for n in norm:
                # 1. Точное совпадение или морфология
                if t == n:
                    score += 3
                # 2. Совпадение по началу слова
                elif n.startswith(t) or t.startswith(n):
                    score += 2
                # 3. Фаззи-поиск (опечатки)
                elif rapidfuzz.fuzz.ratio(t, n) >= fuzz_threshold:
                    score += 1
        if score >= min_score:
            results.append((score, p))
    results.sort(reverse=True)
    return [p for score, p in results]

def enable_smart_search():
    pass

def disable_smart_search():
    global _smart_model
    _smart_model = None
    gc.collect()

def smart_search(query, top_k=50, force=False):
    logger.info("Smart search called: query=%r, force=%s", query, force)
    if not (force or load_settings().get("smart_search_enabled", False)):
        return []
    if not force:
        return []

    if not list(CACHE_DIR.glob("index_*.json")):
        _index = build_index()
        save_index_chunks(_index)

    index_chunks = []
    for file in sorted(CACHE_DIR.glob("index_*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                part = json.load(f)
                index_chunks.append(part)
        except Exception as e:
            logger.error(f"Ошибка при загрузке {file}: {e}")

    try:
        return parallel_rank_frames(query=query, list_of_indexes=index_chunks)
    except Exception:
        logger.exception("Ошибка в parallel_rank_frames")
        return []

def start_search_monitoring(thumbnails_dir="thumbnails"):
    global _search_thread, _last_files, _index
    
    # Проверяем существование папки
    thumbnails_path = Path(thumbnails_dir)
    if not thumbnails_path.exists():
        logger.warning(f"Папка {thumbnails_dir} не существует, создаем...")
        thumbnails_path.mkdir(parents=True, exist_ok=True)
    
    if _search_thread and _search_thread.is_alive():
        return
        
    load_index()
    _last_files = {
        os.path.join(dp, f)
        for dp, _, fs in os.walk(thumbnails_dir)
        for f in fs if f.lower().endswith((".webp", "_pixtral.json"))
    }
    _stop_event.clear()

    def monitor():
        global _index, _last_files
        while not _stop_event.is_set():
            try:
                curr = {
                    os.path.join(dp, f)
                    for dp, _, fs in os.walk(thumbnails_dir)
                    for f in fs if f.lower().endswith((".webp", "_pixtral.json"))
                }
                
                # Проверяем изменения в файлах
                needs_rebuild = False
                
                # Проверяем наличие новых файлов
                if curr != _last_files:
                    needs_rebuild = True
                    logger.info("Обнаружены новые файлы")
                
                # Проверяем время модификации файлов
                if not needs_rebuild:
                    for file_path in curr:
                        try:
                            mtime = os.path.getmtime(file_path)
                            if mtime > time.time() - 30:  # Уменьшаем интервал до 30 секунд
                                needs_rebuild = True
                                logger.info(f"Обнаружен измененный файл: {file_path}")
                                break
                        except Exception as e:
                            logger.error(f"Ошибка при проверке времени модификации {file_path}: {e}")
                
                if needs_rebuild:
                    logger.info("Обнаружены изменения, перестраиваем индекс")
                    _index = build_index(thumbnails_dir)
                    save_index_chunks(_index)
                    _last_files = curr
                    logger.info(f"Индекс перестроен, содержит {len(_index)} элементов")
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
            time.sleep(2)  # Уменьшаем интервал проверки до 2 секунд

    _search_thread = threading.Thread(target=monitor, daemon=True)
    _search_thread.start()

def stop_search_monitoring():
    _stop_event.set()
    disable_smart_search()

def very_smart_filter(paths, query):

    
    from modules.pixtral_api import PixtralAPI
    settings = load_settings()
    thumbs = settings.get("thumbnails_folder", "thumbnails")
    keys = settings.get("api_keys", [])
    logger.info(f"[Pixtral] very_smart_filter запущен: {len(paths)} путей, запрос: '{query}'")
    chunks = [paths[i::len(keys)] for i in range(len(keys))]
    logger.info(f"[Pixtral] Распараллелено на {len(chunks)} чанков (по ключам)")    
    cache_path = "very_smart_cache.json"
    cache = json.load(open(cache_path, "r", encoding="utf-8")) if os.path.exists(cache_path) else {}
    out = []
    lock = threading.Lock()
    threads = []

    chunks = [paths[i::len(keys)] for i in range(len(keys))]

    for i, chunk in enumerate(chunks):
        def worker(sublist):
            pix = PixtralAPI()
            local_out = []
            for p in sublist:
                key_cache = f"{query}|{p}"
                if cache.get(key_cache) == "yes":
                    local_out.append(p)
                    continue
                full = os.path.join(thumbs, p)
                if not os.path.exists(full):
                    cache[key_cache] = "no"
                    continue
                try:
                    ok = pix.ask_yes_no(full, query)
                    cache[key_cache] = "yes" if ok else "no"
                    if ok:
                        local_out.append(p)
                except Exception as e:
                    logger.error("Pixtral error: %s", e)
            with lock:
                out.extend(local_out)
        t = threading.Thread(target=worker, args=(chunk,))
        t.start()
        threads.append(t)
        time.sleep(1.1)

    for t in threads:
        t.join()
    logger.info(f"[Pixtral] Завершено: {len(out)} релевантных кадров найдено")

    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return out

def get_current_index():
    return _index
