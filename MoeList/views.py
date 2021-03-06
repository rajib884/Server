import datetime
import json
import os
# import pickle
import secrets
# import random
import threading
from mimetypes import guess_type
from os import path, system
from pprint import pprint
from subprocess import Popen
from time import sleep
from urllib.parse import urlparse, parse_qs

import magic
import requests
from django.http import FileResponse
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse
from fuzzywuzzy import process
from send2trash import send2trash, TrashPermissionError

from MoeList.Backbone import anilist, animepahe
from MoeList.Backbone.DowonloadLinks import DownloadLinks
from MoeList.Backbone.backbone import FileList
from MoeList.Backbone.myanimelist import MAL

animelist = FileList()
download_links = DownloadLinks()
mal = MAL()
variables = {
    "view": "List",
    "select_random": False,
    "show_deleted_ep": False,
    "show_watched_ep": True,
    "show_new_ep": True,
    "show_downloadable_ep": True,
    "deleted": None,
    "watched": None,
    "genre": None,
    "year": None,
    "typ": None,
    "season": None,
    "status": None
}

try:
    variables = json.load(open("options.json", "rb"))
except FileNotFoundError:
    pass

variables["views"] = ["Card", "List"]
variables["genres"] = animelist.available_genres
variables["years"] = animelist.available_years
variables["types"] = animelist.available_types
variables["seasons"] = animelist.available_seasons
variables["statuses"] = animelist.available_statuses


# noinspection PyUnusedLocal
def http404(text, request=None):
    r = HttpResponse(text)
    r.status_code = 404
    return r


# noinspection PyUnusedLocal
def http200(text, request=None):
    r = HttpResponse(text)
    r.status_code = 200
    return r


def anime(request, anilist_id):
    anilist_id = str(anilist_id)
    if anilist_id not in animelist.data:
        animelist.update_anilist_data(anilist_id)

    context = {
        'anilist_id': anilist_id,
        'anime': animelist.data[anilist_id],
        'cover': animelist.get_cover(anilist_id),
        'banner': animelist.get_banner(anilist_id),
        'episodes': get_template('MoeList/ep_sorted.html').render(animelist.get_episode_sorted(anilist_id)),
        'relations': animelist.get_relations(anilist_id),
        'mal_id': animelist.data[anilist_id].get('mal'),
        'navbar': variables
    }
    return HttpResponse(get_template('MoeList/anime.html').render(context, request))


def update_variables(request, name, value):
    if name in variables:
        if value == 1:
            variables[name] = True
        elif value == 2:
            variables[name] = False
        else:
            variables[name] = None
        json.dump(variables, open("options.json", "w"), indent=4, sort_keys=True)
        return HttpResponseRedirect(reverse('MoeList:index'))
    else:
        return http404("Name not in variables", request)


def update_options(request, key, value):
    variables[key] = None if value == "All" else value
    json.dump(variables, open("options.json", "w"), indent=4, sort_keys=True)
    return HttpResponseRedirect(reverse('MoeList:index'))


def import_mal(request):
    # todo: Finish this
    if request.method == 'POST' and request.FILES['myfile']:
        # animelist.import_mal(request.FILES['myfile'])
        threading.Thread(target=animelist.import_mal, daemon=True, kwargs={"f": request.FILES['myfile']}).start()
        context = {
            "banner": animelist.random_banner,
            "navbar": variables
        }
        return HttpResponse(get_template('MoeList/import_mal.html').render(context, request))
    elif request.method == 'GET' and 'print' in request.GET:
        t = ""
        while len(animelist.to_print) != 0:
            t += animelist.to_print.pop(0) + "\n"
        return http200(t)
    elif request.method == 'GET' and 'code' in request.GET:
        if mal.process_code(request.GET['code'], request.build_absolute_uri(reverse('MoeList:importMAL'))):
            return http200("Success")
        else:
            return http200("Failed")
    else:
        return HttpResponseRedirect(reverse('MoeList:settings'))


