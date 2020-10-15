import bz2
import json
import os
import re
from json import JSONDecodeError
from os import path
from os.path import join
from pprint import pprint
from time import sleep
from typing import Union

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

file = r"MoeList\data\animepahe_data.bz2"
anime_url = "https://animepahe.com/anime"
api_url = 'https://animepahe.com/api'
header_file = r"MoeList\data\animepahe_header.json"
header = json.load(open(header_file))


def cf_decode_email(enc_str):
    r = int(enc_str[:2], 16)
    return ''.join([chr(int(enc_str[i:i + 2], 16) ^ r) for i in range(2, len(enc_str), 2)])


def decode_encoded_data(encoded_string, key, char_offset, separator):
    print("Decoding data...")
    decoded_str = ""
    for word_from_string in encoded_string.split(key[separator]):
        for n, char_from_key in enumerate(key):
            word_from_string = word_from_string.replace(char_from_key, str(n))
        v = 0
        for n, char_from_key in enumerate(reversed(word_from_string)):
            v += pow(separator, n) * int(char_from_key)
        try:
            decoded_str += chr(v - char_offset)
        except ValueError:
            pass
    return decoded_str


def check_cookie(ck, link="https://kwik.cx/f/4PQFJ0Wofthj"):
    print("Checking cookie with link {}".format(link), end="")
    headers = {
        'User-Agent': header["User-Agent"],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
    }
    cookies = {}
    for cookie in ck:
        cookies[cookie['name']] = cookie['value']
    try:
        response = requests.get(link, headers=headers, cookies=cookies)
    except requests.exceptions.ConnectionError:
        print(" ..Connection Error")
        return None
    if response.status_code == 200:
        print(" ..OK")
        return True
    else:
        print(" ..Failed")
        return False


def check_header():
    print("Checking Animepahe header..", end="")
    global header
    response = requests.get("https://animepahe.com", headers=header)
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
        header = {
            "User-Agent": browser.execute_script("return navigator.userAgent;"),
            "cookie": "cf_clearance={}".format(cf_clearance or "null")
        }
        browser.close()
        browser.quit()
        json.dump(header, open(header_file, "w"), indent=4)
        print(f"cf_clearance: {cf_clearance}")
    else:
        print("OK")


def mal_to_animepahe(mal: Union[str, int]) -> Union[int, None]:
    mal = int(mal)
    print(f"Searching for Animepahe id with MAL {mal}.. ", end="")
    with open(file, "rb") as f:
        data = json.loads(bz2.decompress(f.read()))
    for name, ids in data.items():
        if ids["MyAnimeList"] == mal:
            print(f"Found {ids['Animepahe']}")
            return ids["Animepahe"]
    print("Not Found")
    return None


