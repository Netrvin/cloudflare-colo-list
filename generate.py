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


def get(url, retry=5, referer=''):
    try:
        headers = {'referer': referer}
        r = requests.get(url, timeout=5, headers=headers)
        return r
    except:
        if retry > 0:
            time.sleep(1)
            return get(url, retry - 1, referer)
        else:
            raise Exception('Failed to get url: {}'.format(url))


def generate():

    country_codes = json.load(open('country.json', 'r', encoding='utf-8'))
    country_codes_inv = {v: k for k, v in country_codes.items()}

    data = {}

    # https://www.cloudflarestatus.com/api/v2/components.json for DC list
    components_json = json.loads(requests.get('https://www.cloudflarestatus.com/api/v2/components.json').text)

    grouped_list = {}

    for item in components_json['components']:
        if item['group_id']:
            group_id = item['group_id']
            if group_id not in grouped_list:
                grouped_list[group_id] = dict({'child': {}})
            my_id = item['id']
            my_name = item['name']
            grouped_list[group_id]['child'][my_id] = my_name
        else:
            my_id = item['id']
            my_name = item['name']
            if my_id not in grouped_list:
                grouped_list[my_id] = dict({'child': {}})
            grouped_list[my_id]['name'] = my_name

    to_be_deleted_keys = set()

    for key in grouped_list.keys():
        if grouped_list[key]['name'].find('Cloudflare') != -1:
            to_be_deleted_keys.add(key)

    for key in to_be_deleted_keys:
        del grouped_list[key]

    for region in grouped_list.values():
        region_name = region['name']
        for v in region['child'].values():
            v = v.strip()
            v = unicodedata.normalize("NFKD", v)
            regex = re.search(r'^([\s\S]+?)( +-)? +\(([A-Z]{3})\)', v)
            name = regex.group(1)
            colo = regex.group(3)
            data[colo] = {
                'name': name,
                'region': region_name
            }
            regex2 = re.search(r'^([\s\S]+), ([\s\S]+)', name)
            if regex2:
                data[colo].update({
                    'city': regex2.group(1),
                    'country': regex2.group(2)
                })
                if regex2.group(2) in country_codes_inv:
                    data[colo]['cca2'] = country_codes_inv[regex2.group(2)]


    # speed.cloudflare.com for locations
    # format: json
    speed_locations = json.loads(get('https://speed.cloudflare.com/locations', referer='https://speed.cloudflare.com/').text)
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

    # Test
    sys.exit(1)

    if len(match_data) == 0 or len(location_data) == 0:
        print('Error: Colo data is empty')
        sys.exit(1)

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