def mal_handler(request):
    if request.POST and 'id' in request.POST:
        pprint(request.POST)
        return http200(json.dumps(
            mal.update_user_list(request.POST['id'], request.POST['status'], request.POST['ep'], request.POST['score']),
            indent=4))
    elif request.GET and 'id' in request.GET:
        return HttpResponse(
            get_template('MoeList/mal_part.html').render({'mal': mal.get_anime_info(request.GET['id'])}))
    elif request.GET and 'user_list' in request.GET:
        t = {}
        anilist_ids = list(animelist.data.keys())
        for p in mal.current_user_anime_list(limit=5000).get('data', []):
            mal_id = p['node']['id']
            anilist_id = animelist.get_key_by_mal(mal_id)
            if anilist_id is None:
                try:
                    anilist_id = str(anilist.mal_to_anilist(mal_id))
                except KeyError:
                    print(f"KeyError with mal id {mal_id}")
                    continue

            anilist_data = animelist.data.get(anilist_id, None)
            if anilist_data is None and animelist.update_anilist_data(anilist_id):
                print(f"Anime with anilist id {anilist_id} was not found, was downloaded")
                anilist_data = animelist.data.get(anilist_id, {})

            t[anilist_id] = {
                'title': anilist_data.get('title', 'Unavailable'),
                'id': mal_id,
                'status': p['list_status']['status'],
                'score': p['list_status']['score'],
                'watched_ep': p['list_status']['num_episodes_watched'],
                'num_episodes': p['node']['num_episodes'],
                'local_watched_ep': animelist.get_max_watched_ep(anilist_id),
                'local_num_episodes': int(animelist.get_max_ep(anilist_id)),
            }
            try:
                anilist_ids.remove(anilist_id)
            except ValueError:
                pass
        for anilist_id in anilist_ids:
            mal_id = animelist.data[anilist_id].get('mal', None)
            if mal_id is None and animelist.update_anilist_data(anilist_id):
                print(f"MAL id of anilist {anilist_id} was not found, was downloaded")
                mal_id = animelist.data.get('mal', None)
            t[anilist_id] = {
                'title': animelist.data[anilist_id]['title'],
                'id': mal_id,
                'status': None,
                'score': 0,
                'watched_ep': 0,
                'num_episodes': 0,
                'local_watched_ep': animelist.get_max_watched_ep(anilist_id),
                'local_num_episodes': int(animelist.get_max_ep(anilist_id)),
            }
        return HttpResponse(get_template('MoeList/mal_data_compare.html').render({'data': t}, request))
    else:
        pprint(request.POST)
        return HttpResponse("Send key value via POST")


def data_json(request):
    return http200(animelist.data_json)


def data_summary(request):
    return http200(animelist.data_summary_json)


def index(request):
    if variables["select_random"] is True:
        try:
            return anime(request, anilist_id=secrets.choice(animelist.get_keys(**variables)))
        except IndexError:
            pass

    eps_template = get_template('MoeList/ep_sorted.html')
    anime_list = []
    if variables["view"] == "List":
        years = []
        x = datetime.datetime.now()
        for anilist_id in animelist.get_keys(**variables):
            year = x.year if animelist.data[anilist_id]["year"] is None else animelist.data[anilist_id]["year"]
            if year not in years:
                years.append(year)
            if animelist.data[anilist_id]["status"] == "RELEASING":
                anime_list.append(
                    {
                        "airing": True,
                        "deleted": animelist.is_deleted(anilist_id),
                        "completed": animelist.is_completed(anilist_id),
                        "nextEp": animelist.airing_time(anilist_id),
                        "episodes": eps_template.render(animelist.get_episode_sorted(anilist_id, False, False, False)),
                        "name": animelist.data[anilist_id]["title"],
                        "cover_small": animelist.get_small_cover(anilist_id),
                        "id": anilist_id
                    }
                )
        context = {
            "anime_list": anime_list,
            "years": sorted(years, reverse=True),
            "banner": animelist.random_banner,
            "navbar": variables
        }
        return HttpResponse(get_template('MoeList/listview.html').render(context, request))
    # elif variables["view"] == "List Old":
    #     return HttpResponse(get_template('MoeList/listview_old.html').render(context, request))
    else:
        variables["view"] = "Card"
        for anilist_id in animelist.get_keys(**variables):
            anime_list.append(
                {
                    "airing": True if animelist.data[anilist_id]["status"] == "RELEASING" else False,
                    "deleted": animelist.is_deleted(anilist_id),
                    "episodes": eps_template.render(animelist.get_episode_sorted(anilist_id, False, False, True)),
                    "name": animelist.data[anilist_id]["title"],
                    "cover": animelist.get_cover(anilist_id),
                    "id": anilist_id
                }
            )
        context = {
            "anime_list": anime_list,
            "banner": animelist.random_banner,
            "navbar": variables
        }
        return HttpResponse(get_template('MoeList/index.html').render(context, request))


