import json
from os.path import exists
from time import time


class DownloadLinks:
    def __init__(self):
        self.file_path = r"MoeList\data\download_links.json"
        self.data = {}
        self.timeout = 30 * 60
        self.downloading_keys = []
        if exists(self.file_path):
            with open(self.file_path) as f:
                self.data = json.load(f)
            # for key in list(self.data.keys()):
            #     if self.get(key) is None:
            #         del self.data[key]
        else:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=4)

    def add(self, key, url):
        self.downloaded(key)
        self.data[key] = (url, int(time()))
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def get(self, key):
        if key in self.data:
            if self.data[key][1] > int(time()) - self.timeout:
                return self.data[key][0]
        return None

    def is_downloading(self, key):
        if key in self.downloading_keys:
            return True
        return False

    def downloading(self, key):
        if key not in self.downloading_keys:
            self.downloading_keys.append(key)
            return True
        return False

    def downloaded(self, key):
        if key in self.downloading_keys:
            self.downloading_keys.pop(self.downloading_keys.index(key))

    @property
    def all_links(self):
        return self.data
