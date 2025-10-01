import asyncio
import aiohttp
from aiohttp import ClientSession
import time
from bs4 import BeautifulSoup
import io
import requests
import re 

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
    standings_dict = {}
    if standings_html:
        rows = standings_html.find_all('tr')
        for row in rows[1:]:  # Skip the header row
            cols = row.find_all('td')
            if len(cols) >= 2:
                rank = cols[0].text.strip()
                player = cols[1].text.strip()
                standings_dict[player] = {'Rank': rank}
    return standings_dict

def convert_battlefy_url(original_url):
    """
    Converts a Battlefy tournament bracket URL to its embed URL format.

    Args:
        original_url (str): The original Battlefy URL in the format
                            'https://battlefy.com/{org_slug}/{tournament_slug}/{tournament_id}/stage/{stage_id}/bracket/'.

    Returns:
        str: The converted embed URL in the format
             'https://battlefy.com/embeds/{tournament_id}/stage/{stage_id}?showFullscreen=true',
             or an error message if the URL format does not match.
    """
    # Regex to capture the tournament_id and stage_id from the original URL.
    # We look for two sequences of 24 hexadecimal characters separated by '/stage/'.
    match = re.search(r'([a-f0-9]{24})/stage/([a-f0-9]{24})', original_url)

    if match:
        tournament_id = match.group(1)
        stage_id = match.group(2)

        # Construct the new embed URL
        converted_url = f"https://battlefy.com/embeds/{tournament_id}/stage/{stage_id}"
        return converted_url
    else:
        return "Could not convert the URL. The format does not match the expected pattern."


def extract_code_from_list(item_list):
    """
    Extracts a 24-character hexadecimal code from a list of strings.

    Args:
        item_list (list): A list of strings where the code might be present.

    Returns:
        str or None: The extracted code if found, otherwise None.
    """
    # Regex to match a 24-character hexadecimal string.
    # [0-9a-f] matches any digit (0-9) or lowercase hex character (a-f).
    # {24} ensures it's exactly 24 characters long.
    hex_code_pattern = re.compile(r'^[0-9a-f]{24}$')

    for item in item_list:
        # Check if the current item contains the hex code pattern
        # The search() method is used to find matches of a pattern anywhere in the string.
        # However, since we want the *entire* item to be the code, we use fullmatch() or adjust the regex
        # If the code can be part of a larger string (e.g., 'match-container-6830fe93235a19002b5365fe'),
        # we would use re.search and then extract the group.
        # Based on the example, the code itself is the target, so we'll look for it as a standalone item,
        # or as a part of a string that *contains* the 24-char hex string.

        # If the code can be found as a standalone item in the list
        if hex_code_pattern.fullmatch(item):
            return item
        
        # If the code is embedded within another string (like 'match-container-6830fe93235a19002b5365fe')
        # We need a different regex to extract it from the larger string.
        # This regex looks for 24 hex characters preceded by '-' if it's in a string like 'prefix-code'.
        # Or just anywhere within the string.
        embedded_code_match = re.search(r'([0-9a-f]{24})', item)
        if embedded_code_match:
            # We found a 24-character hex string within the item
            # Return the first one found
            return embedded_code_match.group(1)
            
    return None 

def get_matches(master_url, tourney_url):
    converted_url = convert_battlefy_url(tourney_url)
    get_url = master_url.format(converted_url, '?showFullscreen=true', 'node')
    results = fetch(get_url)
    soup = BeautifulSoup(results, 'html.parser')
    matches_html = soup.findAll('g', class_='node')
    all_matches = {}
    for match in matches_html:
        try:
            matchNumber = match.find('text', class_='match-number').text.strip('#')
            matchContainer = extract_code_from_list(match.find('rect', class_='match-container').attrs['class'])        
            winner = match.find('text', class_='team-winner').text
            loser = match.find('text', class_='team-loser').text
            all_matches[matchNumber] = {'winner': winner, 'loser': loser, 'container': matchContainer}
        except:
            continue
    return all_matches


async def fetch_html(url: str, url_battlefy: str, session: ClientSession, **kwargs):
    """GET request wrapper to fetch page HTML.

    kwargs are passed to `session.request()`.
    """
    retry_count = 0
    while retry_count < 10:
        try:
            url_match = scrapo + '?url=' + url_battlefy + 'match/' + url + '&ele=team-name'
            resp = await session.request(method="GET", url=url_match, **kwargs)
            resp.raise_for_status()
            html = await resp.text()
            return html, resp.status
        except Exception as e:
            print(f"Error fetching {url_match}: {e}. Retrying in 1 second.")
            retry_count += 1
            await asyncio.sleep(1)

    return "", 500 # Return empty string and 500 status after retries fail