def index_part(request, year=None):
    if year is None:
        return http404("Year Not Provided", request)
    anime_list = []
    episodes_template = get_template('MoeList/ep_sorted.html')
    for anilist_id in animelist.get_keys(year0=year, sorted_by_year=True, **variables)[year]:
        anime_list.append({
            "airing": True if animelist.data[anilist_id]["status"] == "RELEASING" else False,
            "deleted": animelist.is_deleted(anilist_id),
            "completed": animelist.is_completed(anilist_id),
            "nextEp": animelist.airing_time(anilist_id),
            "episodes": episodes_template.render(animelist.get_episode_sorted(anilist_id, False, False, False)),
            "name": animelist.data[anilist_id]["title"],
            "cover_small": animelist.get_small_cover(anilist_id),
            "id": anilist_id
        })
    context = {
        "anime_list": anime_list,
        "year": year,
    }
    return HttpResponse(get_template('MoeList/listview_part.html').render(context, request))


def anime_watched_all(request, anilist_id):
    anilist_id = str(anilist_id)
    if anilist_id not in animelist.data:
        return http404(f"{anilist_id} was not found", request)
    else:
        if animelist.watched_all(anilist_id):
            return HttpResponseRedirect(reverse('MoeList:anime', args=[int(anilist_id)]))
        else:
            return http404("Failed!!", request)


def reload_info(request, anilist_id):
    anilist_id = str(anilist_id)
    if anilist_id not in animelist.data:
        return http404(f"{anilist_id} was not found", request)
    else:
        if animelist.update_anilist_data(anilist_id):
            return HttpResponseRedirect(reverse('MoeList:anime', args=[int(anilist_id)]))
        else:
            return http404("Failed!!", request)


