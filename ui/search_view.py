import time
import threading
import logging
from modules.settings_manager import load_settings
from modules.search_manager import (
    search_in_index,
    smart_search,
    very_smart_filter,
    get_current_index
)
from ui.thumbnail_view import load_thumbnails_from_results

# Настраиваем логгер
logger = logging.getLogger(__name__)

# Кэш для хранения результатов поиска
_search_cache = {}
_search_cache_lock = threading.Lock()
_last_index_count = 0

def perform_search(query):
    """
    Выполняет поиск в индексе на основе запроса с кэшированием результатов.
    
    Args:
        query (str): Поисковый запрос
        
    Returns:
        list: Список путей к найденным миниатюрам
    """
    global _search_cache, _last_index_count
    
    # Нормализуем запрос для кэширования
    query = query.strip().lower()
    
    # Проверяем, изменился ли индекс
    current_index = get_current_index()
    current_index_count = len(current_index)
    index_changed = current_index_count != _last_index_count
    _last_index_count = current_index_count
    
    # Проверяем кэш при неизменном индексе и существующем запросе
    if not index_changed and query in _search_cache:
        logger.info(f"Используем кэшированный результат для запроса: '{query}'")
        return _search_cache[query]
    
    # Выполняем запрос в зависимости от настроек
    if not query:
        result = list(current_index.keys())
    else:
        settings = load_settings()
        use_smart = settings.get("smart_search_enabled", False)
        use_very = settings.get("very_smart_enabled", False)
        
        # Выбираем стратегию поиска
        if use_very:
            logger.info(f"Выполняем супер-умный поиск: '{query}'")
            candidates = smart_search(query, force=True)
            logger.info(f"Кандидатов от smart_search: {len(candidates)}")
            result = very_smart_filter(candidates, query)
        elif use_smart:
            logger.info(f"Выполняем умный поиск: '{query}'")
            result = smart_search(query, force=True)
        else:
            logger.info(f"Выполняем стандартный поиск: '{query}'")
            result = search_in_index(query)
    
    # Кэшируем результат
    with _search_cache_lock:
        # Ограничиваем размер кэша
        if len(_search_cache) > 50:  # Храним не более 50 запросов
            oldest_query = next(iter(_search_cache))
            del _search_cache[oldest_query]
        
        _search_cache[query] = result
    
    return result

def update_search_results(page, results, filtered_results, current_page, current_query):
    """
    Обновляет результаты поиска и отображает их.
    
    Args:
        page (ft.Page): Страница Flet
        results (list): Результаты поиска
        filtered_results (list): Список для хранения отфильтрованных результатов
        current_page (int): Текущая страница
        current_query (str): Текущий поисковый запрос
    """
    # Обновляем результаты
    filtered_results.clear()
    filtered_results.extend(results)
    
    # Находим элементы интерфейса на странице
    thumbnails_grid = None
    image_view_container = None
    
    # Ищем в контейнерах на странице
    for container in page.controls:
        if hasattr(container, 'content') and container.content:
            for control in container.content.controls:
                if hasattr(control, 'controls'):
                    for nested_control in control.controls:
                        if hasattr(nested_control, 'controls') and len(nested_control.controls) == 2:
                            if hasattr(nested_control.controls[0], 'runs_count'):
                                thumbnails_grid = nested_control.controls[0]
                                image_view_container = nested_control.controls[1]
                                break
                if thumbnails_grid and image_view_container:
                    break
            if thumbnails_grid and image_view_container:
                break
    
    if thumbnails_grid and image_view_container:
        # Загружаем миниатюры
        load_thumbnails_from_results(
            page,
            thumbnails_grid,
            image_view_container,
            filtered_results,
            current_page
        )

def start_thumbnail_auto_refresh(page, image_view_container, current_query):
    """
    Запускает автоматическое обновление миниатюр с оптимизацией для большого количества данных.
    
    Args:
        page (ft.Page): Страница Flet
        image_view_container (ft.Container): Контейнер для просмотра изображения
        current_query (str): Текущий поисковый запрос
    """
    last_loaded_count = -1
    update_in_progress = False
    
    def refresh_loop():
        nonlocal last_loaded_count, update_in_progress
        while True:
            try:
                # Проверяем обновление только если предыдущее завершено
                if not update_in_progress:
                    current_index = get_current_index()
                    count = len(current_index)
                    
                    if count != last_loaded_count:
                        # Уменьшаем частоту обновлений для больших индексов
                        if count > 5000:
                            logger.info(f"Обнаружен большой индекс ({count} элементов), оптимизируем обновление")
                            
                            # Если индекс очень большой, обновляем только если добавлено много новых
                            if last_loaded_count > 0 and (count - last_loaded_count) < 10:
                                logger.info(f"Пропускаем обновление, добавлено только {count - last_loaded_count} элементов")
                                last_loaded_count = count
                                time.sleep(10)  # Увеличиваем интервал для больших индексов
                                continue
                        
                        last_loaded_count = count
                        
                        # Обновляем только если мы в главном окне и НЕ в предпросмотре
                        if not image_view_container.visible:
                            logger.info("🔁 Обнаружены новые стопкадры — обновляем интерфейс")
                            
                            # Отмечаем, что обновление в процессе
                            update_in_progress = True
                            
                            # Запускаем обновление в отдельном потоке
                            def perform_update():
                                nonlocal update_in_progress
                                try:
                                    filtered_results = perform_search(current_query)
                                    update_search_results(page, filtered_results, [], 0, current_query)
                                finally:
                                    update_in_progress = False
                            
                            threading.Thread(target=perform_update, daemon=True).start()
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления миниатюр: {e}")
            
            # Интервал обновления зависит от размера индекса
            sleep_time = 5 if last_loaded_count < 5000 else 10
            time.sleep(sleep_time)
    
    threading.Thread(target=refresh_loop, daemon=True).start()