# Новый модуль: modules/progress_tracker.py
import time
import threading
from dataclasses import dataclass

@dataclass
class ProgressInfo:
    """Информация о прогрессе операции"""
    operation_name: str  # Название операции
    current: int  # Текущий прогресс
    total: int  # Общее количество
    start_time: float  # Время начала операции
    status: str = "active"  # Status: active, paused, complete, error
    message: str = ""  # Дополнительная информация
    
    @property
    def percentage(self):
        """Возвращает процент завершения"""
        if self.total <= 0:
            return 0
        return min(100, int(self.current / self.total * 100))
    
    @property
    def elapsed_time(self):
        """Возвращает прошедшее время в секундах"""
        return time.time() - self.start_time
    
    @property
    def estimated_time_remaining(self):
        """Оценивает оставшееся время в секундах"""
        if self.current <= 0 or self.percentage >= 100:
            return 0
        
        elapsed = self.elapsed_time
        rate = self.current / elapsed  # items per second
        remaining_items = self.total - self.current
        
        if rate > 0:
            return remaining_items / rate
        return 0
    
    def format_time(self, seconds):
        """Форматирует время для отображения"""
        if seconds < 60:
            return f"{int(seconds)} сек"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)
            return f"{minutes} мин {seconds} сек"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} ч {minutes} мин"
    
    def get_info_text(self):
        """Возвращает информативный текст о прогрессе"""
        if self.status == "complete":
            return f"{self.operation_name}: Завершено за {self.format_time(self.elapsed_time)}"
        elif self.status == "error":
            return f"{self.operation_name}: Ошибка - {self.message}"
        elif self.status == "paused":
            return f"{self.operation_name}: Приостановлено - {self.current}/{self.total}"
        else:
            est = self.format_time(self.estimated_time_remaining)
            return f"{self.operation_name}: {self.current}/{self.total} ({self.percentage}%) - Осталось: {est}"


class ProgressTracker:
    """Класс для отслеживания прогресса операций"""
    
    def __init__(self):
        self.operations = {}
        self.callbacks = []
        self.lock = threading.Lock()
    
    def start_operation(self, operation_id, name, total):
        """Начинает отслеживание новой операции"""
        with self.lock:
            self.operations[operation_id] = ProgressInfo(
                operation_name=name,
                current=0,
                total=total,
                start_time=time.time()
            )
            self._notify_update(operation_id)
        return operation_id
    
    def update_progress(self, operation_id, current, message=""):
        """Обновляет прогресс операции"""
        if operation_id not in self.operations:
            return False
            
        with self.lock:
            op = self.operations[operation_id]
            op.current = current
            if message:
                op.message = message
            
            if current >= op.total:
                op.status = "complete"
            
            self._notify_update(operation_id)
        return True
    
    def complete_operation(self, operation_id, message=""):
        """Отмечает операцию как завершенную"""
        if operation_id not in self.operations:
            return False
            
        with self.lock:
            op = self.operations[operation_id]
            op.current = op.total
            op.status = "complete"
            if message:
                op.message = message
            
            self._notify_update(operation_id)
        return True
    
    def error_operation(self, operation_id, message):
        """Отмечает операцию как завершенную с ошибкой"""
        if operation_id not in self.operations:
            return False
            
        with self.lock:
            op = self.operations[operation_id]
            op.status = "error"
            op.message = message
            
            self._notify_update(operation_id)
        return True
    
    def pause_operation(self, operation_id):
        """Приостанавливает операцию"""
        if operation_id not in self.operations:
            return False
            
        with self.lock:
            op = self.operations[operation_id]
            op.status = "paused"
            
            self._notify_update(operation_id)
        return True
    
    def resume_operation(self, operation_id):
        """Возобновляет приостановленную операцию"""
        if operation_id not in self.operations:
            return False
            
        with self.lock:
            op = self.operations[operation_id]
            if op.status == "paused":
                op.status = "active"
                
                self._notify_update(operation_id)
        return True
    
    def get_operation(self, operation_id):
        """Возвращает информацию об операции"""
        with self.lock:
            return self.operations.get(operation_id)
    
    def get_all_operations(self):
        """Возвращает информацию обо всех операциях"""
        with self.lock:
            return dict(self.operations)
    
    def register_callback(self, callback):
        """Регистрирует функцию обратного вызова для обновлений прогресса"""
        with self.lock:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Удаляет функцию обратного вызова"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def _notify_update(self, operation_id):
        """Оповещает обо всех обновлениях прогресса"""
        op = self.operations[operation_id]
        for callback in self.callbacks:
            try:
                callback(operation_id, op)
            except Exception as e:
                print(f"Ошибка при вызове callback: {e}")


# Создаем глобальный экземпляр трекера прогресса
_progress_tracker = None

def get_progress_tracker():
    """Возвращает глобальный экземпляр ProgressTracker"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker