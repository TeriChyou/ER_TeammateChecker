"""Explicit developer smoke checks; --live reads public pages for one player."""
import argparse
import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
from er_checker.ocr import Recognizer

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
parser.add_argument('--normal', action='store_true', help='Also test Normal mode on the same public player')
args = parser.parse_args()
reader = Recognizer()
cases = [('페이블', 'malgun.ttf'), ('백수', 'malgun.ttf'), ('회광반조김현우', 'malgun.ttf'),
         ('Preme', 'malgun.ttf'), ('永恆輪迴', 'msjh.ttc'), ('テスト太郎', 'meiryo.ttc'), ('페이블123', 'malgun.ttf')]
for name, font in cases:
    image = Image.new('RGB', (400, 48), '#1c2333')
    draw = ImageDraw.Draw(image)
    draw.text((10, 3), name, font=ImageFont.truetype('C:/Windows/Fonts/' + font, 28), fill='white')
    choices = reader.recognize(image)
    print(json.dumps({'expected': name, 'candidates': [c.__dict__ for c in choices]}, ensure_ascii=False))
    assert choices and choices[0].name == name, name
if args.live:
    from er_checker.dak import DakClient
    with DakClient() as client:
        result = client.lookup('페이블')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert result['metrics']['win_rate'] != '—'
    assert result['games'], 'No live match cards parsed'
    assert result['character_stats'], 'No live character details parsed'
    assert result['recent_analysis']['count'] > 0, 'No all-mode match cards parsed'
    assert all(c['average_rp'] is None for c in result['character_stats'] if c['games'] is not None and c['games'] < 3)
    if args.normal:
        with DakClient() as client:
            normal = client.lookup('페이블', mode=2)
        print(json.dumps({'normal_games': len(normal['games']), 'warning': normal['warning'], 'season': normal['season']}, ensure_ascii=False))
        assert all(g['mode'] in ('一般', 'Normal', '일반') for g in normal['games'])
