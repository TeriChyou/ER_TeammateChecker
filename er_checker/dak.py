"""Low-volume headless reads of public DAK.GG player pages."""
from collections import OrderedDict
from contextlib import suppress
from datetime import datetime
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from .api import ApiError, dak_url

SCRIPT = Path(__file__).with_name('dak_dom.js').read_text(encoding='utf-8')
CACHE = OrderedDict()
FIELDS = {
    'win_rate': ('勝率', 'Win Rate', '승률', '勝率'),
    'total_games': ('遊戲場數', 'Total Games', 'Games', '게임 수', '게임수'),
    'kills': ('平均擊殺', 'Avg. Kills', 'Avg. Kill', '평균 킬'),
    'assists': ('平均助攻', 'Avg. Assists', 'Avg. Assist', '평균 어시스트'),
    'damage': ('平均傷害', 'Avg. Damage', '평균 피해량'),
    'rank': ('平均排名', 'Avg. Rank', '평균 순위'),
    'team_kills': ('平均TK', 'Avg. TK', '평균 TK'),
}


def same_name(left, right):
    return unicodedata.normalize('NFC', left).casefold() == unicodedata.normalize('NFC', right).casefold()


def parse_snapshot(snapshot, requested, mode):
    body = snapshot.get('body', '')
    if re.search(r'verify you are human|just a moment|access denied|checking your browser|captcha', body, re.I):
        raise ApiError('DAK.GG 要求驗證或拒絕自動存取，請按「開啟網頁」自行查看。')
    if not same_name(snapshot.get('name', ''), requested):
        raise ApiError('DAK.GG 找不到此名稱或回傳不同玩家，請從 OCR 候選選擇另一個名稱。')
    values = snapshot.get('metrics', {})
    metrics = {key: next((values[label] for label in labels if label in values), '—') for key, labels in FIELDS.items()}
    games = []
    expected = ('排位', 'Rank', 'Ranked', '랭크') if mode == 3 else ('一般', 'Normal', '일반')
    for raw in snapshot.get('games', []):
        header = [v.strip() for v in raw.get('header', '').splitlines() if v.strip()]
        if len(header) < 2 or header[1] not in expected:
            continue
        combat = re.fullmatch(r'\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*', raw.get('combat', ''))
        # DAK displays TK / K / A, not kills / deaths / assists.
        if not combat or re.sub(r'\s+', '', raw.get('combatLabel', '')) != 'TK/K/A':
            continue
        tkills, kills, assists = map(int, combat.groups())
        games.append({'placement': header[0], 'mode': header[1], 'time': header[-1],
                      'character': raw.get('character') or '—', 'team_kills': tkills,
                      'kills': kills, 'assists': assists, 'damage': raw.get('damage') or '—'})
    if not games and all(v == '—' for v in metrics.values()):
        if not snapshot.get('recentEmpty'):
            raise ApiError('DAK.GG 戰績尚未載入或頁面格式已變更，請稍後再試或開啟網頁。')
    warning = ''
    if not games:
        warning = '網站顯示此模式沒有近期紀錄。' if snapshot.get('recentEmpty') else '近期對局未載入或格式不符；目前僅顯示網站賽季摘要。'
    return {'source': 'dak', 'name': requested, 'url': dak_url(requested), 'mode': mode,
            'metrics': metrics, 'rp': snapshot.get('rp') or '—', 'tier': snapshot.get('tier') or '—',
            'season': snapshot.get('season') or '網站預設賽季', 'updated': snapshot.get('updated') or '網站未提供更新時間',
            'characters': snapshot.get('characters', []), 'games': games,
            'fetched': datetime.now().strftime('%H:%M:%S'), 'cached': False, 'warning': warning}


class DakClient:
    def __init__(self, cancel=None):
        self.cancel = cancel
        self.runtime = self.browser = None
        self.robots = None
        self.last_request = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.runtime:
                self.runtime.stop()

    def check_cancel(self):
        if self.cancel and self.cancel.is_set():
            raise ApiError('查詢已取消。')

    def allowed(self, url):
        if self.robots is None:
            try:
                req = Request('https://dak.gg/robots.txt', headers={'User-Agent': 'ER-TeammateChecker/0.2'})
                with urlopen(req, timeout=10) as response:
                    data = response.read(100000).decode('utf-8')
                self.robots = RobotFileParser()
                self.robots.parse(data.splitlines())
            except Exception:
                raise ApiError('無法確認 DAK.GG robots.txt，暫停背景查詢；可按「開啟網頁」。') from None
        if not self.robots.can_fetch('ER-TeammateChecker', url):
            raise ApiError('網站 robots.txt 不允許此頁面的自動查詢，請改用「開啟網頁」。')

    def lookup(self, name, mode=3, season=None):
        self.check_cancel()
        key = (name, mode)
        cached = CACHE.get(key)
        if cached and time.monotonic() - cached[0] < 120:
            return dict(cached[1], cached=True)
        url = dak_url(name) + ('?gameMode=RANK' if mode == 3 else '?gameMode=NORMAL')
        self.allowed(url)
        try:
            from playwright.sync_api import sync_playwright, Error as BrowserError
        except ImportError:
            raise ApiError('缺少瀏覽器依賴，請先執行 setup.ps1。') from None
        self.check_cancel()
        if self.cancel:
            self.cancel.wait(max(0, 3 - (time.monotonic() - self.last_request)))
        else:
            time.sleep(max(0, 3 - (time.monotonic() - self.last_request)))
        self.check_cancel()
        self.last_request = time.monotonic()
        context = None
        try:
            if self.runtime is None:
                self.runtime = sync_playwright().start()
                # Use an isolated Edge instance, never the user's signed-in profile.
                self.browser = self.runtime.chromium.launch(channel='msedge', headless=True)
            context = self.browser.new_context(locale='zh-TW', viewport={'width': 1280, 'height': 900})
            page = context.new_page()
            response = page.goto(url, wait_until='domcontentloaded', timeout=25000)
            if response and response.status in (403, 429):
                raise ApiError('DAK.GG 拒絕存取或限制流量，請稍後再試／開啟網頁。')
            if response and response.status == 404:
                raise ApiError('查無此玩家，請選擇另一個辨識候選名稱。')
            if urlparse(page.url).hostname != 'dak.gg':
                raise ApiError('DAK.GG 導向非預期網站，已停止查詢。')
            deadline = time.monotonic() + 20
            snapshot = {}
            while time.monotonic() < deadline:
                self.check_cancel()
                snapshot = page.evaluate(SCRIPT)
                body = snapshot.get('body', '')
                if re.search(r'verify you are human|just a moment|access denied|captcha', body, re.I):
                    raise ApiError('DAK.GG 要求驗證，請按「開啟網頁」自行查看。')
                # Wait for match cards too; season stats alone can arrive earlier.
                if snapshot.get('games') or snapshot.get('recentEmpty'):
                    break
                page.wait_for_timeout(400)
            result = parse_snapshot(snapshot, name, mode)
            result['url'] = url
            CACHE[key] = (time.monotonic(), result)
            CACHE.move_to_end(key)
            while len(CACHE) > 32:
                CACHE.popitem(last=False)
            return result
        except BrowserError:
            raise ApiError('背景瀏覽器啟動失敗、網路逾時或頁面載入失敗；請確認 Microsoft Edge 已安裝，或開啟網頁。') from None
        finally:
            if context:
                with suppress(BrowserError):
                    context.close()
