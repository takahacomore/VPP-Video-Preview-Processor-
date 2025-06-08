import os
import json
import hashlib
import subprocess
import threading
import signal
from pathlib import Path
from modules.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
from modules.settings_manager import load_settings

THUMBNAILS_DIR = Path("thumbnails")
THUMBNAILS_DIR.mkdir(exist_ok=True)

VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".mxf"]

# Флаг для остановки обработки
processing_active = False
current_process = None

def hash_path(file_path):
    return hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:16]


def format_timecode(seconds, fps=25):
    """
    Конвертирует время в секундах в профессиональный таймкод формата ЧЧ:ММ:СС:КК.
    Использует алгоритм, идентичный скрипту run_scene_detection.bat.
    
    Args:
        seconds (float): Время в секундах
        fps (int): Частота кадров в секунду (25 по умолчанию)
        
    Returns:
        str: Форматированный таймкод ЧЧ:ММ:СС:КК
    """
    # Проверка на None или невалидные значения
    if seconds is None or not isinstance(seconds, (int, float)):
        seconds = 0.0
    
    # Обработка fps
    if fps is None or not isinstance(fps, (int, float)) or fps <= 0:
        fps = 25
    
    # Вычисляем общее количество кадров (точно так же, как в батнике)
    total_frames = int(round(seconds * fps))
    
    # Вычисляем часы, минуты, секунды и кадры
    total_seconds = total_frames // fps
    frames = total_frames % fps
    
    hours = total_seconds // 3600
    total_seconds %= 3600
    
    minutes = total_seconds // 60
    seconds_int = total_seconds % 60
    
    # Профессиональный таймкод в формате ЧЧ:ММ:СС:КК
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}:{frames:02d}"


