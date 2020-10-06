import json
import queue
import threading
from os.path import basename, exists
from time import sleep

import requests

currently_downloading_file = False


def handler(start, end, url, filename, que, thread_number):
    headers = {'Range': 'bytes=%d-%d' % (start, end)}
    r = requests.get(url, headers=headers, stream=True)
    with open(filename, "r+b") as fp:
        fp.seek(start)
        for data in r.iter_content(chunk_size=4096):
            fp.write(data)
            que.put((thread_number, fp.tell()))
    que.put((thread_number, True))


def progress_bar(tell_positions, part_size, full_size):
    total_char = max(round(30 / len(tell_positions)), 10)
    downloaded_size = sum([d - part_size * n for n, d in enumerate(tell_positions)])
    txt = "["
    for n, tell_position in enumerate(tell_positions):
        number_of_hash = round(total_char * (tell_position - n * part_size) / part_size)
        txt += "#" * number_of_hash + "-" * (total_char - number_of_hash) + "|"
    txt = txt[:-1] + "] "
    txt += "{:5.2f}% {}/{}".format(
        round(100 * downloaded_size / full_size, 2),
        mb(downloaded_size),
        mb(full_size),
    )
    return txt


def mb(size):
    return "{:5.2f}MB".format(round(size / 1048576, 2))


def download_file(url, file_name=None, number_of_threads=4):
    global currently_downloading_file
    if not currently_downloading_file:
        currently_downloading_file = True
    else:
        while currently_downloading_file:
            sleep(5)
            print("Waiting..")
        currently_downloading_file = True
    r = requests.head(url)
    if file_name is None:
        file_name = url.split('/')[-1]
    print(f"File Name: {file_name}")
    try:
        file_size = int(r.headers['content-length'])
    except ValueError:
        print("Invalid URL")
        return None
    print(f"File Size: {mb(file_size)}")

    part = round(int(file_size) / number_of_threads)
    if exists(file_name):
        if exists(f"{basename(file_name)}.json"):
            with open(f"{file_name}.json", "r") as f:
                tell_positions = json.load(f)
        else:
            raise FileExistsError
    else:
        tell_positions = None
        with open(file_name, "wb") as fp:
            fp.write(b'\0' * file_size)

    que = queue.Queue()
    resume = tell_positions is not None and len(tell_positions) == number_of_threads
    for thread_number in range(number_of_threads):
        start = part * thread_number
        end = start + part
        if resume:
            start = max(tell_positions[thread_number] - 8192, start)
        threading.Thread(
            target=handler,
            daemon=True,
            kwargs={
                'start': start,
                'end': end,
                'url': url,
                'filename': file_name,
                'que': que,
                'thread_number': thread_number
            }
        ).start()
        sleep(0.1)

    tell_positions = [0] * number_of_threads
    currently_downloading = [True] * number_of_threads
    while any(currently_downloading):
        try:
            t = que.get()
            if type(t[1]) == int:
                tell_positions[t[0]] = t[1]
            elif t[1] is True:
                currently_downloading[t[0]] = False
            try:
                with open(f"{basename(file_name)}.json", "w") as f:
                    json.dump(tell_positions, f)
            except OSError:
                print("OSError writing to json!")
                print(tell_positions)
            print(f"\r{progress_bar(tell_positions, part, file_size)}", end="")
        except queue.Empty:
            sleep(0.1)
    download_status = sum([d - part * n for n, d in enumerate(tell_positions)]) == file_size
    print(f"\nDownload Complete: {download_status}")
    print('%s downloaded' % file_name)
    currently_downloading_file = False
    return download_status
