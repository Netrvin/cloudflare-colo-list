import requests
import json
import bs4
import os
import sys

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
            span = div.find('span').text
            name = span.split('-')[0].strip()
            colo = span.split('-')[1].strip().replace('(', '').replace(')', '')
            data[colo] = name
    return data


if __name__ == '__main__':
    json.dump(generate(), open('colo.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False, sort_keys=True)
