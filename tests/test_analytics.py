import unittest
from er_checker.analytics import character_stats, recent_analysis, sorted_rows


class AnalyticsTests(unittest.TestCase):
    def test_signed_rp_sample_threshold_and_numeric_fields(self):
        rows = character_stats([
            {'name': 'A', 'games': '2', 'rp': '100', 'rpDirection': 'up-arrow'},
            {'name': 'B', 'games': '3', 'rp': '100', 'rpDirection': 'down-arrow',
             'damage': '23,657', 'winRate': '1 (33.3%)'},
            {'name': 'C', 'games': '75', 'rp': '1,400', 'rpDirection': 'up-arrow'},
            {'name': 'D', 'games': '3', 'rp': '0'},
        ])
        self.assertIsNone(rows[0]['average_rp'])
        self.assertAlmostEqual(rows[1]['average_rp'], -100 / 3)
        self.assertEqual(rows[1]['damage'], 23657)
        self.assertEqual(rows[1]['win_rate'], 33.3)
        self.assertAlmostEqual(rows[2]['average_rp'], 1400 / 75)
        self.assertEqual(rows[3]['average_rp'], 0)

    def test_missing_sign_or_malformed_data_is_unknown(self):
        for raw in [{'games': '3', 'rp': '50'}, {'games': 'bad', 'rp': '+50'},
                    {'games': '3', 'rp': 'RP 50'}, {'games': '0', 'rp': '0'}]:
            self.assertIsNone(character_stats([raw])[0]['average_rp'])

    def test_sort_numbers_and_keep_unknown_last(self):
        rows = [{'rp': None}, {'rp': 1000}, {'rp': -200}, {'rp': 9}]
        self.assertEqual([r['rp'] for r in sorted_rows(rows, 'rp')], [-200, 9, 1000, None])
        self.assertEqual([r['rp'] for r in sorted_rows(rows, 'rp', True)], [1000, 9, -200, None])

    def test_all_modes_include_nonstandard_combat_and_no_premade_guess(self):
        rows = [{'mode': '排位', 'teammates': ['same'], 'badge': 'T 2'}] * 12
        rows += [{'mode': '一般', 'teammates': ['same']}] * 6
        rows += [{'mode': '鈷協議', 'combatLabel': 'K / D / A'}, {}]
        rows += [{'mode': 'should not count'}]
        result = recent_analysis(rows)
        self.assertEqual(result['count'], 20)
        self.assertEqual(result['modes'], {'排位': 12, '一般': 6, '鈷協議': 1, '未辨識模式': 1})
        self.assertIn('無法判定', result['premade'])
        self.assertEqual(recent_analysis([])['count'], 0)


if __name__ == '__main__':
    unittest.main()
