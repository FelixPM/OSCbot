import json
import requests
import re


def get_aligulac(url, key):
    regex = re.compile('events/([0-9]*)')
    ali_id = regex.findall(url)[0]
    get_url = f'http://aligulac.com/api/v1/match/?apikey={key}&eventobj__uplink__parent={ali_id}&limit=300&format=json'
    tourney_json = requests.get(get_url)
    tourney = json.loads(tourney_json.text)
    matches = sorted(tourney['objects'], key=lambda x: x['id'], reverse=True)
    results = {}
    i = 0
    for match in matches:
        if match['sca'] > match['scb']:
            if match['pla']['tag'] in results.keys():
                results[match['pla']['tag']]['win'] += 1
                results[match['pla']['tag']]['played'] += 1
            else:
                results[match['pla']['tag']] = {'win': 1, 'played': 1, 'rank': i, 'race': match['pla']['race'],
                                                'country': match['pla']['country']}
                i += 1

            if match['plb']['tag'] in results.keys():
                results[match['plb']['tag']]['played'] += 1
            else:
                results[match['plb']['tag']] = {'win': 0, 'played': 1, 'rank': i, 'race': match['plb']['race'],
                                                'country': match['plb']['country']}
                i += 1
        else:
            if match['plb']['tag'] in results.keys():
                results[match['plb']['tag']]['win'] += 1
                results[match['plb']['tag']]['played'] += 1
            else:
                results[match['plb']['tag']] = {'win': 1, 'played': 1, 'rank': i, 'race': match['plb']['race'],
                                                'country': match['plb']['country']}
                i += 1

            if match['pla']['tag'] in results.keys():
                results[match['pla']['tag']]['played'] += 1
            else:
                results[match['pla']['tag']] = {'win': 0, 'played': 1, 'rank': i, 'race': match['pla']['race'],
                                                'country': match['pla']['country']}
                i += 1
    data = '```'
    for item in results.items():
        data += ',' + item[0].strip() + ',,' + str(item[1]['played']) + ',' + str(item[1]['win']) + '\n'
    return data+'```'
