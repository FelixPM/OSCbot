import json
import re
from math import floor, log
from urllib.parse import urlparse

import challonge
import pytz

from osc_matcherino import get_matcherino_data


def get_tourney_points(ttype, OSC_points_dict, hold_third_place_match, tournament_type):
    if hold_third_place_match or tournament_type == 'double elimination':
        points_dict = OSC_points_dict['DE'].get(ttype, {})
    else:
        points_dict = OSC_points_dict['SE'].get(ttype, {})
    return points_dict


def get_challonge_data(name, user, key):
    challonge.set_credentials(user, key)
    matches = challonge.tournaments.show(name, include_participants=1, include_matches=1)
    return matches


def get_players(url, user, key):
    name, ttype = get_tourney_names(url)
    matches = get_challonge_data(name, user, key)
    challonge_players = [player['participant']['challonge_username'] for player in matches['participants'] if
                         player['participant']['checked_in']]
    returnstring = ''
    for player in challonge_players:
        returnstring += player + '\n'
    return (returnstring)


def get_tourney_names(tourney):
    tourney_input = urlparse(tourney)
    ttype = ''
    if '/' in tourney_input.path:
        name = tourney_input.path.split('/')[1]
    else:
        name = tourney_input.path
    if len(tourney_input.netloc) > 13:
        domain = tourney_input.netloc.split('.')[0]
        name = domain + '-' + name
        if domain == 'scvrush':
            ttype = domain
    if re.search("\d", name) and ttype != 'scvrush':
        ttype = re.findall(r"(\w+?)(\d+)", name)[0][0].lower()

    return name, ttype


def get_player_list(matches, points_dict, payouts_dict):
    player_list = {}
    for participant in matches['participants']:
        username = participant['participant']['challonge_username']
        if participant['participant']['username'] != participant['participant']['display_name']:
            display_name = participant['participant']['display_name']
        else:
            display_name = ''
        final_rank = participant['participant']['final_rank']
        player_list[participant['participant']['id']] = {'username': username,
                                                         'display_name': display_name,
                                                         'rank': final_rank,
                                                         'osc': points_dict.get(str(final_rank), ''),
                                                         'usdprize': payouts_dict.get(final_rank, ''),
                                                         'series played': 0,
                                                         'series won': 0}
    return player_list


def parse_tournament(player_list, list_matches, ttype, display, tournament_status, tournament_type,
                     points_dict, payouts_dict):
    forfeits = []
    rank = 1
    for match in list_matches:
        if match['winner_id']:
            forfeit = False
            for map in match['scores_csv'].split(','):
                if map:
                    maps = map.split('-')
                    if len(maps) > 2 or '99' in maps:
                        forfeit = True
                        break
            if not forfeit:
                player_list[match['winner_id']]['series played'] += 1
                player_list[match['winner_id']]['series won'] += 1
                player_list[match['loser_id']]['series played'] += 1

            else:
                forfeits.append(match['loser_id'])
            if tournament_status != 'complete' and tournament_type == 'single elimination':
                if rank == 1:
                    player_list[match['winner_id']]['rank'] = 1
                    player_list[match['winner_id']]['osc'] = points_dict.get('1', '')
                    player_list[match['winner_id']]['usdprize'] = payouts_dict.get(1, '')

                    player_list[match['loser_id']]['rank'] = 2
                    player_list[match['loser_id']]['osc'] = points_dict.get('2', '')
                    player_list[match['loser_id']]['usdprize'] = payouts_dict.get(2, '')
                    rank += 2
                elif rank in points_dict.keys():
                    player_list[match['loser_id']]['rank'] = rank
                    player_list[match['loser_id']]['osc'] = points_dict.get(str(rank), '')
                    player_list[match['loser_id']]['usdprize'] = payouts_dict.get(rank, '')
                    rank += 1
                else:
                    rank_floor = int(pow(2, floor(log(rank - 0.5, 2))) + 1)
                    player_list[match['loser_id']]['rank'] = rank_floor
                    player_list[match['loser_id']]['osc'] = points_dict.get(str(rank_floor), '')
                    player_list[match['loser_id']]['usdprize'] = payouts_dict.get(rank_floor, '')
                    rank += 1

    deletes = []
    for key, value in player_list.items():
        if value['series played'] == 0 and key not in forfeits:
            deletes.append(key)
    print(display)
    if display != 'Include':
        for key in deletes:
            del player_list[key]
    if ttype != 'oscww' and display != 'Include':
        for key in set(forfeits):
            if player_list[key]['series played'] == 0:
                del player_list[key]


def get_ranking_data(url, user, key, display='False'):
    OSC_points_dict = json.load(open('OSC_points_dict.json', "r"))

    name, ttype = get_tourney_names(url)

    matches = get_challonge_data(name, user, key)

    started_at = matches['started_at'].astimezone(pytz.timezone("Asia/Seoul")).strftime("%d/%m/%Y")

    tournament_name = matches['name']

    tournament_status = matches['state']

    hold_third_place_match = matches['hold_third_place_match']

    tournament_type = matches['tournament_type']

    points_dict = get_tourney_points(ttype, OSC_points_dict, hold_third_place_match, tournament_type)

    payouts_dict, codes_used, total_prize, matcherino_status = get_matcherino_data(matches, ttype)

    list_matches = sorted(matches['matches'],
                          key=lambda k: k['match']['suggested_play_order'] if k['match']['suggested_play_order'] else 0,
                          reverse=True)

    list_matches = [item['match'] for item in list_matches]

    player_list = get_player_list(matches, points_dict, payouts_dict)

    parse_tournament(player_list, list_matches, ttype, display, tournament_status, tournament_type,
                     points_dict, payouts_dict)

    sep = ';'
    sep2 = '\n'
    returnstring = ''
    returnstring = returnstring + ("```")

    returnstring = returnstring + sep2 + (matches[
                                              'full_challonge_url'] + sep2 + 'chllng_stat=' + tournament_status + sep2 + 'mtchrn_stat=' + matcherino_status + sep2 + 'codes_used=' + str(
        codes_used) + sep2 + str(started_at) + sep2 + tournament_name + sep2 + str(total_prize))

    if display == 'True':
        returnstring = returnstring + sep2 + (
                    'DBname' + sep + 'display_name' + sep + 'username' + sep + 'rank' + sep + 'series played' + sep + 'series won' + sep + 'osc' + sep + 'usdprize')
        for key, player in sorted(player_list.items(), key=lambda k_v: k_v[1]['rank'] or ''):
            returnstring = returnstring + sep2 + (str(player['dbname'])
                                                  + sep + str(player['display_name'])
                                                  + sep + str(player['username'])
                                                  + sep + str(player['rank'])
                                                  + sep + str(player['series played'])
                                                  + sep + str(player['series won'])
                                                  + sep + str(player['osc'])
                                                  + sep + str(player['usdprize']))
        returnstring = returnstring + sep2 + ("```")
    else:
        sep = ','
        returnstring = returnstring + sep2 + (
                    'display_name' + sep + 'username' + sep + 'rank' + sep + 'series played' + sep + 'series won' + sep + 'osc' + sep + 'usdprize')
        for key, player in sorted(player_list.items(), key=lambda k_v: k_v[1]['rank'] or 999):
            returnstring = returnstring + sep2 + (str(player['display_name'])
                                                  + sep + str(player['username'])
                                                  + sep + str(player['rank'])
                                                  + sep + str(player['series played'])
                                                  + sep + str(player['series won'])
                                                  + sep + str(player['osc'])
                                                  + sep + str(player['usdprize']))

        returnstring = returnstring + sep2 + ("```")
    return returnstring