import os
import requests
import shutil

def download_file(url, dest_path):
    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки {url}: {e}")
        return False


def backup_and_replace(file_path):
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            shutil.copyfile(file_path, backup_path)
            print(f"📦 Создан бэкап: {backup_path}")
        except Exception as e:
            print(f"⚠️ Не удалось создать бэкап для {file_path}: {e}")


def perform_update(file_list):
    for name, url in file_list:
        target_path = os.path.join(os.getcwd(), name)
        print(f"⬇️ Загружаем {name}...")
        success = download_file(url, target_path + ".tmp")

        if success:
            backup_and_replace(target_path)
            try:
                os.replace(target_path + ".tmp", target_path)
                print(f"✅ Обновлён: {name}")
            except Exception as e:
                print(f"❌ Ошибка замены {name}: {e}")
        else:
            print(f"⏭ Пропускаем {name}, не удалось скачать")


def restart_application():
    print("🔁 Перезапуск приложения...")
    python = os.path.join(os.getcwd(), "python", "python.exe")  # путь к портативному Python
    main_script = os.path.join(os.getcwd(), "main.py")
    os.execv(python, [python, main_script])