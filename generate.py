import requests
import json
import bs4
import os
import sys
import re
import time
import unicodedata
import pandas as pd

os.chdir(os.path.split(os.path.realpath(sys.argv[0]))[0])


def get(url, retry=5):
    try:
        r = requests.get(url, timeout=5)
        return r
    except:
        if retry > 0:
            time.sleep(1)
            return get(url, retry - 1)
        else:
            raise Exception('Failed to get url: {}'.format(url))


def generate():
    data = {}

    # www.cloudflarestatus.com for DC list
    # Site Struct: Table --div--> continents --div--> DCs --text--> Info
    soup = bs4.BeautifulSoup(get('https://www.cloudflarestatus.com/').text, 'html.parser')
    soup = soup.find('div', {'class': 'components-container one-column'})
    continents = soup.find_all('div', recursive=False)
    continents.pop(0)
    for continent in continents:
        for div in continent.find('div', {'class': 'child-components-container'}).find_all('div', recursive=False):
            txt = div.get_text(strip=True)
            txt = unicodedata.normalize("NFKD", txt)
            regex = re.search(r'^([\s\S]+?)( +-)? +\(([A-Z]{3})\)', txt)
            name = regex.group(1)
            colo = regex.group(3)
            data[colo] = {}
            data[colo]['name'] = name

    # speed.cloudflare.com for locations
    # format: json
    speed_locations = json.loads(get('https://speed.cloudflare.com/locations').text)
    country_codes = json.load(open('country.json', 'r', encoding='utf-8'))
    for location in speed_locations:
        iata = location['iata']
        if iata in data:
            data[iata].update(location)
            del data[iata]['iata']
        else:
            print(iata, 'not found in cloudflare status')
            data[iata] = location
            data[iata]['name'] = location['city'] + ', ' + country_codes[location['cca2']]
            del data[iata]['iata']
    return data, speed_locations


if __name__ == '__main__':
    match_data, location_data = generate()

    locations_json_content = json.dumps(location_data, indent=4, ensure_ascii=False, sort_keys=True)
    dc_colos_json_content = json.dumps(match_data, indent=4, ensure_ascii=False, sort_keys=True)
    content_changed = True

    if (os.path.exists('DC-Colos.json')):
        with open('DC-Colos.json', 'r', encoding='utf-8') as f:
            if f.read() == dc_colos_json_content:
                content_changed = False

    if not content_changed:
        print('Content unchanged, exiting...')
        sys.exit()

    # save locations to json
    with open('locations.json', 'w', encoding='utf-8') as f:
        f.write(locations_json_content)

    # save as DC-Colo matched data json
    with open('DC-Colos.json', 'w', encoding='utf-8') as f:
        f.write(dc_colos_json_content)

    # save as xlsx & csv
    dt = pd.DataFrame(match_data).T
    dt.index.name = 'colo'
    dt.to_excel('DC-Colos.xlsx')
    dt.to_csv('DC-Colos.csv', encoding='utf-8')

    # final check for log
    for colo in dt.index[dt.cca2.isnull()]:
        print(colo, 'not found in cloudflare locations')
