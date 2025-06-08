import os
import zipfile
import urllib.request
import subprocess
import threading
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE  = os.path.join(BASE_DIR, "python", "python.exe")
MAIN_PATH   = os.path.join(BASE_DIR, "main.py")
ARCHIVE_URL = "https://update.takahacomore.ru/VPP.zip"
ARCHIVE_PATH= os.path.join(BASE_DIR, "VPP.zip")
GIF_PATH    = os.path.join(BASE_DIR, "assets", "loading.gif")  # ваш GIF

def download_and_extract():
    urllib.request.urlretrieve(ARCHIVE_URL, ARCHIVE_PATH)
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as zip_ref:
        zip_ref.extractall(BASE_DIR)
    os.remove(ARCHIVE_PATH)

def ensure_main_exists():
    if not os.path.exists(MAIN_PATH):
        download_and_extract()

def run_app():
    if not os.path.exists(PYTHON_EXE):
        print("❌ Python не найден!")
        return
    subprocess.run([PYTHON_EXE, "main.py"], cwd=BASE_DIR, shell=True)

def show_splash_and_download():
    # создаём окно
    root = tk.Tk()
    root.title("Загрузка VPP")
    root.overrideredirect(True)  # убираем рамки

    # Размер и позиционирование под GIF 600x390 + текст
    win_w, win_h = 600, 480
    x = (root.winfo_screenwidth() - win_w) // 2
    y = (root.winfo_screenheight() - win_h) // 2
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # Загружаем кадры GIF
    gif = Image.open(GIF_PATH)
    frames = [ImageTk.PhotoImage(frame.copy()) for frame in ImageSequence.Iterator(gif)]
    lbl = tk.Label(root)
    lbl.pack(fill="both", expand=True)

    def animate(ind=0):
        lbl.config(image=frames[ind])
        root.after(100, animate, (ind+1) % len(frames))

    # Текстовое сообщение снизу
    text_label = tk.Label(
        root,
        text=("Спасибо что установили VPP. Сейчас я докачиваю все необходимые компоненты, "
              "пожалуйста, дождитесь загрузки."),
        font=("Arial", 12),
        wraplength=win_w - 20,
        justify="center"
    )
    text_label.pack(side=tk.BOTTOM, fill="x", pady=10)

    # Кнопка закрытия поверх всего
    close_btn = tk.Button(
        root,
        text="✕",
        command=root.destroy,
        bd=0,
        bg=root.cget('bg'),
        font=("Arial", 12, "bold")
    )
    close_btn.place(x=win_w - 25, y=5, width=20, height=20)
    close_btn.lift()

    # По завершении загрузки закрываем окно
    def loader():
        ensure_main_exists()
        try:
            if root.winfo_exists():
                root.destroy()
        except Exception:
            pass

    animate()
    threading.Thread(target=loader, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    show_splash_and_download()
    run_app()
