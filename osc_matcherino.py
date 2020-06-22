import json
import re

import requests


def get_matcherino_data(matches, ttype):
    codes_used = ''
    matcherino_status = 'not found'
    matcherino = re.findall('https://matcherino.com/tournaments/[0-9]+', matches['description'])
    if matcherino:
        matcherino = matcherino[0].split('/')[-1]
        r = requests.get('https://matcherino.com/__api/bounties?id=' + matcherino)
        json_data = json.loads(r.text)
        codes_used = str(json_data['transactions']).count('coupon:use')
        total_prize = json_data['balance'] / 10 ** 2
        payouts = []
        payouts_dict = {}
        matcherino_status = 'pending'
        if json_data['payouts']:
            if 'teams' in json_data['payouts'][0].keys():
                matcherino_status = 'paid'
            for payout in json_data['payouts']:
                if payout['strategy'] == 'percentage':
                    prize = json_data['balance'] * payout['payout'] / 10 ** 6
                else:
                    prize = payout['payout'] / 10 ** 2
                if len(payout.get('teams', '')) > 1:
                    prize /= len(payout['teams'])
                payouts.append(prize)
            payouts = sorted(payouts, reverse=True)
            payouts_dict = dict(zip(range(1, len(payouts) + 1), payouts))

    elif ttype == 'kfc':
        payouts_dict = {1: 200, 2: 100, 3: 50}
        total_prize = 400
    elif ttype == 'blazingmay':
        payouts_dict = {1: 100, 2: 16}
        total_prize = 116
    else:
        payouts_dict = {}
        total_prize = 0
    return payouts_dict, codes_used, total_prize, matcherino_status