import json
import secrets
from os.path import exists
from pprint import pprint
from typing import Union

import requests


def is_int(t):
    try:
        int(t)
        return True
    except ValueError:
        return False


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
        # pprint(self.current_user_anime_list())
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
                    f.write(json.dumps(self.data, indent=4, sort_keys=True))
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

    def current_user_anime_list(self, user_name='@me', status=None, sort='anime_title', limit=10,
                                offset=0):  # todo: status, sort not used!
        if status not in ('watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch', None):
            print(f"Error: {status} is not valid status")
            return None
        if sort not in ('list_score', 'list_updated_at', 'anime_title', 'anime_start_date', 'anime_id'):
            print(f"Error: {status} is not valid status")
            return None
        params = {
            'fields': 'list_status,num_episodes',
            'limit': min(limit, 1000),
            'offset': offset,
        }
        response = self.get(f'https://api.myanimelist.net/v2/users/{user_name}/animelist', params)
        if limit > 1000 and 'next' in response['paging']:
            t = self.current_user_anime_list(user_name, status, sort, limit - 1000, offset + 1000)
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
        t = self.get(f"https://api.myanimelist.net/v2/anime/{anime_id}", params)
        if t is None:
            return t
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
