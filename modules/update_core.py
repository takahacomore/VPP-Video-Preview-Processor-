import os
import sys
import requests
import hashlib
import importlib.util

UPDATE_URL = "https://update.takahacomore.ru/update.json"
VERSION_FILE = "version.py"


def get_current_version():
    try:
        spec = importlib.util.spec_from_file_location("version", VERSION_FILE)
        version_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version_module)
        return getattr(version_module, "VERSION", "0.0.0")
    except Exception:
        return "0.0.0"


def parse_version(version_str):
    try:
        return tuple(map(int, version_str.split('_')[0].split('.')))
    except Exception:
        return (0, 0, 0)

def get_update_description(manifest):
    return manifest.get("description", "Описание обновления недоступно.")

def load_update_manifest():
    try:
        resp = requests.get(UPDATE_URL, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        return resp.json()
    except Exception as e:
        print(f"Ошибка загрузки update.json: {e}")
        return None


def compare_versions(local_version, remote_version):
    return parse_version(remote_version) > parse_version(local_version)


def get_files_to_update(manifest):
    files = []
    for name, meta in manifest.get("files", {}).items():
        local_path = os.path.join(os.getcwd(), name)
        if not os.path.exists(local_path):
            files.append((name, meta["url"]))
            continue

        with open(local_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        if file_hash != meta.get("hash"):
            files.append((name, meta["url"]))

    return files



def restart_application():
    """
    Перезапускает приложение, заменяя текущий процесс
    новым запущенным тем же интерпретатором и скриптом main.py.
    """
    print("🔁 Перезапуск приложения...")
    # корень проекта — папка выше modules/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    python_executable = sys.executable
    main_script = os.path.join(project_root, "main.py")
    # этот вызов сам делает replace текущего процесса
    os.execv(python_executable, [python_executable, main_script])

# Пример использования
if __name__ == "__main__":
    current = get_current_version()
    manifest = load_update_manifest()

    if not manifest:
        print("Не удалось загрузить манифест обновлений")
    elif compare_versions(current, manifest["version"]):
        print(f"Доступна новая версия: {manifest['version']}")
        needed = get_files_to_update(manifest)
        print("Нужно обновить файлы:")
        for name, url in needed:
            print(f" - {name}: {url}")
    else:
        print("Установлена последняя версия")
