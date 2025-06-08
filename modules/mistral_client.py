import os
import json
import requests
import threading
import time
from pathlib import Path
import logging
from modules.index_utils import get_current_index

logger = logging.getLogger(__name__)

# Загрузка настроек
def load_settings():
    SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError("Файл settings.json не найден!")
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Извлечение имён файлов из ответа
def extract_filenames_from_response(response_text):
    lines = response_text.strip().splitlines()
    return [line.strip() for line in lines if line.strip().endswith(".webp")]

# Один запрос к Mistral по заданному ключу и подиндексу с retry
def send_mistral_request(api_key, query, index_data, prompt_template, timeout=30, max_retries=2):
    frames = [f"{path}: {data[0]}" for path, data in index_data.items() if isinstance(data, list) and data]
    if not frames:
        return []

    prompt = prompt_template.format(query=query, images="\n".join(frames))
    api_url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data_payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    for attempt in range(max_retries + 1):
        try:
            logger.info("[Mistral] Request with key: %s | %d descriptions (attempt %d)", api_key[:4] + "****", len(frames), attempt + 1)
            response = requests.post(api_url, headers=headers, json=data_payload, timeout=timeout)
            if response.status_code != 200:
                logger.warning("Mistral API Error %d: %s", response.status_code, response.text)
                continue
            content = response.json()["choices"][0]["message"]["content"]
            return extract_filenames_from_response(content)
        except requests.exceptions.Timeout:
            logger.warning("Mistral API timeout with key: %s (attempt %d)", api_key[:4] + "****", attempt + 1)
        except Exception as e:
            logger.error("Mistral error with key %s: %s (attempt %d)", api_key[:4] + "****", str(e), attempt + 1)
    return []

# Обновлённая функция — поддерживает один ключ (для обратной совместимости)
def rank_frames_with_mistral(query, index_data, top_k=5):
    settings = load_settings()
    api_keys = settings.get("api_keys", [])
    prompt_template = settings.get("prompt_templates", {}).get("smart_search", "")

    if not api_keys:
        logger.error("Нет API-ключей в настройках")
        return []
    if not prompt_template:
        logger.error("Отсутствует prompt-шаблон для smart_search")
        return []

    return send_mistral_request(api_keys[0], query, index_data, prompt_template)

# Многопоточная версия с параллельной обработкой чанков (готово к вызову)
def parallel_rank_frames(query, list_of_indexes):
    settings = load_settings()
    api_keys = settings.get("api_keys", [])
    prompt_template = settings.get("prompt_templates", {}).get("smart_search", "")

    if not api_keys:
        logger.error("Нет API-ключей для параллельной обработки")
        return []

    results = []
    lock = threading.Lock()
    threads = []

    for i, index_data in enumerate(list_of_indexes):
        if i >= len(api_keys):
            logger.warning("Недостаточно ключей для всех чанков")
            break
        key = api_keys[i]
        def worker(index=index_data, api_key=key):
            try:
                partial = send_mistral_request(api_key, query, index, prompt_template)
                with lock:
                    results.extend(partial)
            except Exception as e:
                logger.error("Ошибка в потоке Mistral: %s", str(e))

        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
        time.sleep(1.1)

    for t in threads:
        t.join()

    return results