def episodes(request, anilist_id, ep):
    anilist_id = str(anilist_id)
    ep = str(ep)
    if anilist_id in animelist.data:
        if ep in animelist.data[anilist_id]['episode_list']:
            episode = animelist.data[anilist_id]['episode_list'][ep]
            context = {
                'anime': animelist.data[anilist_id],
                'episode': episode,
                'episodes': animelist.get_episodes_thumb(anilist_id),
                'anilist_id': anilist_id,
                'ep': ep,
                'watchedPart': animelist.data[anilist_id]["episode_list"][ep].get("watchedPart", []),
                'lastWatched': animelist.data[anilist_id]["episode_list"][ep].get("watchedPart", [0])[-1],
                'thumb': None if not
                path.exists(r"D:\PythonServer\MoeList\static\MoeList\thumbnails\{} ep {}.jpeg".format(
                    animelist.data[anilist_id]['slug'], ep)
                ) else r"MoeList\thumbnails\{} ep {}.jpeg".format(
                    animelist.data[anilist_id]['slug'], ep
                ),
                "navbar": variables
            }
            t = animelist.get_next_ep(anilist_id, ep)
            if t is not None:
                context["next_ep"] = int(t)
            t = animelist.get_prev_ep(anilist_id, ep)
            if t is not None:
                context["prev_ep"] = int(t)
            if episode['path'] is not None and path.exists(episode['path']):
                mime, encoding = guess_type(episode['path'])
                if mime == 'video/x-matroska':
                    sub = episode['path'] + '.vtt'
                    if not path.exists(sub):
                        system("{} -i \"{}\" \"{}\"".format(
                            path.join(os.getcwd(),
                                      r"MoeList\Backbone\ffmpeg.exe"
                                      ), episode['path'], sub
                        ))
                    context['sub'] = sub
                return HttpResponse(get_template('MoeList/episode.html').render(context, request))
            else:
                # todo:needs work here, make a deleted ep page
                return http200(f"path {episode['path']} is not found", request)
                # return HttpResponseRedirect(reverse('MoeList:anime', args=(anilist_id,)))
        else:
            return http200(f"ep {ep} is not in episode_list", request)
            # return HttpResponseRedirect(reverse('MoeList:anime', args=(anilist_id,)))
    else:
        return http200(f"anilist_id {anilist_id} not in data", request)
        # return HttpResponseRedirect(reverse('MoeList:index'))


# noinspection PyShadowingNames
def watched_part(request, anilist_id, ep):
    anilist_id = str(anilist_id)
    ep = str(ep)
    if anilist_id in animelist.data:
        anime = animelist.data[anilist_id]
        if ep in anime['episode_list']:
            if "watchedPart" in request.POST:
                part = int(request.POST["watchedPart"])
                if "watchedPart" in anime["episode_list"][ep]:
                    if part in anime["episode_list"][ep]["watchedPart"]:
                        anime["episode_list"][ep]["watchedPart"].remove(part)
                    anime["episode_list"][ep]["watchedPart"].append(part)
                else:
                    anime["episode_list"][ep]["watchedPart"] = [part]
                animelist._changed = True
                return http200(f"Added {part} in watchedPart of {anime['title']} ep {ep}", request)
    return http404("Error", request)


# def open_file(request):
#     if request.GET and 'path' in request.GET:
#         file = request.GET['path']
#     elif request.POST:
#         return HttpResponse("POSTing data? success")
#     else:
#         return HttpResponse("Set path= something")
#
#     if not path.isfile(file):
#         return HttpResponse(file + "<br>It is not a file")
#
#     fp = open(file, "rb")
#     size = path.getsize(file)
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
#     response['Content-Disposition'] = "attachment; filename=%s" % path.basename(file)
#     response['Content-Range'] = "bytes {}-{}/{}".format(start, end, size)
#     response['Content-Length'] = length
#     response.content = fp.read(length)
#     fp.close()
#     return response
def open_file(request):
    if request.GET and 'path' in request.GET:
        file = request.GET['path']
    elif request.POST:
        return HttpResponse("POSTing data? success")
    else:
        return HttpResponse("Set path= something")

    if not path.isfile(file):
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


def filepath(request):
    if request.method == 'GET':
        return HttpResponse("Use POST")
    elif request.method == 'POST':
        if "anilist_id" in request.POST and "ep" in request.POST:
            anilist_id = str(int(request.POST['anilist_id']))
            ep = str(int(request.POST['ep']))
            if anilist_id in animelist.data:
                # noinspection PyShadowingNames
                anime = animelist.data[anilist_id]
                if ep in anime['episode_list']:
                    if anime['episode_list'][ep]['path'] is not None:
                        return HttpResponse(anime['episode_list'][ep]['path'])
                else:
                    return http404("Could not find episode", request)
            else:
                return http404("Anilist id not correct", request)
        else:
            return http404("Set anilist_id and ep", request)


