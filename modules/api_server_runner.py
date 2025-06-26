import subprocess
import sys
import os
import signal

_server_process = None
PID_FILE = "api_server.pid"

def start_api_server():
    global _server_process
    if _server_process is not None:
        return  # Уже запущен
    api_server_path = os.path.join(os.path.dirname(__file__), "..", "api_server.py")
    api_server_path = os.path.abspath(api_server_path)
    _server_process = subprocess.Popen([sys.executable, api_server_path])
    # Сохраняем PID
    with open(PID_FILE, "w") as f:
        f.write(str(_server_process.pid))

def stop_api_server():
    global _server_process
    # Сначала пробуем завершить через переменную
    if _server_process is not None:
        _server_process.terminate()
        _server_process = None
    # Потом пробуем завершить по PID из файла
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read())
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)])
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"Ошибка при завершении сервера по PID: {e}")
        os.remove(PID_FILE) 