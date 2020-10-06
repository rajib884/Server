import bz2
import re
import json
from pprint import pprint
from time import sleep

import requests
from bs4 import BeautifulSoup


def cf_decode_email(enc_str):
    r = int(enc_str[:2], 16)
    return ''.join([chr(int(enc_str[i:i + 2], 16) ^ r) for i in range(2, len(enc_str), 2)])


def update_animepahe():
    file = r"MoeList\data\animepahe_data.bz2"

    animepahe_anime_url = "https://animepahe.com/anime"
    id_pattern = r"\"https:\/\/pahe.win\/a\/(\d+?)\""
    mal_pattern = r"<meta name\=\"myanimelist\" content\=\"(\d+?)\" />"

    print(f"Loading {animepahe_anime_url}")
    try:
        response = requests.get(animepahe_anime_url)
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
