"""Conservative statistics from rendered DAK.GG tables."""
from collections import Counter
import re


def number(value):
    """Parse a whole numeric cell, never silently accept unrelated text."""
    value = str('' if value is None else value).replace(',', '').strip().rstrip('%').lstrip('#')
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value):
        return None
    return float(value)


def character_stats(rows):
    result = []
    for row in rows:
        count = number(re.sub(r'\s*(遊戲|Games?|게임)\s*$', '', row.get('games', ''), flags=re.I))
        rp = number(row.get('rp'))
        direction = row.get('rpDirection', '')
        if rp is not None and rp != 0:
            if direction == 'down-arrow':
                rp = -abs(rp)
            elif direction == 'up-arrow':
                rp = abs(rp)
            elif not str(row.get('rp', '')).strip().startswith(('+', '-')):
                rp = None  # Magnitude without a direction is not a signed RP value.
        win = re.search(r'([\d.,]+)%', row.get('winRate', ''))
        result.append({'name': row.get('name', '—'), 'games': count,
                       'win_rate': number(win[1]) if win else None, 'rp': rp,
                       'average_rp': rp / count if rp is not None and count is not None and count >= 3 else None,
                       'kills': number(row.get('kills')), 'damage': number(row.get('damage'))})
    return result


def recent_analysis(rows):
    # Count every visible card, including modes with a different combat layout.
    games = rows[:20]
    counts = Counter(row.get('mode') or '未辨識模式' for row in games)
    return {'count': len(games), 'modes': dict(counts),
            'premade': '無法判定：公開頁面未提供可驗證的單排／雙排／三排標記。'}


def sorted_rows(rows, column, descending=False):
    """Keep missing/insufficient samples last in both sorting directions."""
    known = [row for row in rows if row.get(column) is not None]
    missing = [row for row in rows if row.get(column) is None]
    return sorted(known, key=lambda row: row[column], reverse=descending) + missing
