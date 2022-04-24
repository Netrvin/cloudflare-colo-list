import requests
import json
import bs4
import os
import sys
import re
import unicodedata

os.chdir(os.path.split(os.path.realpath(sys.argv[0]))[0])

def get(url, retry=3):
    try:
        r = requests.get(url, timeout=5)
        return r
    except:
        if retry > 0:
            return get(url, retry-1)
        else:
            raise Exception('Failed to get url: {}'.format(url))

def generate():
    data = {}
    soup = bs4.BeautifulSoup(get('https://www.cloudflarestatus.com/').text, 'html.parser')
    soup = soup.find('div', {'class': 'components-container one-column'})
    continents = soup.find_all('div', recursive=False)
    continents.pop(0)
    for continent in continents:
        for div in continent.find('div', {'class': 'child-components-container'}).find_all('div'):
            span = div.find('span').get_text(strip=True)
            span = unicodedata.normalize("NFKD", span)
            regex = re.search(r'^([\s\S]+) +- +\(([A-Z]{3})\)$', span)
            name = regex.group(1)
            colo = regex.group(2)
            data[colo] = {}
            data[colo]['name'] = name
    speed_locations = json.loads(get('https://speed.cloudflare.com/locations').text)
    for location in speed_locations:
        iata = location['iata']
        if iata in data:
            data[iata].update(location)
            del data[iata]['iata']
        else:
            print(iata, 'not found in cloudflare status')
            data[iata] = location
            data[iata]['name'] = location['city'] + ', ' + location['cca2']
            del data[iata]['iata']
    return data


if __name__ == '__main__':
    json.dump(generate(), open('colo.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False, sort_keys=True)
