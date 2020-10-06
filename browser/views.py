import json
import os
from datetime import datetime
from mimetypes import guess_type
from pprint import pprint

import magic
from django.http import FileResponse
from django.http import HttpResponse
from django.template.loader import get_template
from pathvalidate import is_valid_filename

icons = {
    'application': "fa-cogs",
    'audio': "fa-file-audio",
    'image': "fa-file-image",
    'text': "fa-file-alt",
    'video': "fa-file-video",
    'message': "fa-envelope-open",
    'inode': "fa-file",
    'PermissionError': "fa-ban"
}


def http404(text, request=None):
    r = HttpResponse(text)
    r.status_code = 404
    return r


def index(request):
    if "path" in request.GET:
        if os.path.exists(request.GET["path"]):
            if os.path.isdir(request.GET["path"]):
                return HttpResponse(get_template('Browser/index.html').render(pp(request.GET["path"]), request))
            else:
                return HttpResponse(f"{request.GET['path']} is not a directory..")
        else:
            return HttpResponse(f"{request.GET['path']} does not exists..")
    elif "open" in request.GET:
        return open_file(request)
        # return open_file(request)
    else:
        files = {
            'current': None,
            'folders': [("fa-folder", p, None) for p in ["C:/", "D:/", "E:/", "F:/", "G:/"] if os.path.exists(p)],
            'files': []
        }
        return HttpResponse(get_template('Browser/index.html').render(files, request))
        # return HttpResponse("Hello, world. You're at the polls index.")


def file_methods(request):
    if request.method == 'GET':
        return HttpResponse("Use POST")
    elif request.method == 'POST':
        if all(key in request.POST for key in ["method", "file"]):
            pprint(request.POST["file"])
            if request.POST["method"] == 'delete':
                return HttpResponse(json.dumps({
                    "alert": f"{os.path.basename(request.POST['file'])} was deleted successfully (no)"
                }))
            elif request.POST["method"] == 'rename':
                if 'new_name' in request.POST:
                    if is_valid_filename(request.POST['new_name']):
                        if os.path.exists(request.POST['file']):
                            return HttpResponse(json.dumps({
                                "alert": f"{os.path.basename(request.POST['file'])} was renamed",
                                "old_name": os.path.basename(request.POST['file']),
                                "new_name": request.POST['new_name'],
                            }))
                        else:
                            return HttpResponse(json.dumps({
                                "error": f"{request.POST['file']} does not exists"
                            }))
                    else:
                        return HttpResponse('{"error": "New Name is not valid"}')
                else:
                    return HttpResponse('{"error": "New name was not provided"}')
        else:
            return HttpResponse('{"error": "Invalid keys"}')


def check_file_name(request):
    if "file_name" in request.POST:
        print(request.POST["file_name"])
        if is_valid_filename(request.POST["file_name"]):
            return HttpResponse("true")
        else:
            return HttpResponse("false")
    else:
        return http404("'file_name' not found")


# def open_file(request):
#     if request.GET and 'open' in request.GET:
#         file = request.GET['open']
#     elif request.POST:
#         return HttpResponse("POSTing data? success")
#     else:
#         return HttpResponse("Set path= something")
#
#     if not os.path.isfile(file):
#         return HttpResponse(file + "<br>It is not a file")
#     try:
#         fp = open(file, "rb")
#     except PermissionError:
#         return HttpResponse(file + "<br>Server does not have permission to view this file.")
#     size = os.path.getsize(file)
#     length = size
#     start = 0
#     end = size - 1
#
#     if file.endswith(".vtt"):
#         mime = "text/vtt"
#     else:
#         # mime = Magic(mime=True).from_file(file)
#         # mime, encoding = guess_type(file)
#         mime = magic.from_file(file, True)
#
#     response = HttpResponse(content_type=mime)
#
#     response['Accept-Ranges'] = "0-" + str(length)
#
#     if 'Range' in request.headers:
#         c_end = end
#         req_range = request.headers['Range'].split("=", 2)[1]
#         print(request.headers['Range'])
#
#         if "," in req_range:
#             response.status_code = 416
#             response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
#             return response
#
#         if req_range == "-":
#             c_start = size - int(req_range[1:])
#         else:
#             req_range = req_range.split('-')
#             c_start = int(req_range[0])
#             if req_range[1]:
#                 c_end = int(req_range[1])
#             else:
#                 c_end = size
#
#         if c_end > end:
#             c_end = end
#
#         if c_start > c_end or c_start > size - 1 or c_end >= size:
#             response.status_code = 416
#             response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
#             return response
#
#         start = c_start
#         end = c_end
#         length = end - start + 1
#         fp.seek(start)
#         response.status_code = 206
#
#     response['Content-Disposition'] = "attachment; filename=%s" % os.path.basename(file)
#     response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
#     response['Content-Length'] = length
#     response.content = fp.read(length)
#     fp.close()
#     return response


