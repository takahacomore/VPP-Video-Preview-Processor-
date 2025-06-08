import os
import flet as ft
from functools import partial
from pathlib import Path
from modules.favorites_manager import FavoritesManager
from ui.favorites_image_view import create_favorites_image_view  # Отдельный файл для предпросмотра

def create_favorites_view(page, on_back=None):
    """
    Возвращает контейнер с интерфейсом избранного (панель категорий, кнопка "+", список миниатюр).
    При клике по миниатюре открывается режим предпросмотра, а кнопка "Назад" в предпросмотре возвращает к
    списку избранного, а не на главный экран.
    """
    favorites_manager = FavoritesManager()
    current_category = [None]  # Если None – показываются все изображения

    # Панель категорий (слева)
    categories_view = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=10,
        expand=True,
    )
    new_category_field = ft.TextField(
        hint_text="Новая категория",
        expand=True,
    )

    # Сетка миниатюр (справа) – переименовываем favorites_grid в screenshots_grid
    screenshots_grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=150,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
        padding=20,
    )

    # *****************************
    # Режимы отображения: список и предпросмотр
    # *****************************
    # Интерфейс списка избранного (с категориями и миниатюрами)
    title_bar = ft.Row([
        ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Назад", on_click=lambda e: on_back() if on_back else None),
        ft.Text("Избранное", size=24, weight=ft.FontWeight.BOLD),
    ])
    list_view = ft.Container(
        content=ft.Column([
            title_bar,
            ft.Divider(height=1),
            ft.Row(
                controls=[
                    ft.Container(
                        content=categories_view,
                        width=200,
                        border=ft.border.only(right=ft.border.BorderSide(1, ft.colors.OUTLINE)),
                    ),
                    ft.Container(content=screenshots_grid, expand=True),
                ],
                expand=True,
            ),
        ], spacing=10, expand=True),
        padding=10,
        expand=True,
    )
    
    # Интерфейс предпросмотра – будет создаваться динамически через create_favorites_image_view
    preview_view = ft.Container()  # placeholder

    # Контейнер, который будет менять своё содержимое между режимами
    main_container = ft.Container(content=list_view, expand=True)

    # Функции переключения между режимами
    def show_preview(screenshot_path, category_files):
        nonlocal preview_view
        preview_view = create_favorites_image_view(
            page,
            screenshot_path,
            on_back=lambda e: switch_to_list(),
            category_files=category_files
        )
        main_container.content = preview_view
        page.update()

    def switch_to_list():
        main_container.content = list_view
        page.update()

    # *****************************
    # Функции работы с избранным (скриншоты)
    # *****************************
    def load_favorites(cat):
        screenshots = favorites_manager.get_favorites(cat)  # ожидается dict {path: data}
        screenshots_grid.controls.clear()
        if not screenshots:
            screenshots_grid.controls.append(
                ft.Container(
                    ink=True,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.FAVORITE_BORDER, size=50, color=ft.colors.PRIMARY),
                            ft.Text("Нет избранных скриншотов", size=18, color=ft.colors.PRIMARY),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
        else:
            for path, data in screenshots.items():
                if not Path(path).exists():
                    continue
                thumb = ft.Container(
                    content=ft.Image(
                        src=path,
                        width=150,
                        height=150,
                        fit=ft.ImageFit.COVER,
                        border_radius=ft.border_radius.all(10),
                    ),
                    width=150,
                    height=150,
                    border_radius=ft.border_radius.all(10),
                    ink=True,
                    on_click=lambda e, path=path: show_preview(path, list(screenshots.keys())),
                )
                screenshots_grid.controls.append(thumb)
        page.update()

    # *****************************
    # Функции работы с категориями
    # *****************************
    # Обработчики теперь принимают (cat_name, e)
    def on_select_category(cat_name, e):
        current_category[0] = cat_name
        load_favorites(cat_name)
        # Если был открыт предпросмотр, переключаемся обратно в режим списка
        switch_to_list()
        page.update()

    def on_delete_category(cat_name, e):
        if cat_name == "Общее":
            ft.SnackBar(content=ft.Text("Нельзя удалить категорию 'Общее'")).open = True
            return
        favorites_manager.remove_category(cat_name)
        load_categories()
        load_favorites(current_category[0])
        page.update()

    def load_categories():
        categories_view.controls.clear()

        def on_all_click(e):
            on_select_category(None, e)

        all_button = ft.TextButton(
            text="Все",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=on_all_click,
            style=ft.ButtonStyle(
                color={"": ft.colors.PRIMARY, "hovered": ft.colors.PRIMARY_CONTAINER},
                shape=ft.RoundedRectangleBorder(radius=8),
                animation_duration=200,
            ),
        )
        all_container = ft.Container(
            content=ft.Row([all_button]),
            padding=10,
            border_radius=ft.border_radius.all(8),
            animate=ft.animation.Animation(300, ft.AnimationCurve.FAST_OUT_SLOWIN),
        )
        categories_view.controls.append(all_container)

        cats_dict = favorites_manager.get_categories()
        sorted_cats = sorted(list(cats_dict.keys()), key=lambda x: cats_dict[x]["order"])

        for cat in sorted_cats:
            select_button = ft.TextButton(
                text=cat,
                icon=ft.Icons.FOLDER,
                on_click=partial(on_select_category, cat),
                style=ft.ButtonStyle(
                    color={"": ft.colors.PRIMARY, "hovered": ft.colors.PRIMARY_CONTAINER},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    animation_duration=200,
                ),
            )
            if cat == "Общее":
                delete_button = ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Нельзя удалить",
                    disabled=True,
                )
            else:
                delete_button = ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Удалить",
                    on_click=partial(on_delete_category, cat),
                )
            row = ft.Row(
                controls=[ft.Container(content=select_button, expand=True), delete_button],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            cat_container = ft.Container(
                content=row,
                padding=10,
                border_radius=ft.border_radius.all(8),
                animate=ft.animation.Animation(300, ft.AnimationCurve.FAST_OUT_SLOWIN),
                bgcolor=ft.colors.SURFACE,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=2, color=ft.colors.BLACK12, offset=ft.Offset(0, 1)),
                margin=ft.margin.only(bottom=4),
            )
            categories_view.controls.append(cat_container)

        add_container = ft.Row([
            new_category_field,
            ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=lambda e: add_category(e)),
        ])
        categories_view.controls.append(add_container)
        page.update()

    def add_category(e):
        cat_name = new_category_field.value.strip()
        if not cat_name:
            ft.SnackBar(content=ft.Text("Введите название категории")).open = True
            return
        favorites_manager.add_category(cat_name)
        new_category_field.value = ""
        load_categories()
        load_favorites(current_category[0])
        page.update()

    # *****************************
    # Финальная компоновка интерфейса
    # *****************************
    final_container = ft.Container(content=main_container, expand=True)

    # Основной контейнер состоит из режима списка (list_view).
    # При клике по миниатюре вызывается show_preview(), которое подменяет содержимое main_container.
    main_container = ft.Container(content=list_view, expand=True)

    # Инициализируем режим списка
    load_categories()
    load_favorites(current_category[0])
    
    # Собираем финальный вид: здесь возвращаем main_container, который в дальнейшем меняется функциями переключения.
    return main_container
