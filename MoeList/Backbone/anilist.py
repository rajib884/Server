from pprint import pprint

import requests

url = 'https://graphql.anilist.co'


# AniList get info by id
def info(anilist_id: int) -> dict:
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

    anilist_json = requests.post(url, json={'query': query, 'variables': variables}).json()

    if "errors" in anilist_json:
        pprint(anilist_json)
        raise KeyError
    else:
        return simplify_anilist_json(anilist_json["data"]["Media"])


# AniList search by name
def search(name: str, only_airing: bool = False, max_in_1_page: int = 10) -> list:
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
    anilist_json = requests.post(url, json={'query': query, 'variables': variables}).json()

    if "errors" in anilist_json:
        raise KeyError
    else:
        return simplify_search_json(anilist_json["data"]["Page"]["media"])


# MyAnimeList id to AniList id
def mal_to_anilist(mal: int):
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
    anilist_json = requests.post(url, json={'query': query, 'variables': variables}).json()

    if "errors" in anilist_json:
        raise KeyError
    else:
        return simplify_json(anilist_json["data"]["Media"])


if __name__ == '__main__':
    pprint(info(113538))
    pprint(search("One"))
    pprint(mal_to_anilist(40776))
