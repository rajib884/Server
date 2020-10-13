import bz2
import datetime
import gzip
import json
import os
import pickle
# import random
import re
import secrets
import subprocess
import threading
from collections import defaultdict
from json import loads, dumps
from mimetypes import guess_type
from os.path import isdir, join, exists, basename, getsize, dirname
from pprint import pprint
from time import sleep, time
from typing import Union

import PySimpleGUI as sg
import requests
import xmltodict
from PIL import Image
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from slugify import slugify

from MoeList.Backbone.animepahe import update_animepahe

sg.SetGlobalIcon(r"MoeList\static\MoeList\icon.ico")
sg.theme("DarkBlack")
sg.set_options(font="Verdana 12")


# get file from rajib884.pythonanywhere.com
def getfile(filename):
    data = {
        "filename": filename,
        "key": "fgksyan-aowdu2ii"
    }
    try:
        response = requests.post("http://rajib884.pythonanywhere.com/putget/get", data=data)
    except requests.exceptions.ConnectionError:
        return None
    return response.content


def is_int(t):
    try:
        int(t)
        return True
    except ValueError:
        return False


def cwebp(input_image, output_image, option):
    cmd = r"MoeList\Backbone\cwebp.exe " + option + ' ' + input_image + ' -o ' + output_image
    p = subprocess.Popen(cmd, shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    result = {'exit_code': p.returncode, 'stdout': stdout, 'stderr': stderr, 'command': cmd}
    return result


class MAL:
    def __init__(self):
        self.code_verifier = secrets.token_urlsafe(100)[:128]
        self._data_file = r"MoeList\data\MAL_data.json"
        if exists(self._data_file):
            self.data = json.load(open(self._data_file))
        else:
            self.data = {
                'client_id': "CLIENT ID HERE",
                'client_secret': "CLIENT SECRET HERE",
                'refresh_token': "Would be automatically updated",
                'access_token': "Would be automatically updated",
                'token_type': "Would be automatically updated",
            }
            with open(self._data_file, "w") as f:
                f.write(json.dumps(self.data, indent=4, sort_keys=True))
        self.link1 = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={self.data["client_id"]}&code_challenge={self.code_verifier}'
        # self.search("Made in Abyss Movie 3 - Fukaki Tamashii no Reimei")
        # pprint(self.get_anime_details(38935))
        # print(self.get_score(21))
        # print(self.get_score(38935))
        # print(self.get_score(389350))
        # pprint(self.currnet_user_anime_list())
        # self.update_user_list(41006)
        # pprint(self.seasonal_anime())
        # pprint(self.user_data())
        # exit()

    def save_response(self, response):
        try:
            t = response.json()
        except:
            print(response.content.decode())
            return False
        else:
            if 'access_token' in t:
                self.data['access_token'] = t['access_token']
                self.data['refresh_token'] = t['refresh_token']
                self.data['token_type'] = t['token_type']
                with open(self._data_file, "w") as f:
                    f.write(json.dumps(self._data_file, indent=4, sort_keys=True))
                return True

    def process_code(self, code, redirect_uri):
        l = 'https://myanimelist.net/v1/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.data['client_id'],
            'client_secret': self.data['client_secret'],
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': self.code_verifier,
            'redirect_uri': redirect_uri,
        }
        response = requests.post(l, data=data, headers=headers)
        return self.save_response(response)

    def refresh_access_token(self):
        print("Refreshing MyAnimeList Access Token")
        l = 'https://myanimelist.net/v1/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.data['client_id'],
            'client_secret': self.data['client_secret'],
            'grant_type': 'refresh_token',
            'refresh_token': self.data['refresh_token'],
        }
        response = requests.post(l, data=data, headers=headers)
        return self.save_response(response)

    def get(self, link, params=None, headers=None, ):
        if headers is None:
            headers = {'Authorization': f'{self.data["token_type"]} {self.data["access_token"]}', }
        try:
            response = requests.get(link, headers=headers, params=params)
        except requests.exceptions.ConnectionError:
            return None
        if response.status_code == 401:
            if self.refresh_access_token():
                response = requests.get(link, headers=headers, params=params)
                if response.status_code == 401:
                    print("Refreshing Access token did not help, Log in again")
                    return None
            else:
                print("Could not refresh Access token, Log in again")
                return None
        elif response.status_code == 400:
            print("Invalid Parameters")
        elif response.status_code == 403:
            print("Invalid Token??")
        return response.json()

    def put(self, link, data=None, params=None, headers=None, ):
        if headers is None:
            headers = {'Authorization': f'{self.data["token_type"]} {self.data["access_token"]}', }
        try:
            response = requests.put(link, data=data, headers=headers, params=params)
        except requests.exceptions.ConnectionError:
            return None
        if response.status_code == 401:
            self.refresh_access_token()
            response = requests.put(link, data=data, headers=headers, params=params)
            if response.status_code == 401:
                print("Refreshing Access token did not help, Log in again")
                return None
        elif response.status_code == 400:
            print("Invalid Parameters")
        return response.json()

    def user_data(self):
        params = {'fields': 'anime_statistics'}
        return self.get('https://api.myanimelist.net/v2/users/@me', params)

    def currnet_user_anime_list(self, user_name='@me', status=None, sort='anime_title', limit=10, offset=0):
        if status not in ('watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch', None):
            print(f"Error: {status} is not valid status")
            return None
        if sort not in ('list_score', 'list_updated_at', 'anime_title', 'anime_start_date', 'anime_id'):
            print(f"Error: {status} is not valid status")
            return None
        params = {
            'fields': 'list_status',
            'limit': min(limit, 1000),
            'offset': offset,
        }
        response = self.get(f'https://api.myanimelist.net/v2/users/{user_name}/animelist', params)
        if limit > 1000 and 'next' in response['paging']:
            t = self.currnet_user_anime_list(user_name, status, sort, limit - 1000, offset + 1000)
            response['data'].extend(t['data'])
            response['paging']['next'] = t['paging']['next']
        return response

    def search(self, q):
        params = {
            'q': q,
            'limit': '10',
            'fields': 'id, title, alternative_titles'
        }
        response = self.get('https://api.myanimelist.net/v2/anime', params)
        pprint(response)

    def get_anime_details(self, anime_id):
        params = {
            'fields': ','.join(
                ['title', 'main_picture', 'end_date', 'synopsis', 'mean', 'rank', 'popularity', 'num_list_users',
                 'num_scoring_users', 'nsfw', 'status', 'num_episodes', 'source', 'average_episode_duration', 'rating',
                 'studios', 'statistics',
                 'id', 'alternative_titles', 'background', 'broadcast', 'created_at', 'genres',
                 'media_type', 'my_list_status', 'pictures', 'recommendations', 'related_anime', 'related_manga',
                 'start_date', 'start_season', 'updated_at'
                 ]),
        }
        return self.get(f"https://api.myanimelist.net/v2/anime/{anime_id}", params)

    def get_anime_info(self, anime_id):
        params = {
            'fields': ','.join(
                ['end_date', 'mean', 'rank', 'popularity', 'num_scoring_users', 'status', 'num_episodes', 'source',
                 'average_episode_duration', 'rating', 'studios', 'num_list_users', 'my_list_status', ]),
        }
        t = self.get(f"https://api.myanimelist.net/v2/anime/{anime_id}", params) or {}
        t['status'] = t.get('status', 'Unavailable').replace('_', ' ')
        t['rating'] = t.get('rating', 'Unavailable').replace('_', ' ')
        t['average_episode_duration'] = "%d:%02d" % divmod(t.get('average_episode_duration', 0), 60)
        pprint(t)
        return t

    def get_score(self, anime_id):
        params = {
            'fields': 'num_scoring_users,mean,my_list_status'
        }
        response = self.get(f"https://api.myanimelist.net/v2/anime/{anime_id}", params)
        if response is None:
            return None, None
        t = response.get('my_list_status', {}).get('score', None)
        return response.get('mean', None), None if t == 0 else t

    def update_user_list(
            self,
            anime_id: Union[str, int],
            status: str = 'plan_to_watch',
            num_watched_episodes: int = 0,
            score: Union[int, None] = None,
            is_rewatching: Union[bool, None] = None
    ):
        if not is_int(anime_id):
            print(f"Error: {anime_id} is not valid anime id")
            return None
        if not is_int(num_watched_episodes):
            print(f"Error: {num_watched_episodes} must be int (num_watched_episodes)")
            return None
        if status not in ('watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch'):
            print(f"Error: {status} is not valid status")
            return None
        data = {
            'status': status,
            'score': score,
            'num_watched_episodes': num_watched_episodes
        }
        if score is not None:
            data['score'] = score
        if is_rewatching is not None:
            data['is_rewatching'] = is_rewatching

        return self.put(f"https://api.myanimelist.net/v2/anime/{anime_id}/my_list_status", data)

    def seasonal_anime(self, year: Union[int, str] = '2020', season: str = 'fall', limit: int = 25, offset: int = 0):
        if not is_int(year):
            print(f"Error: {year} is not valid year")
            return None
        if season not in ('winter', 'spring', 'summer', 'fall'):
            print(f"Error: {season} is not valid season")
            return None
        params = {
            'sort': 'num_list_users',  # or 'anime_score'
            'limit': min(limit, 500),
            'offset': offset,
            'fields': 'num_list_users, mean, start_season'
        }
        response = self.get(f"https://api.myanimelist.net/v2/anime/season/{year}/{season}", params)
        if limit > 500 and 'next' in response['paging']:
            t = self.seasonal_anime(year, season, limit - 500, offset + 500)
            response['data'].extend(t['data'])
            response['paging']['next'] = t['paging']['next']
        return response


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


