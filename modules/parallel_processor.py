"""
Модуль для параллельной обработки API запросов с учетом ограничений на количество запросов
"""

import time
import queue
import threading
from modules.settings_manager import load_settings

class ParallelProcessor:
    """
    Класс для параллельной обработки API запросов с учетом rate-лимитов.
    Поддерживает работу с несколькими API ключами и обеспечивает справедливое 
    распределение запросов между ними.
    """
    def __init__(self):
        """
        Инициализирует процессор с параметрами по умолчанию.
        """
        # Флаг активности процессора
        self.active = False
        
        # Очередь задач для Pixtral
        self.task_queue = queue.Queue()
        
        # Информация о последних вызовах API для каждого ключа
        self.api_usage = {}
        
        # Время между вызовами API (1 сек по умолчанию)
        self.request_interval = 1.0
        
        # Потоки обработчиков
        self.worker_threads = []
        
        # Загружаем настройки
        settings = load_settings()
        self.api_keys = settings.get("api_keys", [])
        
        # Мьютекс для обеспечения безопасности работы с ключами
        self.api_lock = threading.Lock()
        
    def start(self, num_workers=None):
        """
        Запускает процессор с указанным количеством рабочих потоков.
        
        Args:
            num_workers (int): Количество рабочих потоков. По умолчанию равно количеству ключей.
        """
        if self.active:
            print("Процессор уже запущен")
            return
            
        # Если количество потоков не указано, используем по одному на каждый ключ
        if num_workers is None:
            num_workers = max(1, len(self.api_keys))
            
        self.active = True
        
        # Создаем и запускаем рабочие потоки
        for i in range(num_workers):
            t = threading.Thread(target=self._worker, args=(i,))
            t.daemon = True
            t.start()
            self.worker_threads.append(t)
            
        print(f"Процессор запущен с {num_workers} рабочими потоками")
        
    def stop(self):
        """
        Останавливает процессор и все рабочие потоки.
        """
        if not self.active:
            return
            
        self.active = False
        
        # Добавляем специальные задачи для завершения потоков
        for _ in range(len(self.worker_threads)):
            self.task_queue.put(None)
            
        # Ожидаем завершения всех потоков
        for t in self.worker_threads:
            t.join(0.5)  # Таймаут на всякий случай
            
        self.worker_threads = []
        print("Процессор остановлен")
        
    def add_task(self, api_type, task_func, *args, **kwargs):
        """
        Добавляет задачу в очередь.
        
        Args:
            api_type (str): Тип API (pixtral)
            task_func (callable): Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            threading.Event: Событие, которое сработает при завершении задачи
            queue.Queue: Очередь, в которую будет помещен результат
        """
        result_queue = queue.Queue(1)
        done_event = threading.Event()
        
        task = {
            "api_type": api_type,
            "func": task_func,
            "args": args,
            "kwargs": kwargs,
            "result_queue": result_queue,
            "done_event": done_event
        }
        
        self.task_queue.put(task)
        return done_event, result_queue
        
    def _worker(self, worker_id):
        """
        Функция рабочего потока. Берет задачи из очереди и выполняет их.
        
        Args:
            worker_id (int): Идентификатор рабочего потока
        """
        print(f"Рабочий поток {worker_id} запущен")
        
        while self.active:
            try:
                # Получаем задачу из очереди
                task = self.task_queue.get(timeout=1.0)
                
                # Проверяем сигнал завершения
                if task is None:
                    print(f"Рабочий поток {worker_id} получил сигнал завершения")
                    self.task_queue.task_done()
                    break
                    
                # Получаем параметры задачи
                api_type = task["api_type"]
                func = task["func"]
                args = task["args"]
                kwargs = task["kwargs"]
                result_queue = task["result_queue"]
                done_event = task["done_event"]
                
                # Определяем, какой ключ использовать и сколько ждать до следующего запроса
                wait_time = self._get_wait_time(api_type)
                
                # Ждем необходимое время
                if wait_time > 0:
                    time.sleep(wait_time)
                    
                # Выполняем задачу
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    print(f"Ошибка при выполнении задачи: {e}")
                    result_queue.put(None)
                    
                # Обновляем информацию об использовании API
                self._update_api_usage(api_type)
                
                # Сигнализируем о завершении задачи
                done_event.set()
                
                # Отмечаем задачу как выполненную
                self.task_queue.task_done()
                
            except queue.Empty:
                # Очередь пуста, просто продолжаем
                continue
            except Exception as e:
                print(f"Неожиданная ошибка в рабочем потоке {worker_id}: {e}")
                
        print(f"Рабочий поток {worker_id} завершен")
        
    def _get_wait_time(self, api_type):
        """
        Определяет, сколько нужно ждать до следующего запроса для заданного API ключа.
        
        Args:
            api_type (str): Тип API (pixtral)
            
        Returns:
            float: Время ожидания в секундах
        """
        with self.api_lock:
            # Проверяем, есть ли доступные ключи
            if not self.api_keys:
                print("Нет доступных API ключей")
                return 10.0  # Долгое ожидание, если нет ключей
                
            # Находим ключ с самым давним использованием
            now = time.time()
            best_key = None
            min_wait = float('inf')
            
            for key in self.api_keys:
                key_id = key[:8]  # Используем часть ключа как идентификатор
                
                # Если ключ еще не использовался, выбираем его
                if key_id not in self.api_usage:
                    self.api_usage[key_id] = {
                        "pixtral": 0,
                        "total": 0
                    }
                    best_key = key
                    min_wait = 0
                    break
                    
                # Проверяем время последнего использования
                last_use = self.api_usage[key_id].get("last_use", 0)
                wait = max(0, last_use + self.request_interval - now)
                
                # Если этот ключ доступен раньше других, выбираем его
                if wait < min_wait:
                    min_wait = wait
                    best_key = key
            
            # Запоминаем выбранный ключ и возвращаем время ожидания
            self.current_key = best_key
            return min_wait
                
    def _update_api_usage(self, api_type):
        """
        Обновляет информацию об использовании API ключа.
        
        Args:
            api_type (str): Тип API (pixtral)
        """
        with self.api_lock:
            # Проверяем, установлен ли текущий ключ
            if not hasattr(self, 'current_key') or self.current_key is None:
                print("Невозможно обновить использование API: ключ не установлен")
                return
                
            try:
                # Берем первые 8 символов ключа как идентификатор
                key_id = self.current_key[:8] if len(self.current_key) >= 8 else self.current_key
                now = time.time()
                
                # Если этот ключ впервые используется, инициализируем счетчики
                if key_id not in self.api_usage:
                    self.api_usage[key_id] = {
                        "pixtral": 0,
                        "total": 0,
                        "last_use": now
                    }
                    
                # Увеличиваем счетчики использования
                self.api_usage[key_id][api_type] = self.api_usage[key_id].get(api_type, 0) + 1
                self.api_usage[key_id]["total"] = self.api_usage[key_id].get("total", 0) + 1
                self.api_usage[key_id]["last_use"] = now
            except Exception as e:
                print(f"Ошибка при обновлении использования API: {e}")
                
    def update_api_keys(self):
        """
        Обновляет список API ключей из настроек.
        """
        settings = load_settings()
        
        with self.api_lock:
            self.api_keys = settings.get("api_keys", [])
            
            try:
                # Если список ключей изменился, нужно обновить информацию об их использовании
                current_keys = {}
                for key in self.api_keys:
                    if key and len(key) >= 8:
                        current_keys[key[:8]] = key
                    elif key:
                        current_keys[key] = key
                
                # Удаляем информацию о ключах, которых больше нет
                for key_id in list(self.api_usage.keys()):
                    if key_id not in current_keys:
                        del self.api_usage[key_id]
            except Exception as e:
                print(f"Ошибка при обновлении API ключей: {e}")
                    
        print(f"Список API ключей обновлен, доступно {len(self.api_keys)} ключей")
        
    def get_status(self):
        """
        Возвращает информацию о текущем состоянии процессора.
        
        Returns:
            dict: Информация о состоянии процессора
        """
        with self.api_lock:
            return {
                "active": self.active,
                "workers": len(self.worker_threads),
                "queue_size": self.task_queue.qsize(),
                "api_keys": len(self.api_keys),
                "api_usage": self.api_usage
            }
