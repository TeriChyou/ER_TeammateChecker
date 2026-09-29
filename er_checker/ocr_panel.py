import threading
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageGrab, ImageTk, UnidentifiedImageError
from .capture import RegionPicker, desktop_bounds, load_regions, save_regions, capture_regions
from .ocr import Recognizer, OcrError, LANGUAGES, confident_choice


class OcrPanel:
    def __init__(self, app, parent):
        self.app = app
        self.root = app.root
        self.picker = None
        self.capture_timer = None
        self.photos = []
        self.boxes = []
        self.candidates = []
        self.language = tk.StringVar(value=next(iter(LANGUAGES)))
        self.auto = tk.BooleanVar(value=True)
        try:
            self.bounds = desktop_bounds()
            self.regions = load_regions(self.bounds)
        except ValueError:
            self.bounds, self.regions = None, []
        frame = ttk.LabelFrame(parent, text='影像辨識隊友名稱', padding=8)
        frame.pack(fill='x', pady=(0, 8))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        ttk.Button(row, text='① 框選名稱位置', command=self.select_desktop).pack(side='left')
        ttk.Button(row, text='② 截圖辨識', command=self.capture).pack(side='left', padx=5)
        ttk.Button(row, text='匯入截圖', command=self.import_image).pack(side='left')
        ttk.Combobox(row, textvariable=self.language, values=list(LANGUAGES), state='readonly', width=21).pack(side='left', padx=8)
        ttk.Checkbutton(row, text='辨識清楚時自動查詢', variable=self.auto).pack(side='left')
        self.hint = ttk.Label(frame, text=f'已記住 {len(self.regions)} 個名稱位置；首次使用請框選。', wraplength=850)
        self.hint.pack(anchor='w', pady=4)
        self.previews = ttk.Frame(frame)
        self.previews.pack(fill='x')

    def reserve(self):
        if self.app.busy:
            return False
        self.app.busy = True
        self.app.cancel.clear()
        self.app.search.state(['disabled'])
        self.app.status.set('準備截圖…')
        return True

    def restore(self):
        if not self.app.closed:
            self.root.deiconify()
            self.root.lift()

    def release(self, message):
        self.app.busy = False
        self.app.search.state(['!disabled'])
        self.app.status.set(message)

    def select_desktop(self):
        if not self.reserve():
            return
        self.root.withdraw()
        self.capture_timer = self.root.after(300, self.open_desktop_picker)

    def open_desktop_picker(self):
        try:
            if self.app.closed:
                return
            if self.app.cancel.is_set():
                self.restore()
                self.release('已取消截圖。')
                return
            self.bounds = desktop_bounds()
            image = ImageGrab.grab(all_screens=True)
            if image.size != tuple(self.bounds[2:]):
                raise ValueError('截圖尺寸與顯示器不一致，請改用匯入截圖。')
            self.picker = RegionPicker(self.root, image, self.selected_desktop, self.bounds[:2], desktop=True)
        except (ValueError, OSError, tk.TclError) as exc:
            self.restore()
            self.release('無法框選：' + str(exc))

    def selected_desktop(self, regions, crops):
        self.picker = None
        self.restore()
        if regions is None:
            self.release('已取消框選，保留原有位置。')
            return
        self.regions = regions
        try:
            save_regions(regions, self.bounds)
            self.hint.configure(text=f'已記住 {len(regions)} 個名稱位置。下次按 Ctrl+Alt+Q 重新截圖辨識。')
        except OSError:
            self.hint.configure(text='位置僅保留於本次執行（無法寫入設定檔）。')
        self.start_ocr(crops)

    def capture(self):
        if not self.regions:
            self.select_desktop()
            return
        if not self.reserve():
            return
        self.root.withdraw()
        self.capture_timer = self.root.after(300, self.do_capture)

    def do_capture(self):
        if self.app.closed:
            return
        if self.app.cancel.is_set():
            self.restore()
            self.release('已取消截圖。')
            return
        try:
            crops = capture_regions(self.regions, self.bounds)
        except (ValueError, OSError) as exc:
            self.restore()
            self.release(str(exc))
            return
        self.restore()
        self.start_ocr(crops)

    def import_image(self):
        if self.app.busy:
            return
        path = filedialog.askopenfilename(title='選擇遊戲截圖', filetypes=[('截圖', '*.png *.jpg *.jpeg *.bmp *.webp')])
        if not path:
            return
        try:
            with Image.open(path) as source:
                if source.width * source.height > 40_000_000:
                    raise ValueError('圖片太大，請使用一般遊戲截圖。')
                image = source.convert('RGB')
            self.reserve()
            self.picker = RegionPicker(self.root, image, self.selected_file)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            self.release('無法開啟截圖：' + str(exc))

    def selected_file(self, regions, crops):
        self.picker = None
        if regions is None:
            self.release('已取消匯入。')
            return
        # File coordinates must never overwrite desktop capture coordinates.
        self.start_ocr(crops)

    def start_ocr(self, crops):
        self.app.names.set('')
        self.app.clear_results()
        self.candidates = []
        self.boxes = []
        self.photos = []
        for widget in self.previews.winfo_children():
            widget.destroy()
        for i, crop in enumerate(crops):
            tile = ttk.Frame(self.previews, padding=(0, 0, 12, 0))
            tile.pack(side='left', fill='x', expand=True)
            view = crop.copy()
            view.thumbnail((340, 60))
            photo = ImageTk.PhotoImage(view)
            self.photos.append(photo)
            ttk.Label(tile, image=photo).pack(anchor='w')
            ttk.Label(tile, text=f'隊友 {i+1} · 候選名稱').pack(anchor='w')
            combo = ttk.Combobox(tile, state='readonly', width=35)
            combo.pack(fill='x')
            combo.bind('<<ComboboxSelected>>', self.choose)
            self.boxes.append(combo)
        self.app.status.set('本機多語辨識中…會自動比較韓／英／中／日候選，無須切换輸入法。')
        language = self.language.get()
        self.auto_for_job = self.auto.get()
        threading.Thread(target=self.worker, args=(crops, language), daemon=True).start()

    def worker(self, crops, language):
        try:
            reader = Recognizer()
            candidates = [reader.recognize(crop, language, self.app.cancel) for crop in crops]
            self.app.events.put(('ocr', candidates))
        except OcrError as exc:
            self.app.events.put(('ocr_error', str(exc)))
        except Exception:
            self.app.events.put(('ocr_error', '辨識失敗，請重新框選完整的一行名稱。'))

    def choose(self, event=None):
        names = []
        for combo, candidates in zip(self.boxes, self.candidates):
            if combo.current() >= 0:
                names.append(candidates[combo.current()].name)
        self.app.names.set(', '.join(names))

    def complete(self, candidates):
        self.candidates = candidates
        for combo, choices in zip(self.boxes, candidates):
            combo.configure(values=[f'{c.name}   [{c.languages} · {c.confidence:.0f}]' for c in choices])
            if choices:
                combo.current(0)
        self.choose()
        self.release('辨識完成；可直接選其他候選名稱再查詢。分數為 OCR 參考值，不是正確率。')
        if not all(candidates):
            self.app.status.set('有名稱無法辨識，請縮小到單行名稱並重新截圖。已辨識的隊友仍可單獨查詢。')
        elif self.auto_for_job and not self.app.cancel.is_set() and all(confident_choice(c) for c in candidates):
            self.app.lookup()
        elif self.auto_for_job:
            self.app.status.set('辨識分數偏低或候選接近：請點選最像截圖的名稱，再按查詢；不需要打韓文。')
