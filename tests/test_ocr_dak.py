import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from er_checker.api import ApiError
from er_checker.ocr import parse_tsv, normalize_name, Candidate, confident_choice
from er_checker.capture import valid_regions, load_regions, save_regions
from er_checker.dak import parse_snapshot, DakClient, CACHE


def snapshot():
    return {'name': '페이블', 'body': 'profile', 'metrics': {'勝率': '24.1%', '遊戲場數': '357'},
            'games': [{'header': '#1\n排位\n25:10\n4分前', 'combat': '15\n/\n10\n/\n3',
                       'combatLabel': 'TK / K / A', 'character': '莉央', 'damage': '31,245'}]}


class OcrAndCaptureTests(unittest.TestCase):
    def test_ambiguous_candidates_need_review(self):
        self.assertTrue(confident_choice([Candidate('페이블', 97, '韓'), Candidate('other', 60, '英')]))
        self.assertFalse(confident_choice([Candidate('abc', 90, '英'), Candidate('aBc', 89, '英')]))
        self.assertFalse(confident_choice([]))

    def test_unicode_and_tsv(self):
        self.assertEqual(normalize_name(' 페 이 블\u200b '), '페이블')
        tsv = 'level\tconf\ttext\n5\t96\t페\n5\t90\t이블\n1\t-1\t\n'
        self.assertEqual(parse_tsv(tsv), ('페이블', 92.0))
        self.assertIsNone(parse_tsv('conf\ttext\n-1\t?\n'))

    def test_negative_monitor_and_config(self):
        bounds = (-1920, 0, 3840, 1080)
        regions = [[-1900, 100, -1600, 140], [100, 200, 400, 245]]
        self.assertTrue(valid_regions(regions, bounds))
        self.assertFalse(valid_regions([[0, 0, 1920, 1080]], bounds))
        self.assertFalse(valid_regions([[0, 0, 2, 2]], bounds))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'regions.json'
            save_regions(regions, bounds, path)
            self.assertEqual(load_regions(bounds, path), regions)
            self.assertEqual(load_regions((0, 0, 1920, 1080), path), [])
            path.write_text('broken', encoding='utf-8')
            self.assertEqual(load_regions(bounds, path), [])


class DakTests(unittest.TestCase):
    def test_additional_pages_validate_access_identity_and_scope(self):
        client = DakClient()
        client.allowed = Mock()
        url = 'https://dak.gg/er/players/test?gameMode=ALL'
        page = Mock(url=url)
        page.goto.return_value.status = 200
        page.evaluate.return_value = {'name': 'test', 'games': [{'mode': '一般'}]}
        with patch('er_checker.dak.time.sleep'):
            self.assertEqual(client.read_page(page, url, 'test')['games'][0]['mode'], '一般')
            client.allowed.assert_called_with(url)
            for code in (403, 429, 500):
                page.goto.return_value.status = code
                with self.assertRaises(ApiError):
                    client.read_page(page, url, 'test')
            page.goto.return_value.status = 200
            for snapshot_value in ({'name': 'other', 'games': [{}]}, {'body': 'captcha'}):
                page.evaluate.return_value = snapshot_value
                with self.assertRaises(ApiError):
                    client.read_page(page, url, 'test')
            page.url = url.replace('ALL', 'RANK')
            with self.assertRaises(ApiError):
                client.read_page(page, url, 'test')
            with self.assertRaises(ApiError):
                client.read_page(page, 'https://dak.gg/er/players/test/character', 'test', characters=True)

    def test_tk_is_not_deaths(self):
        result = parse_snapshot(snapshot(), '페이블', 3)
        game = result['games'][0]
        self.assertEqual((game['team_kills'], game['kills'], game['assists']), (15, 10, 3))
        self.assertEqual(result['metrics']['total_games'], '357')
        self.assertEqual(result['metrics']['damage'], '—')

    def test_identity_and_challenge(self):
        for value in [dict(snapshot(), name='other'), dict(snapshot(), body='Verify you are human')]:
            with self.assertRaises(ApiError):
                parse_snapshot(value, '페이블', 3)

    def test_no_false_empty_or_mode_mix(self):
        result = parse_snapshot(snapshot(), '페이블', 2)
        self.assertEqual(result['games'], [])
        self.assertTrue(result['warning'])
        with self.assertRaises(ApiError):
            parse_snapshot({'name': '페이블', 'body': 'loading'}, '페이블', 3)
        empty = parse_snapshot({'name': '페이블', 'recentEmpty': True}, '페이블', 3)
        self.assertEqual(empty['metrics']['win_rate'], '—')

    def test_no_kda_guess(self):
        value = snapshot()
        value['games'][0]['combatLabel'] = 'K / D / A'
        self.assertFalse(parse_snapshot(value, '페이블', 3)['games'])

    def test_cancel_before_network(self):
        stop = threading.Event()
        stop.set()
        with patch('er_checker.dak.urlopen') as request:
            with self.assertRaises(ApiError):
                DakClient(stop).lookup('test')
            request.assert_not_called()

    def test_robots_disallowed(self):
        from urllib.robotparser import RobotFileParser
        client = DakClient()
        client.robots = RobotFileParser()
        client.robots.parse(['User-agent: *', 'Disallow: /er/players'])
        with self.assertRaises(ApiError):
            client.allowed('https://dak.gg/er/players/test')

    def test_cache_skips_network(self):
        import time
        CACHE[('test', 3)] = (time.monotonic(), {'name': 'test', 'cached': False})
        try:
            with patch('er_checker.dak.urlopen') as request:
                self.assertTrue(DakClient().lookup('test')['cached'])
                request.assert_not_called()
        finally:
            CACHE.clear()


if __name__ == '__main__':
    unittest.main()