def trash_file(request):
    if request.method == 'GET':
        return HttpResponse("Use POST")
    elif request.method == 'POST':
        if "anilist_id" in request.POST and "ep" in request.POST:
            anilist_id = str(int(request.POST['anilist_id']))
            ep = str(int(request.POST['ep']))
            if anilist_id in animelist.data:
                # noinspection PyShadowingNames
                anime = animelist.data[anilist_id]
                if ep in anime['episode_list']:
                    if anime['episode_list'][ep]['path'] is not None:
                        if path.isfile(anime['episode_list'][ep]['path']):
                            msg = "Deleted {}".format(anime['episode_list'][ep]['path'])
                            try:
                                send2trash(anime['episode_list'][ep]['path'])
                            except TrashPermissionError:
                                return http404("TrashPermissionError!! Are u using android??", request)
                            anime['episode_list'][ep]['path'] = None
                            animelist.save_data()
                            return HttpResponse(msg)
                        else:
                            return http404(
                                "{} is not file".format(anime['episode_list'][ep]['path']), request)
                else:
                    return http404("Could not find episode", request)
            else:
                return http404("Anilist id not correct", request)
        else:
            return http404("Set anilist_id and ep", request)


def file_handler(request):
    if request.method == 'GET':
        return HttpResponse("Use POST")
    elif request.method == 'POST':
        if all(key in request.POST for key in ["anilist_id", "ep", "method", "text"]):
            anilist_id = str(int(request.POST['anilist_id']))
            ep = str(int(request.POST['ep']))
            method = str(request.POST['method'])
            text = str(request.POST["text"])
            if anilist_id in animelist.data:
                if ep in animelist.data[anilist_id]['episode_list']:
                    if method == "toggle":
                        if text == "Watched":
                            w = True
                            response = "New"
                        elif text == "New":
                            w = False
                            response = "Watched"
                        else:
                            return http404("Set text to 'Watched' or 'New'", request)

                        # animelist.data[anilist_id]['episode_list'][ep]['watched'] = w
                        animelist.watched(anilist_id, ep, w)
                        # animelist.save_data()

                    elif method == "open":
                        if animelist.data[anilist_id]['episode_list'][ep]['path'] is not None:
                            Popen(
                                r'explorer /select,"{}"'.format(animelist.data[anilist_id]['episode_list'][ep]['path']))
                        else:
                            return http404("File path None", request)
                        response = "opened {}".format(animelist.data[anilist_id]['episode_list'][ep]['path'])
                    else:
                        return http404("set method to 'open' or 'toggle", request)

                    return HttpResponse(json.dumps({
                        "anilist_id": anilist_id,
                        "ep": ep,
                        "method": method,
                        "text": text,
                        "response": response
                    }, indent=4, sort_keys=True))
                elif ep not in animelist.data[anilist_id]['episode_list'] and method == "toggle" and text == "Watched":
                    animelist.watched(anilist_id, ep)
                    # animelist.data[anilist_id]['episode_list'][ep] = {
                    #     "path": None,
                    #     "watched": True
                    # }
                    # animelist.save_data()
                    return HttpResponse(json.dumps({
                        "anilist_id": anilist_id,
                        "ep": ep,
                        "method": method,
                        "text": text,
                        "response": "New"
                    }, indent=4, sort_keys=True))
                else:
                    return http404("Could not find episode", request)
            else:
                return http404("Anilist id not correct", request)
        else:
            return http404("Set anilist_id, ep, text and method", request)


def get_downloadable_ep_http(request, anilist_id):
    return HttpResponse(get_template('MoeList/ep_new.html').render({
        'episodes': get_downloadable_ep(anilist_id),
        'anilist_id': anilist_id
    }))


def get_downloadable_ep_http_refresh(request, anilist_id):
    return HttpResponse(get_template('MoeList/ep_new.html').render({
        'episodes': get_downloadable_ep(anilist_id, refresh=True),
        'anilist_id': anilist_id
    }))


