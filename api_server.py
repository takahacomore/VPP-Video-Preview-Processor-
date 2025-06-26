import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import collections

# Добавляем родительскую директорию в путь, чтобы видеть модули
sys.path.append(os.path.dirname(__file__))

from modules import search_manager
from modules.utils import read_file_with_detect

# --- Конфигурация ---
THUMBNAILS_DIR = "thumbnails"
# Укажите абсолютный путь, если нужно
# THUMBNAILS_DIR = "J:/VPP/VPP/Видео/thumbnails"

app = Flask(__name__)

# Включаем CORS для всех маршрутов. Это позволит панели Premiere Pro
# отправлять запросы к этому серверу.
CORS(app)

# Загружаем индекс при старте
print("Загрузка поискового индекса...")
search_manager.load_index()
print("Индекс загружен.")


def get_media_info(thumbnail_path):
    """
    Извлекает полную информацию о медиафайле по пути к его миниатюре.
    """
    try:
        # thumbnail_path — это относительный путь к миниатюре, который мы и будем возвращать клиенту.
        # Для внутренних операций нам нужен абсолютный путь.
        abs_thumb_path = os.path.abspath(os.path.join(THUMBNAILS_DIR, thumbnail_path))
        
        base = os.path.splitext(abs_thumb_path)[0]
        file_name_no_ext = os.path.basename(base)

        # 1. Получаем описание из _pixtral.json
        pixtral_json_path = f"{base}_pixtral.json"
        description = ""
        if os.path.exists(pixtral_json_path):
            pixtral_data = json.loads(read_file_with_detect(pixtral_json_path))
            description = pixtral_data.get("text", "")

        # 2. Получаем source, timestamp, fps из descriptions_loc.json
        loc_json_path = os.path.join(os.path.dirname(abs_thumb_path), "descriptions_loc.json")
        source = ""
        timestamp = ""
        fps = ""
        
        if os.path.exists(loc_json_path):
            loc_data = json.loads(read_file_with_detect(loc_json_path))
            
            # Имя файла миниатюры может быть ключом с расширением или без
            key = os.path.basename(thumbnail_path)
            if key not in loc_data:
                key = os.path.splitext(key)[0]
            if key in loc_data:
                info = loc_data[key]
                if isinstance(info, dict):
                    source = info.get("source", "")
                    timestamp = info.get("timestamp", "")
                    fps = str(info.get("fps", ""))
                else:
                    # Для старого формата, где значение - это просто путь к источнику
                    source = info
                # --- FIX: Обработка пути к исходнику ---
                if source:
                    # Если путь относительный, делаем его абсолютным от папки с JSON
                    if not os.path.isabs(source):
                        source_dir = os.path.dirname(loc_json_path)
                        source = os.path.abspath(os.path.join(source_dir, source))
                    # Нормализуем путь для ОС (например, C:\path\to\file для Windows)
                    source = os.path.normpath(source)
        return {
            # --- FIX: Возвращаем относительный путь для миниатюры (с /) ---
            "thumbnail_path": thumbnail_path.replace(os.sep, '/'),
            "source_video": source,
            "timestamp": timestamp,
            "fps": fps,
            "description": description,
        }
    except Exception as e:
        print(f"Ошибка при получении информации для {thumbnail_path}: {e}")
        return None


@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    print(f"Получен поисковый запрос: '{query}'")
    
    found_paths = search_manager.smart_keyword_search(query)
    if not found_paths:
        return jsonify([])

    # Шаг 1: Получаем полную информацию для всех найденных путей
    all_found_items = []
    for path in found_paths:
        info = get_media_info(path)
        if info:
            all_found_items.append(info)

    # Шаг 2: Группируем результаты по исходному видеофайлу
    grouped_by_source = collections.defaultdict(list)
    for item in all_found_items:
        source_video = item.get("source_video")
        if source_video:
            grouped_by_source[source_video].append(item)

    final_results = []
    
    # Шаг 3: Обрабатываем каждую группу (каждое видео)
    for source_video, items in grouped_by_source.items():
        if not items:
            continue

        # Определяем путь к descriptions_loc.json для этой группы
        # (берем из первого элемента, т.к. они все из одного видео)
        first_item_thumb_path = items[0]['thumbnail_path']
        thumb_dir = os.path.dirname(os.path.abspath(os.path.join(THUMBNAILS_DIR, first_item_thumb_path)))
        loc_json_path = os.path.join(thumb_dir, "descriptions_loc.json")

        if not os.path.exists(loc_json_path):
            # Если нет JSON, то для всех элементов ставим 'end'
            for item in items:
                item['in_timecode'] = item.get('timestamp', '')
                item['out_timecode'] = 'end'
                final_results.append(item)
            continue

        with open(loc_json_path, 'r', encoding='utf-8') as f:
            descriptions_loc = json.load(f)

        # Шаг 4: Создаем полный, отсортированный список всех кадров для ДАННОГО видео
        all_frames_in_file = []
        for key, val in descriptions_loc.items():
            if isinstance(val, dict) and 'timestamp' in val:
                all_frames_in_file.append({
                    "timestamp": val['timestamp'],
                    "fps": val.get('fps', 25)
                })

        def tc_to_tuple(tc_str):
            try:
                return tuple(map(int, tc_str.split(':')))
            except (ValueError, AttributeError):
                return (0, 0, 0, 0)
        
        all_frames_in_file.sort(key=lambda x: tc_to_tuple(x['timestamp']))

        # Создаем карту для быстрого поиска индекса по таймкоду
        ts_to_idx_map = {frame['timestamp']: i for i, frame in enumerate(all_frames_in_file)}

        # Шаг 5: Вычисляем out_timecode для каждого элемента в группе
        for item in items:
            in_timecode = item.get('timestamp')
            idx = ts_to_idx_map.get(in_timecode)
            out_timecode = 'end'  # По умолчанию до конца

            if idx is not None and idx < len(all_frames_in_file) - 1:
                next_frame = all_frames_in_file[idx + 1]
                next_tc = next_frame['timestamp']
                fps = float(item.get('fps') or 25)
                
                try:
                    h, m, s, f = map(int, next_tc.split(':'))
                    total_frames = f + s*fps + m*60*fps + h*3600*fps
                    if total_frames > 0:
                        total_frames -= 1
                    
                    h_out = int(total_frames // (3600*fps))
                    m_out = int((total_frames % (3600*fps)) // (60*fps))
                    s_out = int((total_frames % (60*fps)) // fps)
                    f_out = int(total_frames % fps)
                    out_timecode = f"{h_out:02}:{m_out:02}:{s_out:02}:{f_out:02}"
                except (ValueError, TypeError) as e:
                    print(f"Error calculating out_timecode for '{next_tc}' with fps={fps}: {e}")
                    out_timecode = 'end'

            item['in_timecode'] = in_timecode
            item['out_timecode'] = out_timecode
            final_results.append(item)

    print(f"Найдено {len(final_results)} результатов.")
    return jsonify(final_results)

@app.route('/thumbnail/<path:filename>')
def get_thumbnail(filename):
    """
    Отдает файл миниатюры. Требуется для отображения в плагине.
    """
    return send_from_directory(THUMBNAILS_DIR, filename)

if __name__ == '__main__':
    # Используйте host='0.0.0.0' чтобы сделать сервер доступным по сети
    app.run(host='127.0.0.1', port=5000, debug=True) 