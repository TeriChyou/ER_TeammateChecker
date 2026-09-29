import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from er_checker.api import ApiError, Client, NoRedirect, dak_url, parse_names, recent_games, summary


def response(payload):
    return io.StringIO(json.dumps(payload))


class ApiTests(unittest.TestCase):
    def test_names_and_urls(self):
        self.assertEqual(parse_names('玩家甲\n玩家乙，玩家甲'), ['玩家甲', '玩家乙'])
        for invalid in ['', 'a,b,c', 'a\tb']:
            with self.assertRaises(ValueError):
                parse_names(invalid)
        self.assertEqual(dak_url('a/b?'), 'https://dak.gg/er/players/a%2Fb%3F')

    def test_recent_filter_and_order(self):
        games = [{'gameId': i, 'matchingMode': 3, 'matchingTeamMode': 3} for i in range(30)]
        games += [{'gameId': 40, 'matchingMode': 2, 'matchingTeamMode': 3}]
        selected = recent_games(games, 3)
        self.assertEqual(len(selected), 20)
        self.assertEqual([selected[0]['gameId'], selected[-1]['gameId']], [29, 10])

    def test_summary_missing_is_not_zero(self):
        self.assertIsNone(summary([])['win_rate'])
        result = summary([{'gameRank': 1, 'playerKill': 0}, {'gameRank': 3}, {}])
        self.assertEqual(result['win_rate'], 50)
        self.assertEqual(result['kills'], 0)
        self.assertIsNone(result['assists'])

    def test_uid_endpoints_and_partial_result(self):
        opener = Mock()
        opener.open.side_effect = [response({'code': 200, 'user': {'uid': 'abc/123'}}),
                                   response({'code': 200, 'userGames': []}),
                                   response({'code': 404})]
        result = Client('secret', opener, interval=0).lookup('隊友', 3, 33)
        urls = [c.args[0].full_url for c in opener.open.call_args_list]
        self.assertIn('query=%E9%9A%8A%E5%8F%8B', urls[0])
        self.assertTrue(urls[1].endswith('/v1/user/games/uid/abc%2F123'))
        self.assertTrue(urls[2].endswith('/v2/user/stats/uid/abc%2F123/33/3'))
        self.assertTrue(result['warning'])
        self.assertEqual(result['games'], [])
        self.assertEqual(opener.open.call_args.args[0].get_header('X-api-key'), 'secret')

    def test_no_key_no_request(self):
        opener = Mock()
        with self.assertRaises(ApiError):
            Client('', opener).lookup('a')
        opener.open.assert_not_called()

    def test_network_and_payload_failures(self):
        for failure in [HTTPError('url', 429, 'secret', {}, None), URLError('secret'), TimeoutError('secret')]:
            opener = Mock()
            opener.open.side_effect = failure
            with self.assertRaises(ApiError) as caught:
                Client('secret', opener, interval=0).get('/test')
            self.assertNotIn('secret', str(caught.exception))
        for payload in [{'code': 403}, [], {'code': 200, 'user': {'userNum': 1}}]:
            opener = Mock()
            opener.open.return_value = response(payload)
            with self.assertRaises(ApiError):
                Client('key', opener, interval=0).lookup('a')

    def test_redirect_denied(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere'))

    def test_stats_selects_requested_mode_and_season(self):
        opener = Mock()
        wanted = {'matchingTeamMode': 3, 'matchingMode': 3, 'seasonId': 33, 'totalGames': 10}
        opener.open.side_effect = [response({'code': 200, 'user': {'uid': 'abc'}}),
                                   response({'code': 200, 'userGames': []}),
                                   response({'code': 200, 'userStats': [dict(wanted, seasonId=32), wanted]})]
        self.assertEqual(Client('key', opener, interval=0).lookup('a', 3, 33)['stats'], wanted)


if __name__ == '__main__':
    unittest.main()
