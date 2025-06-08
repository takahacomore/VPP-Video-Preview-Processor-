"""
Модуль для автоматической обработки изображений с помощью нейросетей
"""

import os
import json
import time
import threading
import requests
import base64
from pathlib import Path
from modules.settings_manager import load_settings

class MistralAPI:
    """
    Класс для взаимодействия с Mistral API
    """
    def __init__(self, api_keys):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.key_index = 0
        self.model = "mistral-large-latest"  # можно настроить в будущем

    def _get_next_key(self):
        key = self.api_keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return key

    def process_text(self, text, language="ru"):
        """
        Обрабатывает текст с помощью Mistral API
        """
        headers = {
            "Authorization": f"Bearer {self._get_next_key()}",
            "Content-Type": "application/json"
        }
        
        # Составляем промпт в зависимости от языка
        prompt = (
            "Отредактируй следующий текст описания изображения: убери лишние вводные фразы, очисти форматирование, "
            "убери \\n и **, сделай его кратким, пригодным для поиска. "
            "В конце добавь теги по содержанию. Ответ должен быть на русском."
            if language == "ru" else
            "Edit the following image description: remove unnecessary introductory phrases, clean up formatting, "
            "remove \\n and **, make it concise and searchable. Add tags based on content at the end. Respond in English."
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"Ошибка API Mistral: {response.status_code} {response.text}")
                return None
        except Exception as e:
            print(f"Ошибка при обращении к Mistral API: {e}")
            return None


class PixtralAPI:
    """
    Класс для взаимодействия с Pixtral API
    """
    def __init__(self, api_keys):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.key_index = 0
        self.model = "pixtral-v1"  # актуальная модель

    def _get_next_key(self):
        key = self.api_keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return key

    def process_image(self, image_path, language="ru"):
        """
        Обрабатывает изображение с помощью Pixtral API
        """
        headers = {
            "Authorization": f"Bearer {self._get_next_key()}",
            "Content-Type": "application/json"
        }
        
        # Загружаем и кодируем изображение
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Ошибка при чтении файла {image_path}: {e}")
            return None
            
        # Составляем промпт в зависимости от языка
        prompt = (
            "Опиши детально что изображено на этом изображении. Не используй лишние вводные фразы. Не используй \\n и **."
            "В конце добавь теги по содержанию. Ответ должен быть на русском."
            if language == "ru" else
            "Describe in detail what is shown in this image. Respond in English."
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ],
            "temperature": 0.5,
            "top_p": 0.9,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"Ошибка API Pixtral: {response.status_code} {response.text}")
                return None
        except Exception as e:
            print(f"Ошибка при обращении к Pixtral API: {e}")
            return None