def download_link(kwik_link):
    headers = {
        'User-Agent': header["User-Agent"],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
    }
    cookies = {}
    try:
        ck = json.load(open("cookies.json", "rb"))
    except FileNotFoundError:
        print("Cookie not found, getting online one..")
        # ck = json.loads(getfile("cookies.json"))  # todo: remove this
        raise FileNotFoundError

    if check_cookie(ck, kwik_link) is False:
        print("Cookie not valid anymore, getting new..")
        # browser = webdriver.Firefox(executable_path=r"MoeList\Backbone\geckodriver.exe", timeout=300)
        # browser.install_addon(path.join(os.getcwd(), r"MoeList\Backbone\Privacy Pass.xpi"), temporary=False)
        options = webdriver.ChromeOptions()
        options.add_argument(r"user-data-dir={}".format(path.join(os.getcwd(), r"MoeList\Backbone\chrome_data")))
        browser = webdriver.Chrome(
            executable_path=r"MoeList\Backbone\chromedriver.exe",
            chrome_options=options
        )
        browser.get("chrome://version/")
        header["User-Agent"] = browser.execute_script("return navigator.userAgent;")
        sleep(2)
        browser.get(kwik_link)
        WebDriverWait(browser, 3000).until(EC.title_contains("AnimePahe"))
        sleep(1)
        ck = browser.get_cookies()
        browser.close()
        browser.quit()
        # pickle.dump(ck, open("cookies.pkl", "wb"))
        json.dump(ck, open("cookies.json", "w"), indent=4)
        json.dump(header, open(header_file, "w"), indent=4)
        # threading.Thread(target=putfile, daemon=True, kwargs={"filename": "cookies.json"})  # todo: remove this

    for cookie in ck:
        cookies[cookie['name']] = cookie['value']

    session = requests.session()
    session.headers.update(headers)
    session.cookies.update(cookies)

    print("Loading First Page...", end="")
    try:
        response = session.get(kwik_link)
    except requests.exceptions.ConnectionError:
        return {'error': "Connection Error"}

    if response.status_code != 200:
        print("\tError in cookies")
        print("Setting New Cookie did Not help!")
        print(response.status_code)
        print(response.content.decode())
        pprint(cookies)
        raise Exception("Super Duper Error!")

    print("Loaded")
    pattern = r"String\.fromCharCode\(\_0x\S+?\)}return decodeURIComponent\(escape\(\S+?\)\)\}\(\"(" \
              r"?P<encoded_string>[a-zA-Z]+?)\",(?P<useless_1>\d+?),\"(?P<key>[a-zA-Z]+?)\",(?P<char_offset>\d+?)," \
              r"(?P<separator>\d+?),(?P<useless_2>\d+?)\)\)\n  \</script>\n"
    try:
        matched = re.search(pattern, response.content.decode()).groupdict()
    except AttributeError:
        print(response.content.decode())
        print("Error")
        return {'error': "Error"}

    decoded_string = decode_encoded_data(
        encoded_string=matched['encoded_string'],
        key=matched['key'],
        char_offset=int(matched['char_offset']),
        separator=int(matched['separator'])
    )
    print("Obtaining Token...", end="")
    pattern = r"\<input type=\"hidden\" name=\"_token\" value=\"(?P<_token>[0-9a-zA-Z]+?)\"\>"
    data = re.search(pattern, decoded_string).groupdict()
    print("Done")

    headers = {
        'User-Agent': header["User-Agent"],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://kwik.cx',
        'Connection': 'keep-alive',
        'Referer': kwik_link,
        'Upgrade-Insecure-Requests': '1',
    }
    session.headers.update(headers)
    print("Loading 2nd page...", end="")
    response = session.post(kwik_link.replace("/f/", "/d/"), data=data, allow_redirects=False)
    if response.status_code == 302:
        print("Link found")
        url = response.headers['location']
        print(url)
        return {'link': url}
    else:
        print("Error. 2nd page did not redirect to download link.")
        return {'error': "Error. 2nd page did not redirect to download link."}


def get_kwik_link(anime_data, session, anilist_id, ep):
    # todo: use these arguments!
    # anilist_id = str(int(anilist_id))
    # ep = str(int(ep))
    print("Loading kwik links from animepahe..", end="")
    params = {
        'm': 'links',
        'id': anime_data,
        'session': session,
        'p': 'kwik',
    }

    x = requests.get(api_url, headers=header, params=params)
    try:
        response = json.loads(x.content)
    except JSONDecodeError:
        print(f"Error {x.status_code}\n{x.content}")
        return {f"Error {x.status_code}": ""}
    else:
        print("Loaded")
        json.dump(response, open("tmp.response.json", "w"), indent=4, sort_keys=True)
    temp = {}
    print("Links:")
    for anime_data in response['data']:
        for quality, info in anime_data.items():
            title = "{} {}MB {} {}p {} {}".format(
                info['disc'],
                round(info['filesize'] / 1048576),
                info['fansub'],
                quality,
                "HQ" if info['hq'] else "",
                info["audio"].title()
            )
            temp[title] = anime_data[quality]['kwik'].replace("https://kwik.cx/e/", "/MoeList/kwikDownload/")

    pprint(temp)
    return temp


