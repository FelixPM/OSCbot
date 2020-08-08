import asyncio
import aiohttp
from aiohttp import ClientSession
import pandas as pd
import time
from bs4 import BeautifulSoup
from async_retrying import retry
import requests

import nest_asyncio
nest_asyncio.apply()

scrapo = 'https://battlefy-scrapo-vfmikmpifa-uc.a.run.app/'

def fetch(url: str):
    """GET request wrapper to fetch page HTML.

    kwargs are passed to `session.request()`.
    """
    count = 0
    code = 100
    while count < 3 and code != 200:
        resp = requests.get(url)
        html = resp.text
        code = resp.status_code
        count += 1
    return html


def get_standings(master_url, tourney_url):
    get_url = master_url.format(tourney_url, 'results', 'text-muted')
    results = fetch(get_url)
    soup = BeautifulSoup(results, 'html.parser')
    standings_html = soup.find('table', class_='bfy-table')
    df = pd.read_html(str(standings_html))[0]
    df.drop('Unnamed: 1', axis=1, inplace=True)
    standings_dict = df.set_index('Player').to_dict(orient='index')
    return standings_dict


def get_matches(master_url, tourney_url):
    get_url = master_url.format(tourney_url, 'bracket', 'node')
    results = fetch(get_url)
    soup = BeautifulSoup(results, 'html.parser')
    matches_html = soup.findAll('g', class_='node')
    all_matches = {}
    for match in matches_html:
        try:
            matchNumber = match.find('text', class_='match-number').text.strip('#')
            matchContainer = match.find('rect', class_='match-container').attrs['class'][-1].split('-')[-1]
            winner = match.find('text', class_='team-winner').text
            loser = match.find('text', class_='team-loser').text
            all_matches[matchNumber] = {'winner': winner, 'loser': loser, 'container': matchContainer}
        except:
            continue
    return all_matches


@retry(attempts=10)
async def fetch_html(url: str, url_battlefy: str, session: ClientSession, **kwargs):
    """GET request wrapper to fetch page HTML.

    kwargs are passed to `session.request()`.
    """
    url_match = scrapo + '?url=' + url_battlefy + 'match/' + url + '&ele=team-name'
    resp = await session.request(method="GET", url=url_match, **kwargs)
    resp.raise_for_status()
    html = await resp.text()

    return html, resp.status


async def parse(url: str, url_battlefy: str, session: ClientSession, **kwargs):
    """Find HREFs in the HTML of `url`."""

    html, stat = await fetch_html(url, url_battlefy, session=session, **kwargs)
    soupmd = BeautifulSoup(html, 'html.parser')
    if 'Error loading results' in soupmd:
        stat = 400
    match_detail = soupmd.findAll('i', class_='fa-ban')
    return match_detail, stat


async def write_one(all_matches: dict, key: int, value: dict, url_battlefy: str, **kwargs):
    """Write the found HREFs from `url` to `file`."""
    res, stat = await parse(value['container'], url_battlefy, **kwargs)
    all_matches[key]['walkover'] = False
    all_matches[key]['status'] = False
    if res and stat == 200:
        all_matches[key]['walkover'] = True
    elif stat != 200:
        all_matches[key]['status'] = True


async def bulk_crawl_and_write(all_matches: dict, url_battlefy: str):
    """Crawl & write concurrently to `file` for multiple `urls`."""
    connector = aiohttp.TCPConnector(limit=50)
    async with ClientSession(connector=connector) as session:
        tasks = []
        for key, value in all_matches.items():
            tasks.append(
                write_one(all_matches, key, value, url_battlefy, session=session)
            )
        await asyncio.gather(*tasks)


def get_battlefy(url_battlefy):
    url = scrapo + '?url={}{}&ele={}'

    standings_dict = get_standings(url, url_battlefy)
    all_matches = get_matches(url, url_battlefy)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bulk_crawl_and_write(all_matches, url_battlefy))

    for match_num, match_players in all_matches.items():

        if not match_players['walkover'] and match_players['loser'] != 'BYE':
            if 'Won' not in standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]:
                standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]['Played'] = 1
                standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]['Won'] = 1
            else:
                standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]['Played'] += 1
                standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]['Won'] += 1

            if 'Played' not in standings_dict[match_players['loser'].split('\xa0 \xa0')[-1]]:
                standings_dict[match_players['loser'].split('\xa0 \xa0')[-1]]['Played'] = 1
                standings_dict[match_players['loser'].split('\xa0 \xa0')[-1]]['Won'] = 0
            else:
                standings_dict[match_players['winner'].split('\xa0 \xa0')[-1]]['Played'] += 1
    walkover = []
    results = ''
    for key, value in standings_dict.items():
        if 'Played' in value.keys():
            results += (f'{key},{key.split("#")[0]},{value["Rank"]},{value["Played"]},{value["Won"]}\n')
        else:
            walkover.append(key)
    results += '\nWalkovers: '+str(walkover)
    return results
