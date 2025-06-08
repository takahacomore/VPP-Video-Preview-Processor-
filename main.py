import sys
import os
import subprocess

req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(req_path):
    with open(req_path, encoding="utf-8") as f:
        pkgs = [line.strip().split('==')[0].split('>=')[0].split('<=')[0] for line in f if line.strip() and not line.startswith('#')]
    need_install = False
    for pkg in pkgs:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            need_install = True
            break
    if need_install:
        python_exe = sys.executable
        subprocess.check_call([python_exe, "-m", "pip", "install", "-r", req_path])

# Теперь запускаем настоящий main (app_main.py)
subprocess.check_call([sys.executable, os.path.join(os.path.dirname(__file__), "app_main.py")])