def open_file(request):
    if request.GET and 'open' in request.GET:
        file = request.GET['open']
    elif request.POST:
        return HttpResponse("POSTing data? success")
    else:
        return HttpResponse("Set path= something")
    if not os.path.isfile(file):
        return HttpResponse(file + "<br>It is not a file")

    try:
        fp = open(file, "rb")
    except PermissionError:
        return HttpResponse(file + "<br>Server does not have permission to view this file.")

    size = os.path.getsize(file)
    length = size
    start = 0
    end = size - 1
    if 'Range' in request.headers:
        response = HttpResponse()
        response['Content-Type'] = magic.from_file(file, True)
        c_end = end
        req_range = request.headers['Range'].split("=", 2)[1]

        if "," in req_range:
            response.status_code = 416
            response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
            return response

        if req_range == "-":
            c_start = size - int(req_range[1:])
        else:
            req_range = req_range.split('-')
            c_start = int(req_range[0])
            c_end = int(req_range[1]) if req_range[1] else size

        if c_end > end:
            c_end = end

        if c_start > c_end or c_start > size - 1 or c_end >= size:
            response.status_code = 416
            response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
            return response

        start = c_start
        end = c_end
        length = end - start + 1
        fp.seek(start)
        response.status_code = 206
        response.content = fp.read(length)
        fp.close()
    else:
        response = HttpResponse() if request.method == 'HEAD' else FileResponse(fp)
        response['Content-Type'] = magic.from_file(file, True)

    # response['Content-Disposition'] = "attachment; filename=%s" % os.path.basename(file)
    response['Content-Length'] = length
    response['Accept-Ranges'] = "0-" + str(length)
    response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)

    return response


def pp(path, return_json=False):
    files = {
        'current': path if path[-1] == "/" else path + "/",
        'current_as_list': path[:-1].split("/") if path[-1] == "/" else path.split("/"),
        'folders': [],
        'files': []
    }
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            files['folders'].append(
                (
                    "fa-folder",
                    file,
                    datetime.utcfromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                )
            )
        else:
            # file_type = guess_type(file_path)[0] or "Unknown"
            try:
                # file_type = magic.from_file(file_path, True)
                # file_type = guess_type(file_path)[0] or "PermissionError"
                file_type = guess_type(file_path)[0] or magic.from_file(file_path, True)
            except PermissionError:
                file_type = "PermissionError"
            files['files'].append(
                (
                    icons[file_type.split("/")[0]],
                    file,
                    datetime.utcfromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                    file_type,
                    human_size(file_path)
                )
            )
    if return_json:
        return json.dumps(files, indent=4)
    else:
        return files


def human_size(path: str) -> str:
    size = os.path.getsize(path)
    s = ["byte", "KB", "MB", "GB"]
    if size < 1:
        return f"{size} byte"
    for n, st in enumerate(s):
        if 1024 ** n <= size <= 1024 ** (n + 1):
            return "{} {}".format(
                round(size / 1024 ** n, 2),
                st
            )
    else:
        return "{} {}".format(
            round(size / 1024 ** (len(s) - 1), 2),
            s[-1]
        )
