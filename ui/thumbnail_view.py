import os
import time
import threading
import logging
import flet as ft
from ui.image_view import create_image_view

# Настраиваем логгер
logger = logging.getLogger(__name__)

# Глобальный кэш изображений для экономии памяти
_image_cache = {}
_image_cache_lock = threading.Lock()
_CACHE_MAX_SIZE = 200  # Максимальный размер кэша

def create_thumbnails_view(page):
    """
    Создает интерфейс для отображения миниатюр и просмотра изображений.
    
    Args:
        page (ft.Page): Страница Flet для размещения интерфейса
        
    Returns:
        tuple: Кортеж из (thumbnails_grid, image_view_container, pagination)
    """
    # Сетка для отображения миниатюр
    thumbnails_grid = ft.GridView(
        expand=True,
        runs_count=4,
        max_extent=200,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
        padding=20,
    )
    
    # Контейнер для просмотра изображения, по умолчанию скрыт
    image_view_container = ft.Container(expand=True, visible=False)
    
    # Панель пагинации
    prev_button = ft.IconButton(
        icon=ft.icons.ARROW_BACK,
        tooltip="Предыдущая страница",
        disabled=True,
    )
    
    next_button = ft.IconButton(
        icon=ft.icons.ARROW_FORWARD,
        tooltip="Следующая страница",
        disabled=True,
    )
    
    page_text = ft.Text("Страница 1", size=14)
    
    pagination = ft.Row(
        controls=[prev_button, page_text, next_button],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    
    return thumbnails_grid, image_view_container, pagination

def get_cached_image(path):
    """
    Получает изображение из кэша или создает новый объект изображения.
    
    Args:
        path (str): Путь к изображению
        
    Returns:
        ft.Image: Объект изображения
    """
    with _image_cache_lock:
        if path in _image_cache:
            # Если изображение в кэше, возвращаем его
            return _image_cache[path]
        
        # Если кэш переполнен, удаляем старые записи
        if len(_image_cache) >= _CACHE_MAX_SIZE:
            # Удаляем 20% самых старых записей
            remove_count = _CACHE_MAX_SIZE // 5
            keys_to_remove = list(_image_cache.keys())[:remove_count]
            for key in keys_to_remove:
                del _image_cache[key]
        
        # Создаем новое изображение и добавляем в кэш
        image = ft.Image(
            src=path,
            width=150,
            height=150,
            fit=ft.ImageFit.COVER,
            border_radius=ft.border_radius.all(10)
        )
        _image_cache[path] = image
        return image

def load_thumbnails_from_results(page, thumbnails_grid, image_view_container, filtered_results, current_page=0):
    """
    Загружает и отображает миниатюры из результатов поиска с оптимизацией для большого количества данных.
    
    Args:
        page (ft.Page): Страница Flet
        thumbnails_grid (ft.GridView): Сетка для отображения миниатюр
        image_view_container (ft.Container): Контейнер для просмотра изображения
        filtered_results (list): Список путей к отфильтрованным миниатюрам
        current_page (int): Текущая страница для отображения
    """
    start_time = time.time()
    logger.info(f"Загрузка миниатюр: страница {current_page+1}, всего {len(filtered_results)} результатов")
    
    # Увеличиваем количество элементов на странице для больших объемов данных
    items_per_page = 30 if len(filtered_results) < 5000 else 50
    
    total_thumbnails = len(filtered_results)
    total_pages = max(1, (total_thumbnails + items_per_page - 1) // items_per_page)
    
    # Ограничиваем номер страницы допустимыми пределами
    if current_page >= total_pages and total_pages > 0:
        current_page = total_pages - 1
    elif current_page < 0:
        current_page = 0
    
    # Находим элементы пагинации в родительских элементах
    pagination_row = None
    for parent in thumbnails_grid.parent.controls:
        if isinstance(parent, ft.Row) and len(parent.controls) == 3 and isinstance(parent.controls[1], ft.Text):
            pagination_row = parent
            break
    
    if pagination_row:
        prev_button = pagination_row.controls[0]
        page_text = pagination_row.controls[1]
        next_button = pagination_row.controls[2]
        
        # Обновляем состояние элементов пагинации
        prev_button.disabled = current_page <= 0
        next_button.disabled = (current_page >= total_pages - 1 or total_pages <= 1)
        
        # Обновляем номер страницы
        page_info = f"Страница {current_page + 1} из {total_pages}"
        if total_thumbnails > 1000:
            page_info += f" (всего {total_thumbnails:,} изображений)".replace(",", " ")
        page_text.value = page_info
        
        # Добавляем обработчики событий для кнопок пагинации
        prev_button.on_click = lambda e, p=current_page: load_thumbnails_from_results_page(page, thumbnails_grid, image_view_container, filtered_results, p - 1)
        next_button.on_click = lambda e, p=current_page: load_thumbnails_from_results_page(page, thumbnails_grid, image_view_container, filtered_results, p + 1)
    
    # Вычисляем диапазон элементов для текущей страницы
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, total_thumbnails)
    page_thumbnails = filtered_results[start_idx:end_idx]
    
    # Очищаем сетку
    thumbnails_grid.controls.clear()
    
    # Обрабатываем случай отсутствия миниатюр

    if not hasattr(thumbnails_grid, 'controls') or thumbnails_grid.controls is None:
        thumbnails_grid.controls = []    
    # Добавляем заглушки для миниатюр
    for _ in page_thumbnails:
        thumbnails_grid.controls.append(
            ft.Container(
                width=150,
                height=150,
                bgcolor=ft.colors.with_opacity(0.04, ft.colors.ON_BACKGROUND),
                border_radius=ft.border_radius.all(10)
            )
        )
    
    # Обновляем страницу с заглушками
    page.update()
    
    # Функция для загрузки изображений в фоновом режиме
    def update_images():
        # Загружаем изображения партиями для уменьшения задержек обновления
        batch_size = 10
        
        for batch_start in range(0, len(page_thumbnails), batch_size):
            batch_end = min(batch_start + batch_size, len(page_thumbnails))
            batch = page_thumbnails[batch_start:batch_end]
            
            for i, path in enumerate(batch):
                try:
                    idx = batch_start + i
                    full_path = os.path.join("thumbnails", path)
                    
                    # Используем кэширование изображений
                    image = get_cached_image(full_path)
                    
                    # Создаем контейнер с изображением
                    container = ft.Container(
                        content=image,
                        width=150,
                        height=150,
                        border_radius=ft.border_radius.all(10),
                        ink=True,
                        on_click=lambda e, p=path, img_list=page_thumbnails: on_image_click(
                            page,
                            os.path.join("thumbnails", p),
                            [os.path.join("thumbnails", img) for img in img_list],
                            image_view_container,
                            thumbnails_grid
                        ),
                    )
                    
                    # Обновляем элемент в сетке если индекс валиден
                    if idx < len(thumbnails_grid.controls):
                        thumbnails_grid.controls[idx] = container
                except Exception as e:
                    logger.error(f"Ошибка при загрузке миниатюры {path}: {e}")
            
            # Обновляем интерфейс после каждой партии
            page.update()
            
            # Небольшая пауза между обновлениями для отзывчивости интерфейса
            time.sleep(0.05)
        
        # Логируем время загрузки
        load_time = time.time() - start_time
        logger.info(f"Загрузка миниатюр завершена за {load_time:.2f} сек.")
    
    # Запускаем загрузку изображений в отдельном потоке
    threading.Thread(target=update_images, daemon=True).start()
    
    return current_page

def load_thumbnails_from_results_page(page, thumbnails_grid, image_view_container, filtered_results, new_page):
    """
    Загружает и отображает миниатюры с указанной страницы.
    
    Args:
        page (ft.Page): Страница Flet
        thumbnails_grid (ft.GridView): Сетка для отображения миниатюр
        image_view_container (ft.Container): Контейнер для просмотра изображения
        filtered_results (list): Список путей к отфильтрованным миниатюрам
        new_page (int): Номер страницы для загрузки
    """
    logger.info(f"Запрошена страница: {new_page + 1}")
    load_thumbnails_from_results(page, thumbnails_grid, image_view_container, filtered_results, new_page)

def on_image_click(page, image_path, image_list, image_view_container, thumbnails_grid):
    """
    Обработчик клика по миниатюре.
    
    Args:
        page (ft.Page): Страница Flet
        image_path (str): Путь к выбранному изображению
        image_list (list): Список путей к изображениям на текущей странице
        image_view_container (ft.Container): Контейнер для просмотра изображения
        thumbnails_grid (ft.GridView): Сетка для отображения миниатюр
    """
    def on_back():
        show_thumbnails(page, thumbnails_grid, image_view_container)
    
    image_view = create_image_view(
        page,
        current_file=image_path,
        all_files=image_list,
        on_back=on_back
    )
    thumbnails_grid.visible = False
    image_view_container.visible = True
    image_view_container.content = image_view
    page.update()

def show_thumbnails(page, thumbnails_grid, image_view_container):
    """
    Возвращает представление к режиму миниатюр.
    
    Args:
        page (ft.Page): Страница Flet
        thumbnails_grid (ft.GridView): Сетка для отображения миниатюр
        image_view_container (ft.Container): Контейнер для просмотра изображения
    """
    image_view_container.visible = False
    thumbnails_grid.visible = True
    page.update()

def clear_image_cache():
    """
    Очищает кэш изображений для экономии памяти.
    """
    with _image_cache_lock:
        _image_cache.clear()
    logger.info("Кэш изображений очищен")