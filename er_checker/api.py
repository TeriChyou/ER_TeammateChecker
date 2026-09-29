"""Official UID API only; no game process access or persistent player storage."""
import json
import socket
import time
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


class ApiError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    # Never forward the API key to another location.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def parse_names(text):
    names = list(dict.fromkeys(n.strip() for n in text.replace('，', ',').replace('\n', ',').split(',') if n.strip()))
    if not 1 <= len(names) <= 2:
        raise ValueError('請輸入 1–2 位隊友 ID，以逗號或換行分隔。')
    if any(len(n) > 64 or any(ord(c) < 32 for c in n) for n in names):
        raise ValueError('ID 長度或格式不正確。')
    return names


def dak_url(name):
    return 'https://dak.gg/er/players/' + quote(name, safe='')


def recent_games(games, mode):
    selected = [g for g in games if g.get('matchingMode') == mode and g.get('matchingTeamMode') == 3]
    return sorted(selected, key=lambda g: g.get('gameId', 0), reverse=True)[:20]


def summary(games):
    def average(field):
        values = [g[field] for g in games if isinstance(g.get(field), (int, float))]
        return round(sum(values) / len(values), 2) if values else None
    ranks = [g['gameRank'] for g in games if isinstance(g.get('gameRank'), (int, float)) and g['gameRank'] > 0]
    return {
        'count': len(games),
        'win_rate': sum(r == 1 for r in ranks) / len(ranks) * 100 if ranks else None,
        'average_rank': round(sum(ranks) / len(ranks), 2) if ranks else None,
        'kills': average('playerKill'), 'assists': average('playerAssistant'),
        'characters': Counter(g['characterNum'] for g in games if g.get('characterNum') is not None).most_common(3),
    }


class Client:
    def __init__(self, key, opener=None, interval=1.1):
        self.key = key.strip()
        self.opener = opener or build_opener(NoRedirect())
        self.interval = interval
        self.next_request = 0

    def get(self, path):
        if not self.key:
            raise ApiError('請先輸入官方 API Key；或使用 DAK.GG 按鈕。')
        time.sleep(max(0, self.next_request - time.monotonic()))
        self.next_request = time.monotonic() + self.interval
        request = Request('https://open-api.bser.io' + path, headers={'x-api-key': self.key, 'Accept': 'application/json'})
        try:
            with self.opener.open(request, timeout=12) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise ApiError(self.error_message(exc.code)) from None
        except (URLError, TimeoutError, socket.timeout, OSError):
            raise ApiError('網路連線失敗或逾時，請稍後再試。') from None
        except (ValueError, UnicodeError):
            raise ApiError('API 回應不是有效 JSON。') from None
        if not isinstance(payload, dict):
            raise ApiError('API 回應格式不符預期。')
        if payload.get('code') != 200:
            raise ApiError(self.error_message(payload.get('code')))
        return payload

    @staticmethod
    def error_message(code):
        return {400: 'API 參數不正確，請檢查 ID／賽季 ID。',
                401: 'API Key 無效或已過期。',
                403: 'API 拒絕存取：請確認 Key 權限或稍後再試（可能限流）。',
                404: '查無玩家或資料；請確認目前的遊戲暱稱。',
                429: '已達 API 查詢限制，請稍後再試。'}.get(code, 'API 暫時無法使用或回應格式已變更。')

    def lookup(self, name, mode=3, season=None):
        user = self.get('/v1/user/nickname?' + urlencode({'query': name})).get('user')
        if not isinstance(user, dict) or not isinstance(user.get('uid'), str) or not user['uid']:
            raise ApiError('API 未提供 UID；請確認暱稱或 API 版本。')
        uid = quote(user['uid'], safe='')
        games = self.get('/v1/user/games/uid/' + uid).get('userGames')
        if not isinstance(games, list) or any(not isinstance(g, dict) for g in games):
            raise ApiError('API 戰績格式不符預期。')
        result = {'name': name, 'games': recent_games(games, mode), 'stats': None, 'warning': ''}
        if season is not None:
            try:
                stats = self.get(f'/v2/user/stats/uid/{uid}/{season}/{mode}').get('userStats')
                if not isinstance(stats, list) or any(not isinstance(s, dict) for s in stats):
                    raise ApiError('API 賽季統計格式不符預期。')
                result['stats'] = next((s for s in stats if s.get('matchingTeamMode') == 3 and s.get('matchingMode') == mode and s.get('seasonId') == season), None)
                if result['stats'] is None:
                    result['warning'] = '指定賽季沒有對應統計。'
            except ApiError as exc:
                result['warning'] = str(exc)
        return result


def demo_result(name, mode):
    return {'name': name, 'stats': None, 'warning': '示範資料，並非此玩家真實戰績。',
            'games': [{'gameId': 1000 + i, 'matchingMode': mode, 'matchingTeamMode': 3,
                       'characterNum': [1, 2, 3][i % 3], 'gameRank': [1, 3, 5, 2][i % 4],
                       'playerKill': i % 6, 'playerAssistant': i % 8} for i in range(20, 0, -1)]}