def get_duration(video_path):
    """Получает длительность видео в секундах"""
    try:
        result = subprocess.run(
            [get_ffprobe_path(), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"⚠️ Невозможно получить длительность видео: {e}")
        return None
        
def get_frame_rate(video_path):
    """Получает частоту кадров видео (FPS)"""
    try:
        result = subprocess.run(
            [get_ffprobe_path(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Результат может быть в формате "30000/1001" (для 29.97 fps)
        fps_str = result.stdout.strip()
        if '/' in fps_str:
            numerator, denominator = map(int, fps_str.split('/'))
            fps = numerator / denominator
        else:
            fps = float(fps_str)
        
        # Округляем до стандартных значений
        standard_fps = [8, 15, 24, 25, 30, 50, 60]
        for std_fps in standard_fps:
            if abs(fps - std_fps) < 0.5:
                return std_fps
        
        # Обрабатываем 29.97 и 59.94 fps
        if abs(fps - 29.97) < 0.1:
            return 29.97
        if abs(fps - 59.94) < 0.1:
            return 59.94
            
        return round(fps, 2)
    except Exception as e:
        print(f"⚠️ Невозможно получить частоту кадров: {e}")
        return 25.0  # Возвращаем стандартный FPS по умолчанию

def generate_preview_path(video_path):
    hashed = hash_path(video_path)
    preview_dir = THUMBNAILS_DIR / hashed
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir

# Эта функция заменена новой process_frames_with_pts, которая точнее рассчитывает таймкоды
# на основе номеров кадров в имени файла с использованием параметра -frame_pts
def save_description(video_path, output_folder):
    """
    Устаревшая функция для обратной совместимости.
    Теперь используется process_frames_with_pts.
    """
    # Получаем частоту кадров видео
    fps = get_frame_rate(video_path)
    # Вызываем новую функцию
    process_frames_with_pts(video_path, output_folder, fps)

def stop_processing():
    """Останавливает текущую обработку."""
    global processing_active, current_process
    
    processing_active = False
    
    if current_process:
        try:
            # Для Windows
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            # Для Unix/Linux
            else:
                os.killpg(os.getpgid(current_process.pid), signal.SIGTERM)
        except Exception as e:
            print(f"Ошибка при остановке процесса: {e}")
        
        current_process = None
        print("🛑 Обработка остановлена!")

def process_folder_recursive(folder_path: str, on_update=lambda: None):
    """
    Рекурсивно обрабатывает все видеофайлы в указанной папке и её подпапках.
    
    Args:
        folder_path (str): Путь к папке для обработки
        on_update (callable): Функция для вызова после обработки каждого файла
    """
    global processing_active
    
    processing_active = True
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not processing_active:
                return  # Выходим, если процесс был остановлен
                
            if file.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                full_path = os.path.join(root, file)
                process_video_file(full_path, on_update)

def get_frame_pts_from_filename(filename):
    """
    Извлекает номер кадра из имени файла с frame_pts.
    Для файлов в формате frame_XX.webp или preview_XXX.webp.
    
    Args:
        filename (str): Имя файла
        
    Returns:
        int: Номер кадра или None, если не удалось извлечь
    """
    try:
        # Поддерживаем оба формата: preview_000.webp и frame_123.webp
        if filename.startswith("preview_"):
            frame_number = int(filename.split("_")[1].split(".")[0])
        elif filename.startswith("frame_"):
            frame_number = int(filename.split("_")[1].split(".")[0])
        else:
            return None
            
        return frame_number
    except (ValueError, IndexError):
        return None

def calculate_timecode_from_frame_number(frame_number, fps):
    """
    Рассчитывает таймкод на основе номера кадра и fps.
    Точная реализация алгоритма из run_scene_detection.bat.
    
    Args:
        frame_number (int): Номер кадра
        fps (float): Частота кадров
        
    Returns:
        dict: Словарь с таймкодом, позицией и fps
    """
    # Преобразуем fps в целое число для расчетов (как в bat-файле)
    fps_int = int(round(fps))
    
    # Вычисляем общее число секунд и остаток (номер кадра внутри секунды)
    total_seconds = frame_number // fps_int
    remainder = frame_number % fps_int
    
    # Вычисляем позицию в секундах (для сохранения совместимости)
    position_seconds = frame_number / fps_int
    
    # Вычисляем часы, минуты, секунды
    hours = total_seconds // 3600
    total_seconds %= 3600
    
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    # Профессиональный таймкод в формате ЧЧ:ММ:СС:КК
    timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remainder:02d}"
    
    return {
        "timestamp": timecode,
        "fps": fps,
        "position": position_seconds
    }




def process_video_file(video_path: str, on_update=lambda: None):
    global processing_active, current_process

    if not processing_active:
        print(f"⚠️ Пропускаем обработку {os.path.basename(video_path)}: процесс остановлен")
        return

    if not os.path.exists(video_path) or not os.path.isfile(video_path):
        print(f"❌ Ошибка: файл не существует или не является файлом: {video_path}")
        return

    try:
        print(f"🎞️ Обработка: {os.path.basename(video_path)}")
        duration = get_duration(video_path)
        if not duration:
            print(f"⚠️ Не удалось определить длительность видео: {video_path}")
            return
    except Exception as e:
        print(f"❌ Ошибка при подготовке видео: {e}")
        return

    settings = load_settings()
    scene_detection = settings.get("scene_edit_detection", False)
    output_folder = generate_preview_path(video_path)
    fps = get_frame_rate(video_path)
    print(f"📊 FPS: {fps} | 🎬 Scene detection: {scene_detection}")

    if scene_detection:
        # Сцены: берём кадры по scene change
        output_pattern = output_folder / "preview_%03d.webp"
        command = [
            str(get_ffmpeg_path()),
            "-i", video_path,
            "-an",
            "-vf", "select='eq(n,0)+gt(scene,0.4)',scale=1280:720",
            "-vsync", "vfr",
            "-frame_pts", "1",
            "-vcodec", "libwebp",
            "-f", "image2",
            "-y", str(output_pattern)
        ]
    else:
        # Без сцен: берём кадр из середины видео
        middle_point = duration / 2
        fallback_frame = int(middle_point * fps)
        output_file = output_folder / f"preview_{fallback_frame:03d}.webp"
        command = [
            str(get_ffmpeg_path()),
            "-ss", str(middle_point),
            "-i", video_path,
            "-an",
            "-vf", "scale=1280:720",
            "-frames:v", "1",
            "-vcodec", "libwebp",
            "-f", "image2",
            "-y", str(output_file)
        ]

    print("✅ Команда FFMPEG:", ' '.join(map(str, command)))

    try:
        current_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        stdout, stderr = current_process.communicate()
        print("🧾 STDOUT:", stdout)
        print("🛑 STDERR:", stderr)
        current_process = None
    except Exception as e:
        print(f"❌ Ошибка запуска ffmpeg: {e}")
        current_process = None

    # Постобработка
    if processing_active:
        try:
            print("🕰️ Расчёт таймкодов...")
            process_frames_with_pts(video_path, output_folder, fps)
            print(f"✅ Превью сохранено в {output_folder.name}")
            on_update()
        except Exception as e:
            print(f"❌ Ошибка при расчёте таймкодов: {e}")
            import traceback
            traceback.print_exc()



def process_frames_with_pts(video_path, output_folder, fps):
    """
    Обрабатывает извлечённые кадры, вычисляя таймкод на основе номера кадра.
    Для каждого .webp файла пытается извлечь номер кадра из его имени и затем
    рассчитывает таймкод с использованием функции calculate_timecode_from_frame_number.
    Результат сохраняется в JSON-файле descriptions_loc.json.
    
    Args:
        video_path (str): Путь к исходному видео
        output_folder (str): Папка с извлечёнными кадрами
        fps (float): Частота кадров видео
    """
    print("🕰️ Расчет таймкодов для кадров...")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    mapping = {}
    # Получаем и сортируем файлы по номеру кадра
    webp_files = [f for f in os.listdir(output_folder) if f.endswith(".webp")]
    webp_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]) if "_" in x and x.split("_")[1].split(".")[0].isdigit() else 0)
    
    print(f"🖼️ Найдено {len(webp_files)} кадров для обработки")
    
    for file in webp_files:
        frame_number = get_frame_pts_from_filename(file)
        if frame_number is not None:
            timecode_info = calculate_timecode_from_frame_number(frame_number, fps)
            mapping[file] = {
                "source": str(Path(video_path).resolve()),
                **timecode_info
            }
            print(f"🕐 Кадр {file}: {timecode_info['timestamp']} @ {fps} fps")
        else:
            mapping[file] = str(Path(video_path).resolve())
            print(f"⚠️ Не удалось определить таймкод для {file}")
    
    json_path = os.path.join(output_folder, "descriptions_loc.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=4)
    
    print(f"📝 Создан JSON с таймкодами: {json_path}")
    return True


def get_thumbnail_dir_name(video_path):
    """
    Генерирует имя директории для миниатюр на основе хеша пути к видео
    
    Args:
        video_path (str): Путь к видеофайлу
        
    Returns:
        str: Имя директории для миниатюр
    """
    return hash_path(video_path)

def get_thumbnail_by_video_path(video_path):
    """
    Возвращает путь к директории с миниатюрами для указанного видео
    
    Args:
        video_path (str): Путь к видеофайлу
        
    Returns:
        Path: Путь к директории с миниатюрами или None, если не найдено
    """
    dir_name = get_thumbnail_dir_name(video_path)
    thumbnail_dir = THUMBNAILS_DIR / dir_name
    
    if thumbnail_dir.exists():
        return thumbnail_dir
    
    return None

def start_processing(file_paths=None, folder_path=None, on_update=lambda: None):
    """
    Запускает обработку указанных файлов или папки в отдельном потоке.
    
    Args:
        file_paths (list): Список путей к видеофайлам для обработки
        folder_path (str): Путь к папке для рекурсивной обработки
        on_update (callable): Функция для вызова после обработки каждого файла
    """
    global processing_active
    
    # Более подробное логирование для отладки
    if folder_path:
        print(f"🚀 Запуск обработки папки: {folder_path}")
    elif file_paths:
        if len(file_paths) == 1:
            print(f"🚀 Запуск обработки файла: {file_paths[0]}")
        else:
            print(f"🚀 Запуск обработки {len(file_paths)} файлов: {', '.join([os.path.basename(f) for f in file_paths[:3]])}{' и др.' if len(file_paths) > 3 else ''}")
    else:
        print("⚠️ Не указаны ни файлы, ни папка для обработки")
        return  # Выходим, если нечего обрабатывать
    
    # Сначала останавливаем предыдущую обработку, если есть
    if processing_active:
        print("⚠️ Остановка предыдущей обработки перед запуском новой")
        stop_processing()
    
    # Устанавливаем флаг активной обработки
    processing_active = True
    
    def process_thread():
        global processing_active
        try:
            if folder_path:
                print(f"📂 Начинаем обработку папки: {folder_path}")
                process_folder_recursive(folder_path, on_update)
            elif file_paths:
                print(f"📂 Начинаем обработку списка из {len(file_paths)} файлов")
                for i, file_path in enumerate(file_paths):
                    if not processing_active:
                        print("🛑 Обработка остановлена пользователем")
                        break  # Выходим, если процесс был остановлен
                    print(f"📌 Обработка файла {i+1}/{len(file_paths)}: {file_path}")
                    process_video_file(file_path, on_update)
            
            # По завершении всех файлов
            if processing_active:
                print("✅ Обработка всех файлов завершена!")
        except Exception as e:
            print(f"❌ Ошибка при обработке: {e}")
        finally:
            # Выключаем флаг в любом случае
            processing_active = False
            # Обязательно вызываем функцию обратного вызова при завершении
            on_update()
    
    # Запускаем обработку в отдельном потоке
    threading.Thread(target=process_thread).start()
