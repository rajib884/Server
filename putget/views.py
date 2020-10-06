from os.path import exists
from json import dumps

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


def index(request):
    return HttpResponse("Hello, world.")


@csrf_exempt
def put(request):
    if "filename" in request.POST and "key" in request.POST:
        if request.POST["key"] == "fgksyan-aowdu2ii":
            print(request.FILES)
            if 'file' not in request.FILES:
                return HttpResponse(dumps({"Error": "I got no file!"}))
            else:
                default_storage.save(request.POST['filename'], ContentFile(request.FILES['file'].read()))
                return HttpResponse(dumps({"Success": "File Uploaded"}))
        else:
            return HttpResponse(dumps({"Error": "key is not valid"}))
    else:
        return HttpResponse(dumps({"Error": "filename, file or key was not posted"}))


@csrf_exempt
def get(request):
    if "filename" in request.POST and "key" in request.POST:
        if request.POST["key"] == "fgksyan-aowdu2ii":
            if not exists(request.POST['filename']):
                return HttpResponse(dumps({"Error": "File does not exists"}))
            else:
                return HttpResponse(open(request.POST['filename'], "rb").read())
        else:
            return HttpResponse(dumps({"Error": "key is not valid"}))
    else:
        return HttpResponse(dumps({"Error": "filename or key was not posted"}))