class AniList:
    url = 'https://graphql.anilist.co'

    def mal_to_anilist(self, mal: int):
        def simplify_json(result):
            return {
                'id': result['id'],
                'title': result['title']['romaji'],
                'titleEn': result['title']['english']
            }

        query = '''
            query ($idMal: Int) { 
                Media (idMal: $idMal, type: ANIME) { 
                    id
                    title {
                        romaji
                        english
                    }
                }
            }
            '''
        variables = {'idMal': mal}
        print("Searching AniList for Mal id {}".format(mal))
        anilist_json = requests.post(self.url, json={'query': query, 'variables': variables}).json()

        if "errors" in anilist_json:
            raise KeyError
        else:
            return simplify_json(anilist_json["data"]["Media"])


class FileList:
    def __init__(self):
        self.filelist = []
        self._old_filelist = []
        self.data = {}
        self.title_replace = {}
        self.anilist_url = 'https://graphql.anilist.co'
        self.animepahe_api_url = 'https://animepahe.com/api'
        self.pc_drive_letters = r"C:\\|D:\\|E:\\|F:\\|G:\\"
        self._changed = False
        if re.match(self.pc_drive_letters, os.getcwd()) is None:
            raise Exception
        self._running_on_pc = True
        self._encryption_key_file = r"MoeList\data\encryption_key.txt"
        self._encrypted_data_file = r"MoeList\data\AnimeList Data.enc"
        self._json_data_file = r"MoeList\data\AnimeList Data.json"
        self._root_folders_file = r"MoeList\data\folders.json"
        self._title_replace_file = r"MoeList\data\title replace.json"
        self._name_exceptions_file = r"MoeList\data\exceptions.json"
        self._regex_patterns_file = r"MoeList\data\regex_patterns.json"
        self._animepahe_offset_file = r"MoeList\data\animepahe_offset.json"
        self._animepahe_header_file = r"MoeList\data\animepahe_header.json"
        self._animepahe_data_file = r"MoeList\data\animepahe_data.bz2"
        # self._load_data_from_encrypt()
        self._load_data_from_files()

        self.patterns = json.load(open(self._regex_patterns_file))
        self.exceptions = json.load(open(self._name_exceptions_file))
        self.root_folders = json.load(open(self._root_folders_file))
        self.animepahe_offset = json.load(open(self._animepahe_offset_file))
        self.animepahe_header = json.load(open(self._animepahe_header_file))
        try:
            self.check_animepahe_header()
        except requests.exceptions.ConnectionError:
            print("Connection Error")

        self.unrecognized = []
        self.not_videos = []
        self.to_print = []

        self.check_interval = 30
        self._thread_running = False
        threading.Thread(target=self._recheck, daemon=True).start()

    # extract name and ep from filename
    def _extract(self, file_name: str):
        if (guess_type(file_name)[0] or "").split('/')[0] == "video":
            for regex in self.patterns:
                match = re.match(regex, basename(file_name))
                if match is not None:
                    temp = match.groupdict()
                    if " " not in temp['name']:
                        if "_" in temp['name']:
                            temp['name'] = temp['name'].replace("_", " ")
                        elif "." in temp['name']:
                            temp['name'] = temp['name'].replace(".", " ")

                    temp['name'] = temp['name'].strip()
                    if temp['ep'] is not None:
                        try:
                            # noinspection PyTypeChecker
                            temp['eps'] = [str(int(temp['ep']))]
                        except TypeError:
                            print(temp['ep'])
                            print(file_name)
                            print(match)
                            print(temp)
                            raise Exception
                        del temp['ep']
                    else:
                        # noinspection PyTypeChecker
                        temp['eps'] = [str(ep) for ep in range(
                            int(temp['epRange'].split("-")[0]),
                            int(temp['epRange'].split("-")[1]) + 1
                        )]
                        del temp['epRange']
                    # print(temp['name'])
                    if temp['name'] in self.title_replace:
                        temp['name'] = self.title_replace[temp['name']]
                    return temp
            if basename(file_name) in self.exceptions:
                if self.exceptions[basename(file_name)][0] not in self.data:
                    self.update_anilist_data(self.exceptions[basename(file_name)][0])
                return {
                    'name': self.data[self.exceptions[basename(file_name)][0]]['title'],
                    'eps': [self.exceptions[basename(file_name)][1]]
                }
            elif file_name not in self.unrecognized:
                self.unrecognized.append(file_name)
                print("Unrecognized: {}".format(file_name))
        elif file_name not in self.not_videos:
            self.not_videos.append(file_name)
            print("Not Video: {}".format(file_name))
        return None

    # todo: Currently Airing List

    def watched(self, anilist_id: str, ep: str) -> bool:
        if ep in self.data[anilist_id]["episode_list"]:
            self.data[anilist_id]["episode_list"][ep]["watched"] = True
        else:
            self.data[anilist_id]["episode_list"][ep] = {
                "path": None,
                "watched": True
            }
        self._changed = True
        return True

    @property
    def keys_of_deleted(self) -> list:
        return [anilist_id for anilist_id in self.data if self.is_deleted(anilist_id)]

    @property
    def keys_of_not_deleted(self) -> list:
        return [anilist_id for anilist_id in self.data if not self.is_deleted(anilist_id)]

    @property
    def keys_of_watched(self) -> list:
        return [anilist_id for anilist_id in self.data if self.is_all_downloaded_ep_watched(anilist_id)]

    @property
    def keys_of_not_watched(self) -> list:
        return [anilist_id for anilist_id in self.data if not self.is_all_downloaded_ep_watched(anilist_id)]

    def keys_by_status(self, status: str) -> list:
        return [anilist_id for anilist_id, anime in self.data.items() if
                (anime["status"] or "NOT_YET_RELEASED").lower() == status.lower()]

    def keys_by_type(self, typ: str) -> list:
        return [anilist_id for anilist_id, anime in self.data.items() if
                (anime["type"] or "None").lower() == typ.lower()]

    def keys_by_genre(self, genre: str) -> list:
        return [anilist_id for anilist_id, anime in self.data.items() if genre in anime["genres"]]

    def keys_by_year(self, year: Union[str, int]) -> list:
        x = datetime.datetime.now()
        return [anilist_id for anilist_id, anime in self.data.items() if int(anime["year"] or x.year) == int(year)]

    def keys_by_season(self, season: str) -> list:
        return [anilist_id for anilist_id, anime in self.data.items() if
                (anime["season"] or 'None').lower() == season.lower()]

    @property
    def available_genres(self) -> list:
        genres = []
        for anilist_id, anime in self.data.items():
            for genre in anime['genres']:
                if genre not in genres:
                    genres.append(genre)
        return ["All"] + sorted(genres)

    @property
    def available_seasons(self) -> list:
        seasons = []
        for anilist_id, anime in self.data.items():
            if anime["season"] is not None and anime["season"].title() not in seasons:
                seasons.append(anime["season"].title())
        return ["All"] + sorted(seasons) + ['None']

    @property
    def available_statuses(self) -> list:
        statuses = []
        for anilist_id, anime in self.data.items():
            if anime["status"] is not None and anime["status"].title() not in statuses:
                statuses.append(anime["status"].title())
        return ["All"] + sorted(statuses)

    @property
    def available_years(self) -> list:
        years = []
        for anilist_id, anime in self.data.items():
            if anime["year"] is not None and str(anime["year"]) not in years:
                years.append(str(anime["year"]))
        return ["All"] + sorted(years, reverse=True)

    @property
    def available_types(self) -> list:
        types = []
        for anilist_id, anime in self.data.items():
            if str(anime["type"] or 'None') not in types:
                types.append(str(anime["type"] or 'None'))
        return ["All"] + sorted(types, reverse=True)

    @property
    def titles(self) -> list:
        titles = []
        for key, anime in self.data.items():
            if anime["title"] not in titles:
                titles.append(anime["title"])
            if anime.get("titleEn") is not None and anime["titleEn"] not in titles:
                titles.append(anime["titleEn"])
        return titles

    def watched_all(self, anilist_id: str) -> bool:
        if anilist_id in self.data:
            anime = self.data[anilist_id]
            if anime["nextEp"] is not None:
                end = int(anime["nextEp"]["episode"])
            else:
                end = int(anime["episodes"]) + 1
            for n in range(1, end):
                self.watched(anilist_id, str(n))
            self.save_data()
            return True
        else:
            return False

    # Mal to anilist id
    def mal_to_anilist(self, mal: int) -> int:
        query = '''
            query ($idMal: Int) { 
                Media (idMal: $idMal, type: ANIME) { 
                    id
                }
            }
            '''
        variables = {'idMal': mal}
        print(f"Searching AniList id with mal {mal}.. ", end="")
        anilist_json = requests.post(self.anilist_url, json={'query': query, 'variables': variables}).json()

        if "errors" in anilist_json:
            raise KeyError
        else:
            print("Found {}".format(anilist_json["data"]["Media"]["id"]))
            return anilist_json["data"]["Media"]["id"]

    # import mal
    def import_mal(self, f):
        self.to_print.append("Importing Myanimelist")
        print("PP??")
        try:
            data = xmltodict.parse(gzip.decompress(f.read()).decode())
        except Exception as e:
            print(e)
            self.to_print.append(str(e))
        else:
            for anime in data["myanimelist"]["anime"]:
                key = self.get_key_by_mal(int(anime['series_animedb_id']))
                if key is None:
                    print(f"Importing {anime['series_title']}")
                    self.to_print.append(f"Importing {anime['series_title']}")
                    try:
                        key = self.mal_to_anilist(int(anime['series_animedb_id']))
                        self.to_print.append(f"\tMAL id {anime['series_animedb_id']} is AniList id {key}")
                    except KeyError:
                        print("KeyError")
                        self.to_print.append("KeyError")
                        continue
                    self.update_anilist_data(key)
                    for ep in range(1, int(anime['my_watched_episodes']) + 1):
                        self.watched(str(key), str(ep))
                    self.save_data()
                    self.to_print.append(f"\tDatabase updated")
                    sleep(3)
                else:
                    if int(self.get_max_watched_ep(key)) < int(anime['my_watched_episodes']):
                        print(f"{anime['series_title']} Needs Update")
                        self.to_print.append(f"Updating {anime['series_title']}")
                        for ep in range(1, int(anime['my_watched_episodes']) + 1):
                            self.watched(key, str(ep))
                        self._changed = True
                        self.to_print.append(f"\tDatabase updated")
        self.to_print.append(f"===Importing Finished===")

    # Anilist search by name
    def anilist_search(self, name: str, only_airing: bool = False, max_in_1_page: int = 10) -> list:
        def simplify_search_json(search_result):
            temp = []
            for result in search_result:
                temp.append({
                    'id': result['id'],
                    'mal': result['idMal'],
                    'thumb': result['coverImage']['medium'],
                    'episodes': result['episodes'],
                    'format': result['format'],
                    'season': result['season'],
                    'year': result['startDate']['year'],
                    'status': result['status'],
                    'title': result['title']['romaji'],
                    'titleEn': result['title']['english']
                })
            return temp

        query = '''
            query ($id: Int, $page: Int, $perPage: Int, $search: String, $status: MediaStatus) {
                Page (page: $page, perPage: $perPage) {
                    media (id: $id, search: $search, type: ANIME, status: $status) {
                        id
                        idMal
                        format
                        season
                        status
                        episodes
                        startDate {
                            year
                        }
                        title {
                            romaji
                            english
                        }
                        coverImage{
                            medium
                        }
                    }
                }
            }
            '''

        variables = {
            'search': name,
            'page': 1,
            'perPage': max_in_1_page
        }

        if only_airing:
            variables['status'] = 'RELEASING'
        print("Searching AniList for {}".format(name))
        anilist_json = requests.post(self.anilist_url, json={'query': query, 'variables': variables}).json()

        if "errors" in anilist_json:
            raise KeyError
        else:
            return simplify_search_json(anilist_json["data"]["Page"]["media"])

    # Anilist get info by id
    def anilist_get_info(self, anilist_id: int) -> dict:
        def simplify_edges(nodes):
            y = []
            for node in nodes:
                if node['node']['format'] not in ['MANGA', 'MUSIC', 'NOVEL', 'ONE_SHOT']:
                    y.append({
                        'id': node['node']['id'],
                        'type': node['node']['format'],
                        'title': node['node']['title']['romaji'],
                        'season': node['node']['season'],
                        'episodes': node['node']['episodes'],
                        'status': node['node']['status'],
                        'banner': node['node']['bannerImage'],
                        'cover': node['node']['coverImage']['extraLarge'],
                        'year': node['node']['startDate']['year'],
                        'relationType': node['relationType']
                    })
            return y

        def simplify_anilist_json(anilist_info_json):
            temp = {
                'banner': anilist_info_json['bannerImage'],
                'cover': anilist_info_json['coverImage']['extraLarge'],
                'description': anilist_info_json['description'],
                'episodes': anilist_info_json['episodes'],
                'type': anilist_info_json['format'],
                'genres': anilist_info_json['genres'],
                'mal': anilist_info_json['idMal'],
                'nextEp': anilist_info_json['nextAiringEpisode'],
                'relations': simplify_edges(anilist_info_json['relations']['edges']),
                'season': anilist_info_json['season'],
                'year': anilist_info_json['startDate']['year'],
                'status': anilist_info_json['status'],
                'title': anilist_info_json['title']['romaji'],
                'titleEn': anilist_info_json['title']['english'],
                'titleJp': anilist_info_json['title']['native'],
                'episode_list': {}
            }
            return temp

        query = '''
            query ($id: Int) {
              Media (id: $id, type: ANIME) {
                idMal
                episodes
                format
                season
                startDate {
                    year
                }
                status
                genres
                description(asHtml: false)
                bannerImage
                nextAiringEpisode {
                    airingAt
                    episode
                }
                relations {
                    edges {
                        node {
                            id
                            title{
                                romaji
                            }
                            episodes
                            format
                            status
                            season
                            bannerImage
                            coverImage{
                                extraLarge
                            }
                            startDate {
                                year
                            }
                        }
                        relationType
                    }
                }
                coverImage{
                    extraLarge
                }
                title {
                  romaji
                  english
                  native
                }
              }
            }
            '''

        variables = {'id': anilist_id}

        anilist_json = requests.post(self.anilist_url, json={'query': query, 'variables': variables}).json()

        if "errors" in anilist_json:
            pprint(anilist_json)
            raise KeyError
        else:
            return simplify_anilist_json(anilist_json["data"]["Media"])

    # Update data in anilist id
    def update_anilist_data(self, anilist_id: Union[str, int]) -> bool:
        keep = ["episode_list", "animepahe_id", "downloadableEp", "slug"]
        if str(anilist_id) not in self.data:
            self.data[str(anilist_id)] = {}
        anime = self.data[str(anilist_id)]
        try:
            latest_info = self.anilist_get_info(int(anilist_id))
        except requests.exceptions.ConnectionError:
            print("Connection Error, Failed to update {} data".format(anime['title']))
            return False
        for key, value in latest_info.items():
            if key not in keep:
                if key in ("cover", "banner"):
                    if anime.get(key) != value:
                        self.remove_image(anime.get("slug", slugify(latest_info['title'])), key)
                anime[key] = value

        if anime.get("animepahe_id") is None:
            anime["animepahe_id"] = self.mal_to_animepahe(anime["mal"])
        if anime.get("slug") is None:
            anime["slug"] = slugify(anime["title"])
        if anime.get("episode_list") is None:
            anime["episode_list"] = {}
        self._changed = True
        return True

    def update_anilist(self):
        for anilist_id, anime in self.data.items():
            if anime["status"] in ("RELEASING", "NOT_YET_RELEASED", None):
                if anime['nextEp'] is None or anime['nextEp']['airingAt'] - time() < 0:
                    if self.update_anilist_data(anilist_id):
                        print("Updated {} data".format(anime['title']))
                        if anime['nextEp'] is None and anime["status"] in ("RELEASING", "NOT_YET_RELEASED", None):
                            print(
                                "Next ep is set to air at unknown time. Setting fake data so it is checked 18 hr "
                                "later again")
                            anime['nextEp'] = {
                                "airingAt": int(time()) + 64800,
                                "episode": str(int(self.get_max_ep(anilist_id)) + 1)
                            }

    # Adds new title in the list
    def add_new_title_replace(self, file_name: str, anilist_name: str):
        if file_name != anilist_name:
            self.title_replace[file_name] = anilist_name
            for key in list(self.title_replace.keys()):
                if self.title_replace[key] == file_name:
                    self.title_replace[key] = anilist_name
                if self.title_replace[key] == key:
                    del self.title_replace[key]
        self.save_data()

    # Get key from anime name
    def get_key(self, name: str) -> Union[str, None]:
        for key, anime in self.data.items():
            if name == anime["title"] or name == anime["titleEn"]:
                return key
        return None

    def get_key_by_mal(self, mal: int) -> Union[str, None]:
        if type(mal) is not int:
            raise KeyError('MyAnimeList id needs to be int')
        for key, anime in self.data.items():
            if mal == anime["mal"]:
                return key
        return None

    # noinspection PyUnusedLocal
    def get_keys(
            self,
            deleted: bool = None,
            watched: bool = None,
            genre: str = None,
            season: str = None,
            status: str = None,
            typ: str = None,
            year0: int = None,
            year: str = None,
            sorted_by_year: bool = False,
            **kwargs):
        keys = set(list(self.data.keys()))

        if deleted is True:
            keys = keys.intersection(set(self.keys_of_deleted))
        elif deleted is False:
            keys = keys.intersection(set(self.keys_of_not_deleted))

        if watched is True:
            keys = keys.intersection(set(self.keys_of_watched))
        elif watched is False:
            keys = keys.intersection(set(self.keys_of_not_watched))

        if genre is not None:
            keys = keys.intersection(set(self.keys_by_genre(genre)))

        if year0 is not None:
            keys = keys.intersection(set(self.keys_by_year(year0)))
        elif year is not None:
            keys = keys.intersection(set(self.keys_by_year(year)))

        if season is not None:
            keys = keys.intersection(set(self.keys_by_season(season)))

        if status is not None:
            keys = keys.intersection(set(self.keys_by_status(status)))

        if typ is not None:
            keys = keys.intersection(set(self.keys_by_type(typ)))

        if sorted_by_year:
            return self.get_ids_sorted_by_year(keys)
        else:
            return list(keys)

    # Safely replace path in data
    def safe_replace(self, key: str, name: str, ep: str, file: str):
        current_file = self.data[key]["episode_list"][ep]
        if current_file["path"] != file:
            if current_file["path"] is not None and exists(current_file["path"]):
                if exists(file):
                    print("Duplicate found on {} ep {}\nCurrent file: {}\nNew file:{}".format(
                        name, ep, current_file["path"], file
                    ))
                    print("When used extract, they yield:\n{}\n{}".format(
                        self._extract(current_file["path"]), self._extract(file)))
                    print("Nothing done")
                    # current_file["path"] = file
                else:
                    print(f"Passed file: {file}")
                    print("Previous file: {}".format(current_file["path"]))
                    print(f"As Passed file does not exists but previous file exists.. ignoring")
            else:
                print("Updated {} ep {}, path from {} to {}".format(name, ep, current_file["path"], file))
                current_file["path"] = file

    # Processes added files
    def process_added(self, added_files: list):
        for file in added_files:
            self._changed = True
            temp = self._extract(file)
            if temp is not None:
                name = temp['name']
                eps = temp['eps']
                key = self.get_key(name)
                if key is None:
                    print("New Anime: {}".format(name))
                    search_result = self.anilist_search(name, max_in_1_page=8)
                    for value in search_result:
                        if name == value["title"] or name == value["titleEn"]:
                            key = str(value["id"])
                            self.add_new_title_replace(name, value["title"])
                            print("\tAuto Match found")
                            break
                    if key is None:
                        key = self.anilist_search_dialog(name, file, search_result)
                        if key is not None:
                            for value in search_result:
                                if key == value['id']:
                                    self.add_new_title_replace(name, value["title"])
                                    key = str(key)
                                    break

                    if key is not None:
                        # key found
                        if key in self.data:
                            # Not new anime but file name slightly changed
                            for ep in eps:
                                if ep not in self.data[key]["episode_list"]:
                                    self.data[key]["episode_list"][ep] = {
                                        "path": file,
                                        "watched": False
                                    }
                                else:
                                    self.safe_replace(key, name, ep, file)
                        else:
                            # Totally new anime
                            self.update_anilist_data(key)
                            # self.data[key] = self.anilist_get_info(int(key))
                            # self.data[key]["animepahe_id"] = self.mal_to_animepahe(self.data[key]["mal"])
                            # self.data[key]["slug"] = slugify(self.data[key]["title"])
                            for ep in eps:
                                self.data[key]["episode_list"][ep] = {
                                    "path": file,
                                    "watched": False
                                }
                    else:
                        # New anime, but no search match!
                        raise Exception("New anime, but no search match!")
                else:
                    # add new ep to data!
                    for ep in eps:
                        if ep not in self.data[key]["episode_list"]:
                            print("Added ep {} in {}".format(ep, name))
                            self.data[key]["episode_list"][ep] = {
                                "path": file,
                                "watched": False
                            }
                        else:
                            self.safe_replace(str(key), name, ep, file)
            else:
                pass
                # print("Unrecognized file: {}".format(file))
        if self._changed:
            self.save_data()

    # Processes removed files
    def process_removed(self, removed_files: list):
        for file in removed_files:
            self._changed = True
            temp = self._extract(file)
            if temp is None:
                print("File {} is removed, but is unrecognized".format(file))
                if file in self.unrecognized:
                    self.unrecognized.remove(file)
            else:
                name = temp["name"]
                eps = temp["eps"]
                key = self.get_key(name)
                if key is None:
                    raise Exception("What the hell! {} should get me a key!".format(name))
                else:
                    for ep in eps:
                        if ep in self.data[key]["episode_list"]:
                            if self.data[key]["episode_list"][ep]["path"] == file:
                                print("Removed {} ep {}, path from {} to {}".format(name, ep,
                                                                                    self.data[key]["episode_list"][ep][
                                                                                        "path"], None))
                                self.data[key]["episode_list"][ep]["path"] = None
                            else:
                                if self.data[key]["episode_list"][ep]["path"] is not None and exists(
                                        self.data[key]["episode_list"][ep]["path"]):
                                    print("Possible duplicate removed?")
                                    print("{} ep {}".format(name, ep))
                                    print("Current file {}".format(self.data[key]["episode_list"][ep]["path"]))
                                    print("Removed file {}".format(file))
                                else:
                                    print("Removed if {} ep {}".format(name, ep))
                                    print("Removed file {}".format(self.data[key]["episode_list"][ep]["path"]))
                                    self.data[key]["episode_list"][ep]["path"] = None
                        else:
                            raise Exception("{} should have ep {} in it! What the hell!".format(name, ep))
        if self._changed:
            self.save_data()

    # Checks if path exists in data
    def check_data(self):
        for key in self.data:
            for ep in self.data[key]["episode_list"]:
                if self.data[key]["episode_list"][ep]["path"] is not None and not exists(
                        self.data[key]["episode_list"][ep]["path"]):
                    if self._running_on_pc:
                        if re.match(self.pc_drive_letters, self.data[key]["episode_list"][ep]["path"]) is not None:
                            print("Deleted file? Removed {} ep {}, path from {} to {}".format(
                                self.data[key]["title"],
                                ep,
                                self.data[key]["episode_list"][ep]["path"],
                                None
                            ))
                            self.data[key]["episode_list"][ep]["path"] = None
                            self._changed = True
                        else:
                            pass
                            # print("File on another device? {}".format(self.data[key]["episode_list"][ep]["path"]))
                    else:
                        pass
                        # todo: fix this
                        # if "/storage/" == self.data[key]["episode_list"][ep]["path"][:9]:
                        #     print("Deleted file? Removed {} ep {}, path from {} to {}".format(
                        #         self.data[key]["title"],
                        #         ep,
                        #         self.data[key]["episode_list"][ep]["path"],
                        #         None
                        #     ))
                        #     self.data[key]["episode_list"][ep]["path"] = None
                        #     self._changed = True
                        # else:
                        #     pass
                        # print("File on another device? {}".format(self.data[key]["episode_list"][ep]["path"]))
        if self._changed:
            self.save_data()

    def check_for_misc(self):
        for key in self.data:
            # Check for slug
            if "slug" not in self.data[key]:
                self.data[key]["slug"] = slugify(self.data[key]["title"])
                self._changed = True

            # Check for banner, cover exists
            self.download_image(self.data[key]["slug"], self.data[key]["cover"], "cover")
            self.download_image(self.data[key]["slug"], self.data[key]["banner"], "banner")
            self.get_small_cover(key)

            for relation in self.data[key]["relations"]:
                self.download_image(slugify(relation["title"]), relation["cover"], "cover")
                self.download_image(slugify(relation["title"]), relation["banner"], "banner")

            # Check for animepahe id/data
            if "animepahe_id" not in self.data[key]:
                # animepahe_id = self.search_animepahe_id(self.data[key]["title"])
                self.data[key]["animepahe_id"] = self.mal_to_animepahe(self.data[key]["mal"])
                self._changed = True
        if self._changed:
            self.save_data()

    def check_for_thumbnail(self):
        cwd = os.getcwd()
        generated = False
        for key in self.data:
            for ep, ep_details in self.data[key]["episode_list"].items():
                if ep_details["path"] is not None and exists(ep_details["path"]):
                    if not exists(
                            r"MoeList\static\MoeList\thumbnails\{} ep {}.jpeg".format(
                                self.data[key]['slug'], ep)):
                        generated = True
                        temp_dir = join(cwd, r"MoeList\static\MoeList\thumbnails\temp")
                        if not exists(temp_dir):
                            os.mkdir(temp_dir)
                        if len(os.listdir(temp_dir)) > 0:
                            raise Exception("Temp Dir is not empty. Temp dir: {}".format(temp_dir))
                        cmd = r'"{}" -ss 10 -i "{}" -vf "select=gt(scene\,0.5)" -frames:v 8 -vsync vfr -vf ' \
                              r'fps=fps=1/50 "{}"'.format(
                            join(cwd, r"MoeList\Backbone\ffmpeg.exe"),
                            ep_details["path"],
                            r"{}\%01d.jpeg".format(temp_dir)
                        )
                        subprocess.call(cmd)
                        max_size = 0
                        file_path = None
                        for file in os.listdir(temp_dir):
                            if os.path.getsize(join(temp_dir, file)) > max_size:
                                file_path = join(temp_dir, file)
                                max_size = os.path.getsize(join(temp_dir, file))
                        os.rename(
                            file_path,
                            r"MoeList\static\MoeList\thumbnails\{} ep {}.jpeg".format(
                                self.data[key]['slug'], ep))
                        for file in os.listdir(temp_dir):
                            os.remove(join(temp_dir, file))
                        print(f"Created {self.data[key]['title']} ep {ep} thumbnail")
        if generated:
            print("Thumbnail Generation Finished")

    def check_watched_part(self):
        for anilist_id, anime in self.data.items():
            for ep_no, ep in anime["episode_list"].items():
                if ep["watched"] is False:
                    if "watchedPart" in ep:
                        if len(ep["watchedPart"]) > 80:
                            self.watched(anilist_id, ep_no)
                            print(f"Watched {anime['title']} ep {ep_no} more than 80%")

    def check_animepahe_header(self):
        print("Checking Animepahe header..", end="")
        response = requests.get("https://animepahe.com", headers=self.animepahe_header)
        if response.status_code != 200:
            print("Failed")
            # browser = webdriver.Firefox(executable_path=r"MoeList\Backbone\geckodriver.exe", timeout=300)
            options = webdriver.ChromeOptions()
            options.add_argument(r"user-data-dir={}".format(join(os.getcwd(), r"MoeList\Backbone\chrome_data")))
            browser = webdriver.Chrome(
                executable_path=r"MoeList\Backbone\chromedriver.exe",
                chrome_options=options
            )
            browser.get("https://animepahe.com")
            cf_clearance = None
            WebDriverWait(browser, 3000).until(EC.title_contains("animepahe"))
            # while cf_clearance is None:
            sleep(1)
            p = browser.get_cookies()
            for cookie in p:
                if cookie['name'] == 'cf_clearance':
                    cf_clearance = cookie['value']
                    break
            self.animepahe_header = {
                "User-Agent": browser.execute_script("return navigator.userAgent;"),
                "cookie": "cf_clearance={}".format(cf_clearance or "null")
            }
            browser.close()
            browser.quit()
            json.dump(self.animepahe_header, open(self._animepahe_header_file, "w"), indent=4)
            print(f"cf_clearance: {cf_clearance}")
        else:
            print("OK")

    def move_files(self):
        if not self._running_on_pc:
            return

        move_able = tuple(x[0] for x in self.root_folders if x[2] is True)
        for anilist_id, anime in self.data.items():
            for ep_no, ep in anime["episode_list"].items():
                if ep["path"] is not None:
                    if ":" == ep["path"][1]:
                        if r"\Anime" != ep["path"][2:8] and ep["path"].startswith(move_able):
                            src = ep["path"]
                            current_drive = ep["path"][0]
                            if exists(src):
                                folder_path = r"{}:\Anime\{}".format(current_drive, anime["slug"])
                                os.makedirs(folder_path, exist_ok=True)
                                dst = join(folder_path, basename(src))
                                os.rename(src, dst)
                                ep["path"] = dst
                                self._old_filelist.append(dst)
                                self._old_filelist.pop(self._old_filelist.index(src))
                                self._changed = True
                                print(f"Moved file {src} to {dst}")
        t = ["C", "D", "E", "F", "G"]
        for drive_letter in t:
            checking = r"{}:\Anime".format(drive_letter)
            if exists(checking):
                for folder in os.listdir(checking):
                    if len(os.listdir(join(checking, folder))) == 0:
                        os.rmdir(join(checking, folder))
                        print("Removed Empty dir {}".format(join(checking, folder)))

    # Checks for file changes
    def recheck(self):
        self.filelist = []
        # try:
        #     self.filelist = loads(bz2.decompress(getfile("files.json.bz2")).decode())
        # except json.decoder.JSONDecodeError:
        #     self.filelist = []

        for root_folder, include_subfolder, move_from_here in self.root_folders:
            # if (re.match(self.pc_drive_letters, root_folder) is not None and self.running_on_pc) or (
            #         re.match(self.pc_drive_letters, root_folder) is None and not self.running_on_pc):
            self._scandir(root_folder, include_subfolder)
        self.process_removed([file for file in self._old_filelist if file not in self.filelist])
        self.process_added([file for file in self.filelist if file not in self._old_filelist])
        self._old_filelist = self.filelist
        self.check_data()
        self.move_files()
        self.update_anilist()
        self.check_for_misc()
        self.check_watched_part()
        if self._changed:
            self.save_data()
        self.check_for_thumbnail()

    # called self.recheck forever
    def _recheck(self):
        if self._thread_running:
            print("Thread is already running")
        else:
            self._thread_running = True
            sleep(1.3)
            print("Background Thread Started")
            update_animepahe()
            while True:
                try:
                    self.recheck()
                except Exception as e:
                    self._thread_running = False
                    raise e
                sleep(self.check_interval)
                if not self._thread_running:
                    break
            print("Thread stopped!")

    # Scans given dir and stores files in self.filelist
    def _scandir(self, root_folder: str, include_subfolder: bool = False):
        if not exists(root_folder):
            raise Exception("{} does not exists.".format(root_folder))
        elif not isdir(root_folder):
            raise Exception("{} is not a folder.".format(root_folder))
        else:
            try:
                dirs = os.listdir(root_folder)
            except PermissionError:
                dirs = []
            except FileNotFoundError:
                print("FileNotFoundError: The system cannot find the path specified: '{}'".format(root_folder))
                dirs = []

            for file in dirs:
                file_path = join(root_folder, file)
                if isdir(file_path):
                    if include_subfolder:
                        self._scandir(file_path, True)
                elif file_path not in self.filelist:
                    self.filelist.append(file_path)

    def initialize_everything(self, error):
        if "Yes" == sg.popup_yes_no("Create new save data?",
                                    grab_anywhere=True, font="Consolas 14", keep_on_top=True,
                                    icon=r"MoeList\static\MoeList\icon.ico"):
            self.data = {}

            if exists(self._title_replace_file) and "Yes" == sg.popup_yes_no(
                    "Title replace json data was found, use it?",
                    grab_anywhere=True, font="Consolas 14", keep_on_top=True,
                    icon=r"MoeList\static\MoeList\icon.ico"):
                with open(self._title_replace_file, "r") as f:
                    self.title_replace = loads(f.read())
            else:
                self.title_replace = {}
            self.save_data()

            os.makedirs(r"MoeList\static\MoeList\banner", exist_ok=True)
            os.makedirs(r"MoeList\static\MoeList\images", exist_ok=True)
            os.makedirs(r"MoeList\static\MoeList\thumbnails\temp", exist_ok=True)
            self.root_folders = []
            while 1:
                folder = sg.popup_get_folder("Select Anime folder to scan for.", title="Select Folder",
                                             font="Consolas 14", keep_on_top=True,
                                             icon=r"MoeList\static\MoeList\icon.ico")
                if folder in (None, ""):
                    # print(self.root_folders)
                    if len(self.root_folders) == 0:
                        sg.popup("Select at least one folder.", title="Error",
                                 grab_anywhere=True,
                                 font="Consolas 14", keep_on_top=True,
                                 icon=r"MoeList\static\MoeList\icon.ico")
                    else:
                        break
                else:
                    self.root_folders.append([
                        folder.replace('/', '\\'),
                        "Yes" == sg.popup_yes_no(
                            "If you inlude subfolders then folders in this folders will also be scanned. Else only files in current folders will be scanned and files in subfolders will be excluded.",
                            title="Include subfolders?",
                            grab_anywhere=True, font="Consolas 14", keep_on_top=True,
                            icon=r"MoeList\static\MoeList\icon.ico"),
                        "Yes" == sg.popup_yes_no(
                            "Do you want to move files from this folder to 'Anime' folder in root of drive? i.e. C:/Anime/one-piece folder?",
                            title="Move files from here?",
                            grab_anywhere=True, font="Consolas 14", keep_on_top=True,
                            icon=r"MoeList\static\MoeList\icon.ico")
                    ])
                    with open(self._root_folders_file, "w") as f:
                        f.write(dumps(self.root_folders, indent=4, sort_keys=True))

            sg.popup("Install Privacy Pass and uBlock Origin Extension in the following prompt.", grab_anywhere=True,
                     font="Consolas 14", keep_on_top=True,
                     icon=r"MoeList\static\MoeList\icon.ico")
            options = webdriver.ChromeOptions()
            options.add_argument(r"user-data-dir={}".format(join(os.getcwd(), r"MoeList\Backbone\chrome_data")))
            browser = webdriver.Chrome(
                executable_path=r"MoeList\Backbone\chromedriver.exe",
                chrome_options=options
            )
            for url in ("https://chrome.google.com/webstore/detail/privacy-pass/ajhmfdgkijocedmfjonnpjfojldioehi",
                        "https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm"):
                if requests.get(url).status_code == 404:
                    sg.popup(f"{url} returned code 404, try later",
                             grab_anywhere=True,
                             font="Consolas 14", keep_on_top=True,
                             icon=r"MoeList\static\MoeList\icon.ico")
                    continue
                browser.get(url)
                elem = WebDriverWait(browser, 300).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "webstore-test-button-label")))
                if elem.get_attribute("innerHTML") == "Add to Chrome":
                    elem.click()
                    # sg.popup_no_titlebar("Press Add extension button.")
                    sleep(0.3)
                    while browser.find_element_by_class_name("webstore-test-button-label").get_attribute(
                            "innerHTML") in ("Checking...", "Add to Chrome"):
                        sleep(0.3)
            browser.close()
            browser.quit()
            sg.popup("Exiting now, please rerun.", grab_anywhere=True, font="Consolas 14", keep_on_top=True,
                     icon=r"MoeList\static\MoeList\icon.ico")
            exit()
        else:
            raise error

    @property
    def data_json(self):
        return json.dumps(self.data, sort_keys=True)

    @property
    def data_summary_json(self):
        p = {
            'Anime': defaultdict(int),
            'Episodes': defaultdict(int),
            'By Season': {
                'None': 0,
                'WINTER': 0,
                'SPRING': 0,
                'SUMMER': 0,
                'FALL': 0,
            },
            'By Status': {
                "None": 0,
                "FINISHED": 0,
                "RELEASING": 0,
                "NOT_YET_RELEASED": 0,
            },
            'By Genres': defaultdict(int),
            'By Type': defaultdict(int),
            'By Year': defaultdict(int),
        }
        for anilist_id, anime in self.data.items():
            p['By Type'][str(anime['type'])] += 1
            p['By Year'][str(anime['year'])] += 1
            p['By Season'][str(anime['season'])] += 1
            p['By Status'][str(anime['status'])] += 1

            any_ep_deleted = False
            any_ep_new = False
            for ep, ep_data in anime['episode_list'].items():
                p['Episodes']['Total'] += 1
                if ep_data['path'] is None:
                    p['Episodes']['Deleted'] += 1
                    any_ep_deleted = True
                elif ep_data['watched']:
                    p['Episodes']['Watched'] += 1
                else:
                    p['Episodes']['New'] += 1
                    any_ep_new = True

            for gnr in anime['genres']:
                p['By Genres'][gnr] += 1

            p['Anime']['Total'] = len(self.data)
            if not any_ep_new:
                p['Anime']['Completely Watched'] += 1
            if not any_ep_deleted:
                p['Anime']['Have Full Downloaded'] += 1
        return json.dumps(p)

    # Load data from files
    def _load_data_from_files(self):
        with open(self._title_replace_file, "r") as f:
            self.title_replace = loads(f.read())
        with open(self._json_data_file, "r") as f:
            self.data = loads(f.read())

    def _load_data_from_encrypt(self):
        with open(self._encryption_key_file, "rb") as f:
            crypt = Fernet(f.read())
        try:
            with open(self._encrypted_data_file, "rb") as f:
                self.data, self.title_replace = pickle.loads(bz2.decompress(crypt.decrypt(f.read())))
            print("Loaded Data from encrypted file")
        except FileNotFoundError as e:
            self.initialize_everything(e)

    # Save data to files
    def save_data(self):
        print("Saving Data to file...", end="")
        with open(self._title_replace_file, "w") as f:
            f.write(dumps(self.title_replace, indent=4, sort_keys=True))
        with open(self._json_data_file, "w") as f:
            f.write(dumps(self.data, indent=4, sort_keys=True))

        with open(self._encryption_key_file, "rb") as f:
            crypt = Fernet(f.read())
        with open(self._encrypted_data_file, "wb") as f:
            f.write(crypt.encrypt(bz2.compress(pickle.dumps((self.data, self.title_replace)))))
        print("\tSaved")
        self._changed = False

    def airing_time(self, anilist_id: Union[str, int]):
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            if self.data[anilist_id]["nextEp"] is None:
                return None
            else:
                return self.data[anilist_id]["nextEp"]["airingAt"]
        else:
            return None

    def is_deleted(self, anilist_id: Union[str, int]) -> bool:
        anime = self.data[str(anilist_id)]
        if anime["status"] == "NOT_YET_RELEASED":
            return False
        for ep_no, ep in anime["episode_list"].items():
            if ep["path"] is not None:
                return False
        return True

    # todo: ??
    # Returns if all episode has been watched or not
    def is_completed(self, anilist_id: Union[str, int]) -> bool:
        anime = self.data[str(anilist_id)]
        if anime["status"] == "NOT_YET_RELEASED" or anime.get("episodes") is None:
            return False
        elif anime["episodes"] <= self.get_max_watched_ep(str(anilist_id)):
            return True
        else:
            return False

    # todo: ??
    # Returns if all downloaded episode has been watched or not
    def is_all_downloaded_ep_watched(self, anilist_id: Union[str, int]) -> bool:
        anime = self.data[str(anilist_id)]
        for ep_no, ep in anime["episode_list"].items():
            if ep["watched"] is False:
                return False
        return True

    def get_episode_sorted(
            self,
            anilist_id: Union[str, int],
            fill_missing: bool = True,
            fill_till_1: bool = True,
            remove_watched: bool = False
    ) -> dict:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            anime = self.data[anilist_id]
            episodes_list = {}
            temp = []
            for ep_no, ep in anime["episode_list"].items():
                if remove_watched and ep["watched"] is False:
                    temp.append(int(ep_no))
                elif remove_watched:
                    continue
                else:
                    temp.append(int(ep_no))
            p = None
            for ep_no in sorted(temp, reverse=True):
                if fill_missing:
                    if p is not None:
                        while p - ep_no != 1:
                            p -= 1
                            episodes_list[p] = {
                                'path': None,
                                'watched': True
                            }
                    p = ep_no
                episodes_list[ep_no] = anime["episode_list"][str(ep_no)]
            if fill_till_1 and p is not None and p > 1:
                while p > 1:
                    p -= 1
                    episodes_list[p] = {
                        'path': None,
                        'watched': True
                    }
            context = {
                'anilist_id': anilist_id,
                'episodes': episodes_list
            }
            return context

    def get_ids_sorted_by_year(self, anilist_ids: Union[list, set]) -> dict:
        temp = {}
        x = datetime.datetime.now()
        for anilist_id in anilist_ids:
            if anilist_id in self.data:
                anime = self.data[anilist_id]
                year = x.year if anime["year"] is None else anime["year"]
                if year not in temp:
                    temp[year] = [anilist_id]
                else:
                    temp[year].append(anilist_id)

        seasons = ["WINTER", "SPRING", "SUMMER", "FALL", None]
        for year in temp:
            temp_anilist_ids = []
            for season in seasons:
                for anilist_id in temp[year]:
                    if self.data[anilist_id]["season"] == season:
                        temp_anilist_ids.append(anilist_id)

            if len(temp[year]) != len(temp_anilist_ids):
                raise Exception

            temp[year] = temp_anilist_ids

        for year in temp:
            temp[year] = reversed(temp[year])

        return temp

    def get_cover(self, anilist_id: Union[str, int], animelist: bool = False) -> Union[str, None]:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            if animelist:
                return self.data[anilist_id]['cover']
            else:
                self.download_image(slugify(self.data[anilist_id]['title']), self.data[anilist_id]['cover'], "cover")
                path = join(r"MoeList\images", slugify(self.data[anilist_id]['title']) + ".jpg")
                path_webp = join(r"MoeList\images", slugify(self.data[anilist_id]['title']) + ".webp")
                return path # if exists(join(r"MoeList\static", path)) else path_webp
        else:
            return None

    def get_small_cover(self, anilist_id: Union[str, int]) -> Union[str, None]:
        if str(anilist_id) in self.data:
            return self.small_image(self.get_cover(anilist_id))
        else:
            return None

    def get_banner(self, anilist_id: Union[str, int], animelist: bool = False) -> Union[str, None]:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            anime = self.data[anilist_id]
            if anime['banner'] is not None:
                if animelist:
                    return anime['banner']
                else:
                    self.download_image(slugify(anime['title']), anime['banner'], "banner")
                    path = join(r"MoeList\banner", slugify(anime['title']) + ".jpg")
                    path_webp = join(r"MoeList\banner", slugify(anime['title']) + ".webp")
                    return path  # if exists(path) else path_webp
            else:
                return None
        else:
            return None

    @property
    def random_banner(self) -> str:
        anilist_id = secrets.choice(list(self.data.keys()))
        while self.data[anilist_id]["cover"] is None:
            anilist_id = secrets.choice(list(self.data.keys()))
        return self.get_banner(anilist_id)

    def get_relations(self, anilist_id: Union[str, int]) -> Union[list, None]:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            t1 = []
            for rel in self.data[anilist_id]['relations']:
                y = {}
                self.download_image(slugify(rel['title']), rel['cover'], "cover")
                path = join(r"MoeList\images", slugify(rel['title']) + ".jpg")
                path_webp = join(r"MoeList\images", slugify(rel['title']) + ".webp")
                for z in rel:
                    y[z] = rel[z]
                y['cover'] = path if exists(join(r"MoeList\static", path)) else path_webp
                t1.append(y)
            return t1
        else:
            return None

    @staticmethod
    def download_image(slug, link=None, image_type="cover"):
        folder = "images" if image_type == "cover" else image_type
        path = join(r"MoeList\static\MoeList", folder, slug + ".jpg")
        path_webp = join(r"MoeList\static\MoeList", folder, slug + ".webp")
        printed = False
        if link is not None and not exists(path):  # and not exists(path_webp):
            print("{} {}".format(slug, image_type), end="")
            try:
                response = requests.get(link)
            except requests.exceptions.ConnectionError:
                print(" downloading failed, Connection Error", end="")
            else:
                with open(path, "wb") as f:
                    f.write(response.content)
                    print(" downloaded", end="")
            printed = True

        if exists(path) and not exists(path_webp):
            result = cwebp(path, path_webp, "-q 100")
            if result['exit_code'] == 0:
                print(" and converted", end="")
            else:
                print(" but failed to convert")
                print(result['stderr'].decode(), end="")
            printed = True

        # if exists(path) and exists(path_webp):
        #     if getsize(path_webp) <= getsize(path):
        #         os.remove(path)
        #         print(f", removed {basename(path)}", end="")
        #         printed = True
        if printed:
            print("")

    @staticmethod
    def remove_image(slug, image_type="cover"):
        folder = "images" if image_type == "cover" else image_type
        path = join(r"MoeList\static\MoeList", folder, slug + ".jpg")
        path_webp = join(r"MoeList\static\MoeList", folder, slug + ".webp")
        if exists(path):
            os.remove(path)
        if exists(path_webp):
            os.remove(path_webp)

    @staticmethod
    def small_image(img_path):
        b = basename(img_path).split(".")
        small_path = join(dirname(img_path), ".".join(b[:-1]) + "-small." + b[-1])
        if not exists(join(r"MoeList\static", small_path)):
            print(f"Small image of {basename(img_path)} does not exists..", end="")
            image = Image.open(join(r"MoeList\static", img_path))
            width, height = image.size
            image.thumbnail((100, round(100 * height / width) + 1))
            try:
                image.save(join(r"MoeList\static", small_path))
            except OSError:
                image = image.convert('RGB')
                image.save(join(r"MoeList\static", small_path))
            print("Created")
        return small_path

    def get_max_ep(self, anilist_id: Union[str, int]) -> str:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            max_ep = 0
            for ep in self.data[anilist_id]['episode_list']:
                max_ep = int(ep) if int(ep) > max_ep else max_ep
            return str(max_ep)
        else:
            raise KeyError

    def get_max_watched_ep(self, anilist_id: Union[str, int]) -> int:
        anilist_id = str(anilist_id)
        if anilist_id in self.data:
            max_ep = 0
            for ep, ep_data in self.data[anilist_id]['episode_list'].items():
                if int(ep) > max_ep and ep_data["watched"]:
                    max_ep = int(ep)
            return max_ep
        else:
            raise KeyError

    def get_next_ep(self, anilist_id: Union[str, int], ep: Union[str, int]) -> Union[str, None]:
        anilist_id = str(anilist_id)
        ep = int(ep)
        if anilist_id in self.data:
            eps = sorted([int(e) for e in list(self.data[anilist_id]["episode_list"].keys())])
            for e in eps:
                if e > ep:
                    return str(e)
            return None

    def get_prev_ep(self, anilist_id: Union[str, int], ep: Union[str, int]) -> Union[str, None]:
        anilist_id = str(anilist_id)
        ep = int(ep)
        if anilist_id in self.data:
            eps = sorted([int(e) for e in list(self.data[anilist_id]["episode_list"].keys())], reverse=True)
            for e in eps:
                if e < ep:
                    return str(e)
            return None

    def get_episodes_thumb(self, anilist_id: Union[str, int]) -> Union[list, None]:
        eps = []
        anilist_id = str(anilist_id)
        if anilist_id not in self.data:
            return None
        anime = self.data[anilist_id]
        for ep in range(1, int(self.get_max_ep(anilist_id)) + 1):
            ep = str(ep)
            eps.append({
                'available': False if ep not in anime["episode_list"] else True if
                anime["episode_list"][ep]["path"] is not None and exists(anime["episode_list"][ep]["path"]) else False,
                'ep': ep,
                'thumb': None if not exists(
                    r"MoeList\static\MoeList\thumbnails\{} ep {}.jpeg".format(anime['slug'], ep)
                ) else r"MoeList\thumbnails\{} ep {}.jpeg".format(anime['slug'], ep)
            })
        return eps

    def mal_to_animepahe(self, mal: Union[str, int]) -> Union[int, None]:
        mal = int(mal)
        print(f"Searching for Animepahe id with MAL {mal}.. ", end="")
        with open(self._animepahe_data_file, "rb") as f:
            animepahe_data = json.loads(bz2.decompress(f.read()))
        for name, ids in animepahe_data.items():
            if ids["MyAnimeList"] == mal:
                print(f"Found {ids['Animepahe']}")
                return ids["Animepahe"]
        print("Not Found")
        return None

    # remove it?
    # def search_animepahe_id(self, query):
    #     print("Searching AnimePahe for {}".format(query))
    #     params = {
    #         'm': 'search',
    #         'l': 8,
    #         'q': query.strip()
    #     }
    #     response = requests.get(self.animepahe_api_url, headers=self.animepahe_header, params=params)
    #     try:
    #         sr = response.json()
    #     except json.decoder.JSONDecodeError:
    #         print("JSONDecodeError")
    #         print(response.content.decode())
    #         return None
    #     if 'data' not in sr:
    #         key = self.get_key(query)
    #         if key is not None:
    #             print("\tQuery returned nothing, trying English title")
    #             print("Result:")
    #             print("\ttitleEn: {}".format(self.data[key]["titleEn"]))
    #             if self.data[key]["titleEn"] is not None:
    #                 params = {
    #                     'm': 'search',
    #                     'l': 8,
    #                     'q': self.data[key]["titleEn"]
    #                 }
    #                 sr = requests.get(
    #                     self.animepahe_api_url,
    #                     headers=self.animepahe_header,
    #                     params=params
    #                 ).json()
    #
    #     if 'data' not in sr:
    #         print("\tQuery returned nothing.")
    #         return None
    #
    #     for r in sr['data']:
    #         if query == r['title']:
    #             print("\tExact match found! Animepahe Id: {}".format(r['id']))
    #             return r["id"]
    #     print("Result title did not match 100%, please select yourself")
    #     key = self.get_key(query)
    #     if key is not None:
    #         return self.animepahe_search_dialog(
    #             query,
    #             "{}, {} EP, {} {} {}".format(
    #                 self.data[key]["type"],
    #                 self.data[key]["episodes"],
    #                 self.data[key]["season"],
    #                 self.data[key]["year"],
    #                 self.data[key]["status"]
    #             ),
    #             sr['data']
    #         )
    #     else:
    #         return self.animepahe_search_dialog(
    #             query,
    #             None,
    #             sr['data']
    #         )

    # @staticmethod
    # def animepahe_search_dialog(query, query_data, results):
    #     layout = [
    #         [sg.Text('AnimePahe Search', pad=((5, 5), (5, 0)), font="Verdana 14")],
    #         [sg.Text(query, justification="left", pad=((15, 5), (5, 0)))],
    #     ]
    #     if query_data is not None:
    #         layout.append(
    #             [sg.Text(query_data, font="Consolas 11", text_color="#888888", pad=((15, 5), (0, 5)))]
    #         )
    #     d = True
    #     frame = []
    #     for anime in results:
    #         frame.append([sg.Radio(anime['title'], group_id="2", key=anime['id'], default=d, pad=((5, 5), (0, 0)))])
    #         frame.append([sg.Text(
    #             "{}, {} EP, {} {} {}, ID:{}".format(
    #                 anime['type'],
    #                 anime['episodes'],
    #                 anime['season'],
    #                 anime['year'],
    #                 anime['status'],
    #                 anime['id']
    #             ),
    #             font="Consolas 11",
    #             text_color="#888888",
    #             pad=((5, 5), (0, 6)),
    #         )])
    #         d = False
    #     layout.append([sg.Frame("Results", frame)])
    #     layout.append([sg.Submit(button_color=('white', 'blue')), sg.Cancel(button_color=('yellow', 'red'))])
    #
    #     event, values = sg.Window('MoeList', layout, no_titlebar=True, grab_anywhere=True, keep_on_top=True, ).read(
    #         close=True)
    #     if event != "Submit":
    #         return None
    #     else:
    #         for key, value in values.items():
    #             if value:
    #                 return key

    @staticmethod
    def anilist_search_dialog(title: str, file: str, results: list) -> Union[int, None]:
        layout = [
            [sg.Text('Anilist Search', pad=((5, 5), (5, 0)), font="Verdana 14")],
            [sg.Text(title, justification="left", pad=((15, 5), (5, 0)))],
            [sg.Text(basename(file), justification="left", pad=((15, 5), (5, 0)))],
        ]
        d = True
        frame = []
        for anime in results:
            frame.append([sg.Radio(anime['title'], group_id="1", key=anime['id'], default=d, pad=((5, 5), (0, 0)))])
            if anime['titleEn'] is not None:
                frame.append([sg.Text(anime["titleEn"], font="Verdana 11", text_color="#888888", pad=((5, 5), (0, 0)))])
            frame.append([sg.Text(
                "{}, {} EP, {} {} {}, ID:{}".format(
                    anime['format'],
                    anime['episodes'],
                    anime['season'],
                    anime['year'],
                    anime['status'],
                    anime['id']
                ),
                font="Consolas 11", text_color="#888888", pad=((5, 5), (0, 6)))])
            d = False
        layout.append([sg.Frame("Results", frame)])
        layout.append([sg.Submit(button_color=('white', 'blue')), sg.Cancel(button_color=('yellow', 'red'))])
        event, values = sg.Window('MoeList', layout, no_titlebar=True, grab_anywhere=True, keep_on_top=True, ).read(
            close=True)
        if event != "Submit":
            return None
        else:
            for key, value in values.items():
                if value:
                    return key
        return None