class NeuralProcessor:
    """
    Класс для автоматической обработки изображений с помощью нейросетей
    """
    def __init__(self):
        self.running = False
        self.processing_thread = None
        self.settings = load_settings()
        
        # Загружаем API ключи из настроек
        self.mistral_api_keys = self.settings.get("mistral_api_keys", [])
        self.pixtral_api_keys = self.settings.get("pixtral_api_keys", [])
        
        # Создаем API клиенты
        self.mistral_api = MistralAPI(self.mistral_api_keys) if self.mistral_api_keys else None
        self.pixtral_api = PixtralAPI(self.pixtral_api_keys) if self.pixtral_api_keys else None

    def check_ready(self):
        """
        Проверяет готовность процессора к работе
        
        Returns:
            bool: True, если готов, иначе False
        """
        return (
            self.mistral_api is not None and len(self.mistral_api_keys) > 0 and
            self.pixtral_api is not None and len(self.pixtral_api_keys) > 0
        )

    def watch_thumbnails(self):
        """
        Отслеживает новые файлы в директории thumbnails для обработки
        """
        thumbnails_dir = Path("thumbnails")
        processed_files = set()
        
        print("🔍 Запущено отслеживание новых изображений...")
        
        while self.running:
            try:
                # Перебираем все директории внутри thumbnails
                for subdir in thumbnails_dir.glob("*"):
                    if not subdir.is_dir() or not self.running:
                        continue
                    
                    # Ищем все файлы .webp
                    for image_file in subdir.glob("*.webp"):
                        # Проверяем, не обрабатывали ли мы уже этот файл
                        if image_file in processed_files:
                            continue
                        
                        # Проверяем, нужна ли обработка
                        if self.needs_processing(image_file):
                            print(f"🧠 Обработка {image_file}...")
                            self.process_image(image_file)
                            processed_files.add(image_file)
                        else:
                            # Добавляем в список обработанных, даже если обработка не требуется
                            processed_files.add(image_file)
                            
                # Чтобы не нагружать CPU, делаем паузу
                time.sleep(5)
            except Exception as e:
                print(f"❌ Ошибка при отслеживании файлов: {e}")
                time.sleep(10)  # Делаем паузу перед следующей попыткой

    def needs_processing(self, image_path):
        """
        Проверяет, требует ли файл обработки нейросетями
        
        Args:
            image_path (Path): Путь к изображению
            
        Returns:
            bool: True, если требуется обработка, иначе False
        """
        # Проверяем наличие файлов с описаниями
        stem = image_path.stem
        pixtral_json = image_path.parent / f"{stem}_pixtral.json"
        mistral_json = image_path.parent / f"{stem}_mistral.json"
        
        # Если оба файла существуют, обработка не требуется
        return not (pixtral_json.exists() and mistral_json.exists())

    def process_image(self, image_path):
        """
        Обрабатывает изображение с помощью нейросетей
        
        Args:
            image_path (Path): Путь к изображению
            
        Returns:
            bool: True, если обработка успешна, иначе False
        """
        if not self.check_ready():
            print("⚠️ API клиенты не готовы")
            return False
            
        # Определяем язык обработки
        language = self.settings.get("language", "ru")
            
        # Проверяем наличие файлов описаний
        stem = image_path.stem
        pixtral_json = image_path.parent / f"{stem}_pixtral.json"
        mistral_json = image_path.parent / f"{stem}_mistral.json"
        
        # Обрабатываем через Pixtral, если нет описания
        pixtral_text = None
        if not pixtral_json.exists():
            try:
                pixtral_text = self.pixtral_api.process_image(str(image_path), language)
                if pixtral_text:
                    # Сохраняем результат
                    self.save_pixtral_result(image_path, pixtral_text)
            except Exception as e:
                print(f"❌ Ошибка при обработке через Pixtral: {e}")
        
        # Обрабатываем через Mistral, если нет результата или есть Pixtral-описание
        if not mistral_json.exists() and pixtral_text:
            try:
                self.process_with_mistral(image_path, pixtral_text)
            except Exception as e:
                print(f"❌ Ошибка при обработке через Mistral: {e}")
                
        return pixtral_json.exists() and mistral_json.exists()

    def save_pixtral_result(self, image_path, text):
        """
        Сохраняет результат обработки Pixtral в файл
        
        Args:
            image_path (Path): Путь к изображению
            text (str): Текст описания
        """
        stem = image_path.stem
        output_file = image_path.parent / f"{stem}_pixtral.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"text": text}, f, ensure_ascii=False, indent=4)
            print(f"✅ Сохранен результат Pixtral: {output_file}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении результата Pixtral: {e}")

    def save_mistral_result(self, image_path, text):
        """
        Сохраняет результат обработки Mistral в файл
        
        Args:
            image_path (Path): Путь к изображению
            text (str): Текст описания
        """
        stem = image_path.stem
        output_file = image_path.parent / f"{stem}_mistral.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"text": text}, f, ensure_ascii=False, indent=4)
            print(f"✅ Сохранен результат Mistral: {output_file}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении результата Mistral: {e}")

    def process_with_mistral(self, image_path, pixtral_text):
        """
        Обрабатывает текст описания с помощью Mistral
        
        Args:
            image_path (Path): Путь к изображению
            pixtral_text (str): Текст описания от Pixtral
            
        Returns:
            str: Обработанный текст или None в случае ошибки
        """
        language = self.settings.get("language", "ru")
        
        mistral_text = self.mistral_api.process_text(pixtral_text, language)
        if mistral_text:
            self.save_mistral_result(image_path, mistral_text)
            return mistral_text
            
        return None

    def start(self):
        """
        Запускает процесс автоматической обработки изображений
        """
        if self.running:
            return
            
        if not self.check_ready():
            print("⚠️ API клиенты не готовы, проверьте настройки API ключей")
            return
            
        self.running = True
        self.processing_thread = threading.Thread(target=self.watch_thumbnails)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        print("✅ Запущена автоматическая обработка изображений")

    def stop(self):
        """
        Останавливает процесс автоматической обработки изображений
        """
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(1.0)  # Ждем не более 1 секунды
            self.processing_thread = None
            
        print("⏹ Остановлена автоматическая обработка изображений")
