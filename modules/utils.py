import os
import chardet

def read_file_with_detect(fpath):
    """
    Считывает содержимое файла, универсально определяя его кодировку.
    """
    try:
        if not os.path.exists(fpath):
            return ""
        with open(fpath, 'rb') as f:
            content = f.read()
        if not content:
            return ""
        result = chardet.detect(content)
        encoding = result['encoding'] or 'utf-8'
        return content.decode(encoding, errors='replace')
    except Exception as e:
        print(f"Ошибка при чтении файла {fpath}: {e}")
        return "" 