def animepahe_data(animepahe_id, find_till=None, offset=0):
    page = 1
    params = {
        'm': 'release',
        'id': animepahe_id,
        'l': 30,
        'sort': 'episode_desc',
        'page': page,
    }

    try:
        x = requests.get(api_url, headers=header, params=params)
    except requests.exceptions.ConnectionError:
        return {"error": "Connection Error, Check your connection"}
    try:
        response = json.loads(x.content)
    except JSONDecodeError:
        print(x.content)
        return {"error": "json.decoder.JSONDecodeError!!"}
    temp = {
        "current_page": response["current_page"],
        "last_page": response["last_page"],
        "next_page_url": response["next_page_url"],
        "total": response["total"],
        "data": []
    }
    if 'data' in response:
        for c in response["data"]:
            temp["data"].append({
                'created_at': c['created_at'],
                'episode': c['episode'] - offset,
                'filler': c['filler'],
                'id': c['id'],
                'session': c['session'],
                'anime_id': animepahe_id
            })

    if find_till is None or 'data' not in response:
        return temp
    else:
        min_ep = min([t['episode'] for t in temp['data']])
        while min_ep > find_till + 1 and temp["next_page_url"] is not None:
            page += 1
            params = {
                'm': 'release',
                'id': animepahe_id,
                'l': 30,
                'sort': 'episode_desc',
                'page': page,
            }
            try:
                x = requests.get(api_url, headers=header, params=params)
                response = json.loads(x.content)
            except requests.exceptions.ConnectionError:
                return {"error": "Connection Error, Check your connection"}
            except JSONDecodeError:
                print(x.content)
                return {"error": "json.decoder.JSONDecodeError!!"}

            temp["current_page"] = response["current_page"]
            temp["next_page_url"] = response["next_page_url"]
            if 'data' in response:
                for c in response["data"]:
                    temp["data"].append({
                        'created_at': c['created_at'],
                        'episode': c['episode'] - offset,
                        'filler': c['filler'],
                        'id': c['id'],
                        'session': c['session'],
                        'anime_id': animepahe_id
                    })
            min_ep = min([t['episode'] for t in temp['data']])
        return temp


def update_animepahe():
    id_pattern = r"\"https:\/\/pahe.win\/a\/(\d+?)\""
    mal_pattern = r"<meta name\=\"myanimelist\" content\=\"(\d+?)\" />"

    print(f"Loading {anime_url}")
    try:
        response = requests.get(anime_url)
    except requests.exceptions.ConnectionError:
        print("Connection Error")
        return
    print(f"Page size: {round(len(response.content) / 1024, 2)}KB")
    main_page = BeautifulSoup(response.content, "lxml")

    for enc_email in main_page.find_all(class_="__cf_email__"):
        t = main_page.new_tag("span")
        t.string = cf_decode_email(enc_email['data-cfemail'])
        enc_email.replace_with(t)

    with open(file, "rb") as f:
        data = json.loads(bz2.decompress(f.read()))

    print("Processing..")
    new_anime_found = False
    for a in main_page.find_all(href=re.compile("/anime/")):
        if a.get_text() not in data:
            new_anime_found = True
            name = a.get_text()
            link = "https://animepahe.com" + a['href']
            print(f"New Anime {name} {link}")
            retry = 0
            while True:
                try:
                    response = requests.get(link)
                    break
                except requests.exceptions.ConnectionError as er:
                    print(er)
                    if retry > 5:
                        raise er
                    else:
                        retry += 1
                        print("Sleeping..")
                        sleep(60)
                        print(f"Retry no. {retry}")
            anime_page = BeautifulSoup(response.content, "lxml")
            try:
                t = anime_page.find(id="modalBookmark").find(class_="form-control")['value']
            except AttributeError:
                t = 'https://pahe.win/a/' + re.findall(id_pattern, response.content.decode())[0]
            data[name] = {'Animepahe': int(t.split('/')[-1])}
            try:
                external_links = anime_page.find(class_="external-links").find_all('a')
            except AttributeError:
                external_links = []
            if len(external_links) > 0:
                for external_link in external_links:
                    external_name = external_link.get_text()
                    if external_name not in ('AnimeNewsNetwork', 'Background'):
                        data[name][external_name] = int(external_link['href'].split('/')[-1])
                    elif external_name == 'AnimeNewsNetwork':
                        data[name][external_name] = int(external_link['href'].split('=')[-1])
                    elif external_name == 'Background':
                        pass
            else:
                data[name]["MyAnimeList"] = int(re.findall(mal_pattern, response.content.decode())[0])
            pprint(data[name])
            with open(file, "wb") as f:
                f.write(bz2.compress(json.dumps(data, indent=4, sort_keys=True).encode()))
            with open(".".join(file.split(".")[:-1]) + ".json", "w") as f:
                f.write(json.dumps(data, indent=4, sort_keys=True))

    if not new_anime_found:
        print("No new anime found")


if __name__ == '__main__':
    update_animepahe()