def get_kwik_link_from_session(request):
    keys = ["anime_id", "session", "anilist_id", "ep"]
    if all(key in request.POST for key in keys):
        return HttpResponse(get_template('MoeList/ep_new_link.html').render({
            'link': animepahe.get_kwik_link(
                request.POST["anime_id"],
                request.POST["session"],
                request.POST["anilist_id"],
                request.POST["ep"]
            ),
            'anilist_id': request.POST["anilist_id"],
            'ep': request.POST["ep"],
        }))
    else:
        return http404(f"{', '.join(keys)} not sent!", request)


def get_downloadable_ep(anilist_id: str, force: bool = False, refresh: bool = False):
    anilist_id = str(anilist_id)
    if anilist_id in animelist.data:
        anime = animelist.data[anilist_id]
        max_ep = animelist.get_max_ep(anilist_id)
        if not force and anime["status"] != "RELEASING" and int(anime["episodes"] or 0) <= int(max_ep):
            # print(f"Max ep ok: {animelist.data[anilist_id]['title']}")
            return []
        else:
            if not force and not refresh and "downloadableEp" in anime:
                if len(anime["downloadableEp"]) == 0:
                    max_downloadable_ep = int(animelist.get_max_ep(anilist_id))
                else:
                    max_downloadable_ep = max([dep['episode'] for dep in anime["downloadableEp"]])
                return_cache = False
                if max_downloadable_ep >= (anime["episodes"] or 0):
                    return_cache = True
                if anime["nextEp"] is not None and int(anime["nextEp"]["episode"]) <= max_downloadable_ep + 1:
                    return_cache = True
                if return_cache:
                    cache = []
                    for dep in animelist.data[anilist_id]["downloadableEp"]:
                        if str(dep['episode']) not in animelist.data[anilist_id]["episode_list"]:
                            cache.append(dep)
                    # print(f"Returned from cache {animelist.data[anilist_id]['title']}")
                    return cache

            print(f"Downloading animepahe data of {animelist.data[anilist_id]['title']}")
            if animelist.data[anilist_id].get("animepahe_id") is None:
                return {"error": "Anime does not have animepahe id"}
            res = animepahe.animepahe_data(
                animepahe_id=animelist.data[anilist_id].get("animepahe_id"),
                find_till=int(max_ep),
                offset=animelist.animepahe_offset.get(anilist_id, 0)
            )
            if "error" in res:
                return res
            # pprint(res)
            eps = []
            for r in res["data"]:
                # noinspection PyTypeChecker
                if int(r["episode"]) > int(max_ep):
                    eps.append(r)
            animelist.data[anilist_id]["downloadableEp"] = eps
            animelist._changed = True
            return eps
    else:
        raise KeyError


# noinspection PyUnusedLocal
def get_specific_ep_data(request):
    pass


def get_download_link_from_kwik(request, link, idm=False):
    if "/" not in link:
        link = "https://kwik.cx/f/" + link

    while download_links.is_downloading(link) or not download_links.downloading(link):
        sleep(1)

    if download_links.get(link) is not None:
        download_links.downloaded(link)
        print("Returned url from cache\nurl: {}".format(download_links.get(link)))
        return HttpResponseRedirect(download_links.get(link))

    t = animepahe.download_link(link)
    if 'error' in t:
        return http404(t['error'], request)

    url = t['link']
    download_links.add(link, url)

    if idm:
        idm_path = r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe"
        if path.exists(idm_path):
            if 'file' in parse_qs(urlparse(url).query):
                filename = r'/f "{}"'.format(parse_qs(urlparse(url).query)['file'][0])
                print(f"File Name: {filename}")
            else:
                filename = ""
            system(r'""{}" /a /n /d "{}" {}"'.format(idm_path, url, filename))
            system(r'""{}" /s"'.format(idm_path))
        else:
            print("Error. IDM does not exists")
    else:
        pass
        # threading.Thread(
        #     target=download_file,
        #     kwargs={
        #         'url': url,
        #         'file_name': parse_qs(urlparse(url).query)['file'][0],
        #         'number_of_threads': 2
        #     },
        #     daemon=True
        # ).start()
    if idm:
        return HttpResponse(f"<p>{url}</p><p>Self Closing</p><script>setTimeout(window.close, 10000)</script>")
    else:
        return HttpResponseRedirect(url)


