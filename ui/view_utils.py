import flet as ft

def set_status(page, message, loading=False):
    """
    Устанавливает текст статуса и отображает/скрывает индикатор загрузки.
    
    Args:
        page (ft.Page): Страница Flet
        message (str): Сообщение для отображения
        loading (bool): Флаг отображения индикатора загрузки
    """
    # Ищем строку статуса на странице
    status_bar = None
    status_text = None
    status_spinner = None
    
    # Перебираем контейнеры на странице
    for container in page.controls:
        if hasattr(container, 'content') and container.content:
            if hasattr(container.content, 'controls'):
                for control in container.content.controls:
                    if isinstance(control, ft.Row) and len(control.controls) >= 2:
                        if isinstance(control.controls[0], ft.Text) and \
                           isinstance(control.controls[-1], ft.ProgressRing):
                            status_bar = control
                            status_text = control.controls[0]
                            status_spinner = control.controls[-1]
                            break
    
    if status_text and status_spinner:
        status_text.value = message
        status_spinner.visible = loading
        page.update()
        return
    
    # Если не нашли строку статуса, ищем в дочерних элементах
    for control in page.controls:
        if hasattr(control, 'content') and control.content:
            if hasattr(control.content, 'controls'):
                for child in control.content.controls:
                    if hasattr(child, 'controls'):
                        for grandchild in child.controls:
                            if isinstance(grandchild, ft.Row) and len(grandchild.controls) >= 2:
                                if isinstance(grandchild.controls[0], ft.Text) and \
                                   any(isinstance(c, ft.ProgressRing) for c in grandchild.controls):
                                    status_text = grandchild.controls[0]
                                    spinner_index = next((i for i, c in enumerate(grandchild.controls) 
                                                         if isinstance(c, ft.ProgressRing)), -1)
                                    if spinner_index != -1:
                                        status_spinner = grandchild.controls[spinner_index]
                                        status_text.value = message
                                        status_spinner.visible = loading
                                        page.update()
                                        return
    
    # Если не нашли статусную строку, показываем snackbar
    page.snack_bar = ft.SnackBar(content=ft.Text(message))
    page.snack_bar.open = True
    page.update()

def find_control_by_type(parent, control_type):
    """
    Рекурсивно ищет элемент управления указанного типа в дереве элементов.
    
    Args:
        parent: Родительский элемент для поиска
        control_type: Тип искомого элемента
        
    Returns:
        Найденный элемент или None
    """
    if isinstance(parent, control_type):
        return parent
    
    # Проверяем, имеет ли родитель содержимое
    if hasattr(parent, 'content') and parent.content:
        result = find_control_by_type(parent.content, control_type)
        if result:
            return result
    
    # Проверяем, имеет ли родитель список элементов
    if hasattr(parent, 'controls'):
        for control in parent.controls:
            result = find_control_by_type(control, control_type)
            if result:
                return result
    
    return None

def find_control_by_predicate(parent, predicate):
    """
    Рекурсивно ищет элемент управления, удовлетворяющий условию.
    
    Args:
        parent: Родительский элемент для поиска
        predicate: Функция-предикат, принимающая элемент и возвращающая bool
        
    Returns:
        Найденный элемент или None
    """
    if predicate(parent):
        return parent
    
    # Проверяем, имеет ли родитель содержимое
    if hasattr(parent, 'content') and parent.content:
        result = find_control_by_predicate(parent.content, predicate)
        if result:
            return result
    
    # Проверяем, имеет ли родитель список элементов
    if hasattr(parent, 'controls'):
        for control in parent.controls:
            result = find_control_by_predicate(control, predicate)
            if result:
                return result
    
    return None