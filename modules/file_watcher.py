import os

class FileWatcher:
    def __init__(self, directory):
        self.directory = directory
        self.watched_files = set()
        self.update_files()

    def update_files(self):
        new_files = set()
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    new_files.add(os.path.join(root, file))

        added_files = new_files - self.watched_files
        removed_files = self.watched_files - new_files

        if added_files or removed_files:
            self.watched_files = new_files
            return list(self.watched_files)
        return []

    def get_files(self):
        return list(self.watched_files)