# put file in rajib884.pythonanywhere.com
def putfile(filename, fp=None):
    if fp is None:
        fp = filename
    data = {
        "filename": filename,
        "key": "fgksyan-aowdu2ii"
    }
    files = {'file': open(fp, 'rb')}
    response = requests.post("http://rajib884.pythonanywhere.com/putget/put", files=files, data=data)
    print(response.content.decode())
    if "Success" in response.json():
        return True
    else:
        return False


# get file from rajib884.pythonanywhere.com
def getfile(filename):
    data = {
        "filename": filename,
        "key": "fgksyan-aowdu2ii"
    }
    response = requests.post("http://rajib884.pythonanywhere.com/putget/get", data=data)
    return response.content


def search_pp(request):
    if "search" in request.GET:
        sr = anilist.search(request.GET["search"])
        pprint(sr)
        return HttpResponse(
            get_template('MoeList/search_result.html').render({"result": sr, "navbar": variables}, request))
    else:
        return http404("Search Page, 'search not found", request)


def ajax_search(request):
    query = request.POST['search']
    if query == "":
        return http200("", request)
    search_results = process.extract(query, animelist.titles, limit=10)
    keys = []
    for name, similarity in search_results:
        anilist_id = animelist.get_key(name)
        if anilist_id not in keys:
            keys.append(anilist_id)
        if similarity < 55:
            break
        if len(keys) > 5:
            break
    context = {
        "animes": {key: animelist.data[key] for key in keys}
    }
    return HttpResponse(get_template('MoeList/search_ajax.html').render(context, request))


def delete_anime(request):
    if "anime_id" in request.POST:
        if request.POST['anime_id'] in animelist.data:
            del animelist.data[request.POST['anime_id']]
            animelist.save_data()
            return http200(f"Deleted {request.POST['anime_id']} successfully", request)
        else:
            return http404(f"Anime ID {request.POST['anime_id']} was not found in animelist", request)
    else:
        return http404("Anime ID was not given", request)


def settings(request):
    if request.POST and 'filename' in request.POST and 'anilist_name' in request.POST:
        animelist.add_new_title_replace(request.POST['filename'], request.POST['anilist_name'])
    context = {
        "banner": animelist.random_banner,
        "navbar": variables,
        'titleReplace': animelist.title_replace,
        'regexPatterns': animelist.patterns,
        'folders': animelist.root_folders,
        'exceptions': animelist.exceptions,
        'unrecognized': animelist.unrecognized,
        'notVideos': animelist.not_videos,
        'download_links': download_links.all_links,
        'animepaheOffsets': animelist.animepahe_offset,
        'mal': mal.link1,
        'mal_user_data': mal.user_data(),
    }
    return HttpResponse(get_template('MoeList/settings.html').render(context, request))