async def parse(url: str, url_battlefy: str, session: ClientSession, **kwargs):
    """Find HREFs in the HTML of `url`."""

    html, stat = await fetch_html(url, url_battlefy, session=session, **kwargs)
    soupmd = BeautifulSoup(html, 'html.parser')
    if 'Error loading results' in soupmd:
        stat = 400
    match_detail = soupmd.findAll('i', class_='fa-ban')
    return match_detail, stat


async def write_one(all_matches: dict, key: int, value: dict, url_battlefy: str, progress_callback=None, **kwargs):
    """Write the found HREFs from `url` to `file`."""
    res, stat = await parse(value['container'], url_battlefy, **kwargs)
    all_matches[key]['walkover'] = False
    all_matches[key]['status'] = False
    if res and stat == 200:
        all_matches[key]['walkover'] = True
    elif stat != 200:
        all_matches[key]['status'] = True
    if progress_callback:
        await progress_callback()


async def bulk_crawl_and_write(all_matches: dict, url_battlefy: str, progress_callback=None):
    """Crawl & write concurrently to `file` for multiple `urls`."""
    connector = aiohttp.TCPConnector(limit=50)
    async with ClientSession(connector=connector) as session:
        tasks = []
        for key, value in all_matches.items():
            tasks.append(
                write_one(all_matches, key, value, url_battlefy, session=session, progress_callback=progress_callback)
            )
        await asyncio.gather(*tasks)

def get_full_player_name(scraped_name_field, player_dict):
    """
    Attempts to match a partial, scraped player name to the full name 
    in the player dictionary keys.

    Args:
        scraped_name_field (str): The full string from the winner/loser field                                    
        player_dict (dict): The dictionary of full player names.
    Returns:
        str or None: The full player name (key) if a match is found, otherwise None.
    """
    # 1. Clean the scraped name to get the partial player name
    # Split by the non-breaking space/flag delimiter '\xa0 \xa0'
    partial_name_with_ellipsis = scraped_name_field.split('\xa0 \xa0')[-1]

    # Remove the ellipsis '...' and any trailing '#' or spaces
    # We remove '#' just in case a scraped name *does* include it (e.g., if it's short)
    # We strip any spaces just to be safe.
    partial_name = partial_name_with_ellipsis.replace('...', '').split('#')[0].strip()
    if partial_name in player_dict.keys():
        return player_dict[partial_name]
    else:
        for full_name in player_dict.keys():
            if full_name.startswith(partial_name):
                return player_dict[full_name ]
    return None  

async def get_battlefy(url_battlefy, ctx):
    url = scrapo + '?url={}{}&ele={}'

    if ctx:
        await ctx.send("Fetching standings...")
    standings_dict = get_standings(url, url_battlefy)
    if ctx:
        await ctx.send("Standings fetched. Fetching matches...")
    all_matches = get_matches(url, url_battlefy)

    name_dict = {}
    for name in standings_dict.keys():
        name_dict[name.split('#')[0]] = name

    total_matches = len(all_matches)
    processed_matches = 0

    async def update_progress():
        nonlocal processed_matches
        processed_matches += 1
        if ctx and processed_matches % 10 == 0 or processed_matches == total_matches: # Update every 10 matches or at the end
            await ctx.send(f"Processing matches: {processed_matches}/{total_matches} completed.")

    if ctx:
        await ctx.send(f"Found {total_matches} matches. Starting detailed match processing...")
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bulk_crawl_and_write(all_matches, url_battlefy, progress_callback=update_progress))

    for match_num, match_players in all_matches.items():
        if not match_players['walkover'] and match_players['loser'] != 'BYE':
            winner = get_full_player_name(match_players['winner'], name_dict)
            loser = get_full_player_name(match_players['loser'], name_dict)
            if 'Won' not in standings_dict[winner]:
                standings_dict[winner]['Played'] = 1
                standings_dict[winner]['Won'] = 1
            else:
                standings_dict[winner]['Played'] += 1
                standings_dict[winner]['Won'] += 1

            if 'Played' not in standings_dict[loser]:
                standings_dict[loser]['Played'] = 1
                standings_dict[loser]['Won'] = 0
            else:
                standings_dict[winner]['Played'] += 1
                
    walkover = []
    results = ''
    for key, value in standings_dict.items():
        if 'Played' in value.keys():
            results += (f'{key},{key.split("#")[0]},{value["Rank"]},{value["Played"]},{value["Won"]}\n')
        else:
            walkover.append(key)
    results += '\nWalkovers: '+str(walkover)
    return results
