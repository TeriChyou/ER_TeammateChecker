import argparse
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from .api import ApiError, Client, dak_url, demo_result, parse_names, summary
from .hotkeys import Hotkeys
from .ocr_panel import OcrPanel
from .capture import enable_dpi_awareness


class App:
    def __init__(self, root, demo=False):
        self.root, self.demo = root, demo
        self.events = queue.Queue()
        self.busy = False
        self.closed = False
        self.cancel = threading.Event()
        self.hotkeys = Hotkeys()
        root.title('ER 隊友戰績' + (' — 示範模式' if demo else ''))
        root.geometry('980x820')
        root.minsize(900, 700)
        self.key = tk.StringVar(value=os.getenv('ER_API_KEY', ''))
        self.names = tk.StringVar(value='示範隊友一, 示範隊友二' if demo else '')
        self.season = tk.StringVar()
        self.mode = tk.StringVar(value='積分')
        self.provider = tk.StringVar(value='DAK.GG（免 Key）')
        self.topmost = tk.BooleanVar(value=False)
        self.hotkey_enabled = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='先框選兩位隊友的名稱；也可匯入截圖，免輸入韓文。')
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='ER 隊友戰績', font=('Microsoft JhengHei UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='截圖辨識 → 自動比較多語候選 → DAK.GG 公開戰績').pack(anchor='w', pady=(0, 10))
        self.ocr = OcrPanel(self, frame)
        self.api_row = ttk.Frame(frame)
        row = self.api_row
        ttk.Label(row, text='API Key').pack(side='left')
        ttk.Entry(row, textvariable=self.key, show='●').pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(row, text='申請 Key', command=lambda: webbrowser.open('https://developer.eternalreturn.io/')).pack(side='left')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        ttk.Entry(row, textvariable=self.names).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='貼上 ID', command=self.paste).pack(side='left', padx=6)
        self.search = ttk.Button(row, text='查詢', command=self.lookup)
        self.search.pack(side='left')
        row = ttk.Frame(frame)
        row.pack(fill='x')
        ttk.Combobox(row, textvariable=self.mode, values=['積分', '一般'], state='readonly', width=6).pack(side='left')
        provider = ttk.Combobox(row, textvariable=self.provider, values=['DAK.GG（免 Key）', '官方 API'], state='readonly', width=19)
        provider.pack(side='left', padx=8)
        provider.bind('<<ComboboxSelected>>', lambda _: self.update_provider())
        ttk.Label(self.api_row, text=' API 賽季 ID').pack(side='left')
        ttk.Entry(self.api_row, textvariable=self.season, width=7).pack(side='left')
        ttk.Button(row, text='開啟 DAK.GG', command=self.open_dak).pack(side='right')
        ttk.Button(row, text='取消工作', command=self.cancel_job).pack(side='right', padx=6)
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        ttk.Checkbutton(row, text='置頂 overlay', variable=self.topmost,
                        command=lambda: root.attributes('-topmost', self.topmost.get())).pack(side='left')
        ttk.Checkbutton(row, text='啟用全域快捷鍵', variable=self.hotkey_enabled, command=self.toggle_hotkeys).pack(side='left', padx=12)
        ttk.Label(frame, textvariable=self.status, wraplength=740).pack(anchor='w', pady=(0, 8))
        self.tabs = ttk.Notebook(frame)
        self.tabs.pack(fill='both', expand=True)
        ttk.Label(frame, text='Ctrl+Alt+Q 截圖辨識｜Ctrl+Alt+E 顯示／隱藏（需勾選快捷鍵）\n截圖僅本機處理；不讀取遊戲程序。網站資料可能延遲。', wraplength=900).pack(anchor='w', pady=(8, 0))
        root.bind('<Return>', lambda event: self.lookup())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_timer = root.after(50, self.poll)

    def update_provider(self):
        if self.provider.get() == '官方 API':
            self.api_row.pack(fill='x', before=self.ocr.previews.master)
        else:
            self.api_row.pack_forget()

    def cancel_job(self):
        if self.busy:
            self.cancel.set()
            self.status.set('取消中…正在結束本次工作。')
        if self.ocr.picker:
            self.ocr.picker.finish(False)

    def clear_results(self):
        for tab in self.tabs.tabs():
            self.tabs.nametowidget(tab).destroy()

    def paste(self):
        try:
            self.names.set(', '.join(parse_names(self.root.clipboard_get())))
            self.status.set('已貼上，請確認 ID 後按查詢。')
        except (tk.TclError, ValueError) as exc:
            self.status.set(str(exc) if isinstance(exc, ValueError) else '剪貼簿沒有可用文字。')

    def open_dak(self):
        try:
            for name in parse_names(self.names.get()):
                webbrowser.open(dak_url(name))
        except ValueError as exc:
            self.status.set(str(exc))

    def toggle_hotkeys(self):
        if self.hotkey_enabled.get():
            self.status.set(self.hotkeys.enable())
            self.hotkey_enabled.set(bool(self.hotkeys.ids))
        else:
            self.hotkeys.close()
            self.status.set('全域快捷鍵已停用。')

    def lookup(self):
        if self.busy:
            return
        raw_season = self.season.get().strip()
        try:
            names = parse_names(self.names.get())
            official = self.provider.get() == '官方 API'
            season = int(raw_season) if raw_season and official else None
            mode = 3 if self.mode.get() == '積分' else 2
            if season is not None and (season < 0 or (mode == 3 and season == 0)):
                raise ValueError('積分賽季 ID 必須大於 0。')
            if mode == 2 and season not in (None, 0):
                raise ValueError('一般模式的 API 賽季 ID 請填 0 或留白。')
            if not self.demo and official and not self.key.get().strip():
                raise ValueError('請輸入 API Key，或直接開啟 DAK.GG。')
        except ValueError as exc:
            self.status.set(str(exc) if not raw_season or not str(exc).startswith('invalid literal') else '賽季 ID 必須為整數。')
            return
        self.busy = True
        self.cancel.clear()
        self.search.state(['disabled'])
        self.status.set('查詢中…')
        self.clear_results()
        if official or self.demo:
            client = Client(self.key.get())
            threading.Thread(target=self.worker, args=(client, names, mode, season), daemon=True).start()
        else:
            # Allow finally to close the isolated browser after the GUI closes.
            threading.Thread(target=self.dak_worker, args=(names, mode), daemon=False).start()

    def dak_worker(self, names, mode):
        from .dak import DakClient
        try:
            with DakClient(self.cancel) as client:
                for name in names:
                    if self.cancel.is_set():
                        break
                    try:
                        self.events.put(('result', client.lookup(name, mode)))
                    except ApiError as exc:
                        self.events.put(('error', {'name': name, 'error': str(exc)}))
        except Exception:
            self.events.put(('error', {'name': 'DAK.GG', 'error': '背景查詢未完成，請確認網路與安裝依賴。'}))
        finally:
            self.events.put(('done', None))

    def worker(self, client, names, mode, season):
        try:
            for name in names:
                if self.cancel.is_set():
                    break
                try:
                    result = demo_result(name, mode) if self.demo else client.lookup(name, mode, season)
                    self.events.put(('result', result))
                except ApiError as exc:
                    self.events.put(('error', {'name': name, 'error': str(exc)}))
                except Exception:
                    # Never print raw network exceptions or credentials.
                    self.events.put(('error', {'name': name, 'error': '資料格式異常，請確認 API 是否有變更。'}))
        finally:
            self.events.put(('done', None))

    def render(self, kind, result):
        frame = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(frame, text=result['name'])
        if kind == 'error':
            ttk.Label(frame, text=result['error'], wraplength=850).pack(anchor='w')
            ttk.Button(frame, text='開啟網頁', command=lambda: webbrowser.open(dak_url(result['name']))).pack(anchor='w', pady=8)
            return
        if result.get('source') == 'dak':
            self.render_dak(frame, result)
            return
        games = result['games']
        stats = summary(games)
        val = lambda v: '—' if v is None else str(v)
        win = '—' if stats['win_rate'] is None else f"{stats['win_rate']:.1f}%"
        ttk.Label(frame, text=f"最近 {stats['count']} 場（三人隊） | 勝率 {win} | 平均名次 {val(stats['average_rank'])}").pack(anchor='w')
        ttk.Label(frame, text=f"平均擊殺 {val(stats['kills'])} | 平均助攻 {val(stats['assists'])}").pack(anchor='w')
        chars = '、'.join(f'#{code}（{count} 場）' for code, count in stats['characters']) or '無資料'
        ttk.Label(frame, text='近期常用角色代碼：' + chars).pack(anchor='w')
        if result['stats']:
            s = result['stats']
            ttk.Label(frame, text=f"API 賽季 {s.get('seasonId', '—')} | 場次 {s.get('totalGames', '—')} | 勝場 {s.get('totalWins', '—')} | RP {s.get('mmr', '—') if s.get('matchingMode') == 3 else '不適用'}").pack(anchor='w')
        if result['warning']:
            ttk.Label(frame, text=result['warning'], foreground='#b45309', wraplength=700).pack(anchor='w')
        if not games:
            ttk.Label(frame, text='API 回傳資料中沒有此模式的近期紀錄。').pack(anchor='w')
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill='both', expand=True, pady=(8, 0))
        tree = ttk.Treeview(table_frame, columns=('id', 'character', 'rank', 'kills', 'assists'), show='headings', height=8)
        for column, title in zip(tree['columns'], ['對局 ID', '角色代碼', '名次', '擊殺', '助攻']):
            tree.heading(column, text=title)
            tree.column(column, width=100, anchor='center')
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        for game in games:
            tree.insert('', 'end', values=[game.get(k, '—') for k in ('gameId', 'characterNum', 'gameRank', 'playerKill', 'playerAssistant')])

    def render_dak(self, frame, result):
        m = result['metrics']
        ttk.Label(frame, text=f"{result['season']} · 積分賽季摘要（網站預設） | {result['rp']} | {result['tier']}", font=('Microsoft JhengHei UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=f"場次 {m['total_games']}   勝率 {m['win_rate']}   平均名次 {m['rank']}   平均傷害 {m['damage']}").pack(anchor='w')
        ttk.Label(frame, text=f"平均擊殺 {m['kills']}   平均助攻 {m['assists']}   平均隊伍擊殺 {m['team_kills']}").pack(anchor='w')
        chars = '、'.join(f"{c['name']} {c['games']}（{c['winRate']}）" for c in result['characters'][:3]) or '網站未提供'
        ttk.Label(frame, text='常用角色：' + chars, wraplength=860).pack(anchor='w', pady=4)
        ttk.Label(frame, text=f"DAK.GG · {result['updated']} · 本機讀取 {result['fetched']}" + ('（兩分鐘內快取）' if result['cached'] else ''), foreground='#64748b').pack(anchor='w')
        mode = '積分' if result['mode'] == 3 else '一般'
        ttk.Label(frame, text=f"近期 {mode}：讀到 {len(result['games'])} 場；下方 TK 是隊伍擊殺，不是死亡次數。").pack(anchor='w', pady=(8, 4))
        if result.get('warning'):
            ttk.Label(frame, text=result['warning'], foreground='#b45309', wraplength=860).pack(anchor='w')
        area = ttk.Frame(frame)
        area.pack(fill='both', expand=True)
        columns = ('placement', 'character', 'team_kills', 'kills', 'assists', 'damage', 'time')
        tree = ttk.Treeview(area, columns=columns, show='headings', height=6)
        for col, title in zip(columns, ('名次', '角色', 'TK', '擊殺', '助攻', '傷害', '時間')):
            tree.heading(col, text=title)
            tree.column(col, width=95, anchor='center')
        scroll = ttk.Scrollbar(area, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        for game in result['games']:
            tree.insert('', 'end', values=[game[col] for col in columns])
        ttk.Button(frame, text='開啟此玩家完整網頁', command=lambda: webbrowser.open(result['url'])).pack(anchor='w', pady=(6, 0))

    def poll(self):
        for event in self.hotkeys.poll():
            if event == 1:
                if self.root.state() == 'withdrawn':
                    self.root.deiconify()
                else:
                    self.root.withdraw()
            elif event == 2:
                self.ocr.capture()
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'done':
                    self.busy = False
                    self.search.state(['!disabled'])
                    self.status.set(('已取消。' if self.cancel.is_set() else '查詢完成，請查看各隊友頁籤（錯誤亦顯示於頁籤）。') + ('【示範資料】' if self.demo else ''))
                elif kind == 'ocr':
                    if self.cancel.is_set():
                        self.ocr.release('已取消辨識。')
                    else:
                        self.ocr.complete(data)
                elif kind == 'ocr_error':
                    self.ocr.release(data)
                else:
                    if not self.cancel.is_set():
                        self.render(kind, data)
        except queue.Empty:
            pass
        self.poll_timer = self.root.after(50, self.poll)

    def close(self):
        self.closed = True
        self.cancel.set()
        self.hotkeys.close()
        self.root.after_cancel(self.poll_timer)
        if self.ocr.capture_timer:
            self.root.after_cancel(self.ocr.capture_timer)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='Eternal Return 隊友戰績查詢')
    parser.add_argument('--demo', action='store_true', help='離線示範，不發送 API 請求')
    args = parser.parse_args()
    enable_dpi_awareness()
    root = tk.Tk()
    App(root, demo=args.demo)
    root.mainloop()