def settings_handler(request):
    if request.POST and 'values' in request.POST:
        values = json.loads(request.POST['values'])
        # pprint(values)
        return_data = []
        for key, value, index in values:
            if key == "Regex Patterns":
                old_value = value[0][0]
                new_value = value[1][0]
                if old_value is None:
                    animelist.patterns.append(new_value)
                    print(f"Regex Pattern {new_value} was added")
                else:
                    if old_value in animelist.patterns:
                        animelist.patterns[animelist.patterns.index(old_value)] = new_value
                        print(f"Regex Pattern {old_value} was changed to {new_value}")
                    else:
                        print(f"Regex Pattern {old_value} was not found")  # todo
                        return_data.append([index, f"Regex Pattern {old_value} was not found"])  # todo
            elif key == "Folder":
                value[0][1] = value[0][1] == "true"
                value[0][2] = value[0][2] == "true"
                value[1][1] = value[1][1] == "true"
                value[1][2] = value[1][2] == "true"
                old_value = value[0]
                new_value = value[1]
                new_value[0] = path.normpath(new_value[0])
                if not path.exists(new_value[0]):
                    print(f"{new_value[0]} does not exists, so was ignored")
                    return_data.append([index, f"{new_value[0]} does not exists, so it was ignored"])
                else:
                    if old_value[0] is None:
                        animelist.root_folders.append(new_value)
                        print(f"{new_value} was added")
                    else:
                        if old_value in animelist.root_folders:
                            animelist.root_folders[animelist.root_folders.index(old_value)] = new_value
                            print(f"{old_value} was replaced with {new_value}")
                        else:
                            print(f"{old_value} was not found")  # todo
                            return_data.append([index, f"{old_value} was not found"])  # todo
            elif key == "Exception File Name":
                old_key = value[0][0]
                new_key = value[1][0]
                old_value = value[0][1:3]
                new_value = value[1][1:3]
                try:
                    int(new_value[0])
                    int(new_value[1])
                except ValueError:
                    print(f"AniList ID and Ep can be only integer type, you provided {new_value} on {new_key}")
                    return_data.append(
                        [index, f"AniList ID and Ep can be only integer type, you provided {new_value} on {new_key}"])
                else:
                    if old_key is None:
                        animelist.exceptions[new_key] = new_value
                        print(f"{new_key}: {new_value} was added")
                    else:
                        if old_key in animelist.exceptions and animelist.exceptions[old_key] == old_value:
                            del animelist.exceptions[old_key]
                            animelist.exceptions[new_key] = new_value
                            print(f"{old_key}: {old_value} was replaced with {new_key}: {new_value}")
                        else:
                            print(f"{old_key}: {old_value} was not found.")  # todo
                            return_data.append([index, f"{old_key}: {old_value} was not found."])  # todo
            elif key == "Show":
                t = {
                    "Deleted Episodes": "show_deleted_ep",
                    ".deleted": "show_deleted_ep",
                    "Watched Episodes": "show_watched_ep",
                    ".watched": "show_watched_ep",
                    "New Episodes": "show_new_ep",
                    ".new": "show_new_ep",
                    "Downloadable Episodes": "show_downloadable_ep",
                    ".download": "show_downloadable_ep"
                }
                if value[1][0] in t:
                    variables[t[value[1][0]]] = value[1][1] == "true"
                    print(f"{value[1][0]} is now {value[1][1]}")
                else:
                    print(f"{value[1][0]} is not in dict!")
                    return_data.append([index, f"{value[1][0]} was not found."])  # todo
            elif key == "AnimePahe Offsets":
                if value[1][0].isdigit() and value[1][1].isdigit():
                    animelist.animepahe_offset[str(value[1][0])] = int(value[1][1])
                    print(f"Anime with AniList ID {value[1][0]} offset set to {value[1][1]}")
                else:
                    print(f"{value[1]} is not in digit!")
                    return_data.append([index, f"{value[1]} can be only digit"])  # todo
            else:
                print("Key did not match")
                return_data.append([index, "Key did not match"])

        with open(animelist._regex_patterns_file, "w") as f:
            f.write(json.dumps(animelist.patterns, indent=4, sort_keys=True))
        with open(animelist._root_folders_file, "w") as f:
            f.write(json.dumps(animelist.root_folders, indent=4, sort_keys=True))
        with open(animelist._name_exceptions_file, "w") as f:
            f.write(json.dumps(animelist.exceptions, indent=4, sort_keys=True))
        with open(animelist._animepahe_offset_file, "w") as f:
            f.write(json.dumps(animelist.animepahe_offset, indent=4, sort_keys=True))
        with open("options.json", "w") as f:
            f.write(json.dumps(variables, indent=4, sort_keys=True))

        return HttpResponse(json.dumps(return_data, indent=4))
    else:
        pprint(request.POST)
        return HttpResponse("Send key value via POST")
