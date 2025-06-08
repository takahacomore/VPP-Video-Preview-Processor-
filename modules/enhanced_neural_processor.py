"""
Улучшенная версия модуля для обработки изображений с помощью Pixtral API
с поддержкой параллельной обработки несколькими API ключами
"""

import os
import json
import time
import threading
from pathlib import Path
from modules.settings_manager import load_settings
from modules.parallel_processor import ParallelProcessor
from modules.pixtral_api import PixtralAPI

class EnhancedNeuralProcessor:
    """
    Класс для автоматической обработки изображений с помощью Pixtral API
    с поддержкой параллельной обработки
    """
    def __init__(self):
        """
        Инициализирует процессор
        """
        # Загружаем настройки
        self.settings = load_settings()
        
        # Инициализируем API
        self.pixtral = PixtralAPI()
        
        # Инициализируем параллельный процессор
        self.processor = ParallelProcessor()
        
        # Флаг активности
        self.active = False
        
        # Потоки для наблюдения за файлами
        self.watch_thread = None
        
        # Папка для наблюдения
        self.watched_folder = None
        
        # Множество обработанных файлов
        self.processed_files = set()
        
        # Множество файлов в очереди на обработку
        self.queued_files = set()
        
        # Мьютекс для доступа к множествам файлов
        self.files_lock = threading.Lock()
        
        # Обработчик, вызываемый при завершении обработки файла
        self.on_file_processed = lambda path, result: None
        
    def _get_api_keys(self, api_type):
        """
        Получает API ключи из настроек или переменных окружения
        """
        # Получаем API ключи
        settings = load_settings()
        return settings.get("api_keys", [])
        
    def get_prompt(self):
        """
        Получает промпт на основе настроек
        """
        settings = load_settings()
        templates = settings.get("prompt_templates", {})
        
        # Используем шаблон для описания изображения или стандартный
        return templates.get("image_description", 
            "Опиши что изображено на этом кадре. Ответ должен быть подробным, но не слишком длинным (до 200 символов).")
            
    def watch_files(self):
        """
        Следит за появлением новых файлов для обработки
        """
        if not self.watched_folder or not os.path.exists(self.watched_folder):
            print(f"Ошибка: директория для наблюдения не существует: {self.watched_folder}")
            return
            
        print(f"Начинаем наблюдение за директорией: {self.watched_folder}")
        
        last_checked = time.time()
        
        while self.active:
            # Сканируем директорию на наличие новых файлов
            try:
                for root, _, files in os.walk(self.watched_folder):
                    for file in files:
                        if not self.active:
                            return  # Выходим, если процесс был остановлен
                            
                        # Проверяем только изображения
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            file_path = os.path.join(root, file)
                            
                            # Проверяем, нужно ли обрабатывать файл
                            if self.needs_processing(file_path):
                                with self.files_lock:
                                    if file_path not in self.processed_files and file_path not in self.queued_files:
                                        self.queued_files.add(file_path)
                                        
                                        # Запускаем обработку в отдельном потоке
                                        threading.Thread(
                                            target=self.process_image,
                                            args=(file_path,)
                                        ).start()
            except Exception as e:
                print(f"Ошибка при сканировании директории: {e}")
                
            # Ждем некоторое время перед следующим сканированием
            time.sleep(2)
            
            # Каждые 60 секунд обновляем список API ключей
            now = time.time()
            if now - last_checked > 60:
                last_checked = now
                self.processor.update_api_keys()
        
    def needs_processing(self, image_path):
        """
        Проверяет, требует ли файл обработки через Pixtral API
        """
        if not os.path.exists(image_path):
            return False
            
        # Проверяем, есть ли уже файл с результатами
        base_path = os.path.splitext(image_path)[0]
        pixtral_json = f"{base_path}_pixtral.json"
        
        # Если уже есть результат Pixtral, файл не нуждается в обработке
        if os.path.exists(pixtral_json):
            return False
            
        return True
        
    def save_pixtral_result(self, image_path, result):
        """
        Сохраняет результат Pixtral API в JSON файл
        """
        if not result:
            return
            
        base_path = os.path.splitext(image_path)[0]
        output_file = f"{base_path}_pixtral.json"
        
        try:
            data = {
                "image_path": image_path,
                "timestamp": time.time(),
                "text": result
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print(f"✅ Результат Pixtral API сохранен: {output_file}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении результата Pixtral API: {e}")
                
    def process_image(self, image_path):
        """
        Обрабатывает изображение с помощью Pixtral API
        """
        try:
            # Отмечаем, что файл в обработке
            with self.files_lock:
                self.queued_files.add(image_path)
                
            prompt = self.get_prompt()
            
            # Проверяем, существует ли уже файл с результатами Pixtral
            base_path = os.path.splitext(image_path)[0]
            pixtral_json = f"{base_path}_pixtral.json"
            
            pixtral_text = None
            
            if os.path.exists(pixtral_json):
                try:
                    with open(pixtral_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        pixtral_text = data.get("text")
                        print(f"⏩ Загружен существующий результат Pixtral: {pixtral_json}")
                except Exception as e:
                    print(f"⚠️ Ошибка при чтении существующего результата Pixtral: {e}")
                    
            # Если нет существующего результата, обрабатываем изображение с Pixtral
            if not pixtral_text:
                # Добавляем задачу в очередь
                done_event, result_queue = self.processor.add_task(
                    "pixtral",
                    self.pixtral.process_image,
                    image_path,
                    prompt,
                    language="ru"
                )
                
                # Ждем завершения
                done_event.wait()
                pixtral_text = result_queue.get()
                
                # Сохраняем результат
                if pixtral_text:
                    self.save_pixtral_result(image_path, pixtral_text)
                else:
                    print(f"⚠️ Не удалось получить ответ от Pixtral API для {image_path}")
                    
            # Вызываем обработчик завершения
            if pixtral_text and self.on_file_processed:
                self.on_file_processed(image_path, {
                    "pixtral": pixtral_text
                })
                    
            # Отмечаем, что файл обработан
            with self.files_lock:
                self.processed_files.add(image_path)
                if image_path in self.queued_files:
                    self.queued_files.remove(image_path)
                    
        except Exception as e:
            print(f"❌ Ошибка при обработке изображения {image_path}: {e}")
            
            # В случае ошибки отмечаем, что файл не в очереди
            with self.files_lock:
                if image_path in self.queued_files:
                    self.queued_files.remove(image_path)
            
    def start(self):
        """
        Запускает наблюдение за файлами и их обработку
        """
        if self.active:
            print("Процессор уже запущен")
            return
            
        self.active = True
        
        # Очищаем множества обработанных и ожидающих файлов
        with self.files_lock:
            self.processed_files.clear()
            self.queued_files.clear()
        
        # Запускаем параллельный процессор
        self.processor.start()
        
        # Запускаем наблюдение за директорией, если она указана
        if self.watched_folder:
            self.watch_thread = threading.Thread(target=self.watch_files)
            self.watch_thread.daemon = True
            self.watch_thread.start()
            
        print("✅ Нейропроцессор запущен")
        
    def stop(self):
        """
        Останавливает наблюдение за файлами
        """
        if not self.active:
            print("Процессор уже остановлен")
            return
            
        self.active = False
        
        # Останавливаем параллельный процессор
        self.processor.stop()
        
        # Ждем завершения потока наблюдения
        if self.watch_thread and self.watch_thread.is_alive():
            self.watch_thread.join(2.0)
            
        print("🛑 Нейропроцессор остановлен")

# Глобальный экземпляр процессора
_neural_processor = None

def start_enhanced_neural_processing():
    """
    Запускает улучшенную автоматическую обработку изображений
    """
    global _neural_processor
    
    settings = load_settings()
    thumbs_folder = settings.get("thumbnails_folder", "thumbnails")
    
    if not _neural_processor:
        _neural_processor = EnhancedNeuralProcessor()
        _neural_processor.watched_folder = thumbs_folder
        
    _neural_processor.start()
    
def stop_enhanced_neural_processing():
    """
    Останавливает улучшенную автоматическую обработку изображений
    """
    global _neural_processor
    
    if _neural_processor:
        _neural_processor.stop()
        
def get_enhanced_neural_processor():
    """
    Возвращает экземпляр улучшенного нейропроцессора
    """
    global _neural_processor
    
    if not _neural_processor:
        start_enhanced_neural_processing()
        
    return _neural_processor
_auto_loop_thread = None

def _auto_loop():
    global _neural_processor
    while True:
        time.sleep(60)  # проверяем раз в минуту
        if not _neural_processor or not _neural_processor.active:
            continue

        thumbs_dir = _neural_processor.watched_folder or "thumbnails"
        targets = []

        for root, _, files in os.walk(thumbs_dir):
            for file in files:
                if file.endswith(".webp") and file.startswith("preview_"):
                    full = os.path.join(root, file)
                    base = os.path.splitext(full)[0]
                    json_path = base + "_pixtral.json"
                    if not os.path.exists(json_path):
                        targets.append(full)

        if targets:
            print(f"[AUTO] Найдено {len(targets)} кадров для дообработки")
            for path in targets:
                if _neural_processor.needs_processing(path):
                    threading.Thread(
                        target=_neural_processor.process_image,
                        args=(path,)
                    ).start()

def start_enhanced_neural_auto_loop():
    global _auto_loop_thread
    if not _auto_loop_thread or not _auto_loop_thread.is_alive():
        _auto_loop_thread = threading.Thread(target=_auto_loop, daemon=True)
        _auto_loop_thread.start()
