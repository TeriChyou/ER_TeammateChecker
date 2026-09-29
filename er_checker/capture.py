"""Normal desktop pixels only. No game handles, hooks, or graphics injection."""
import ctypes
import json
import os
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab, ImageTk

CONFIG = Path(__file__).resolve().parents[1] / '.local/regions.json'


def enable_dpi_awareness():
    if os.name == 'nt':
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass


def desktop_bounds():
    if os.name != 'nt':
        raise ValueError('螢幕框選目前只支援 Windows；其他系統可使用匯入截圖。')
    api = ctypes.windll.user32
    return tuple(api.GetSystemMetrics(i) for i in (76, 77, 78, 79))


def valid_regions(regions, bounds):
    if not isinstance(regions, list) or not 1 <= len(regions) <= 2:
        return False
    x, y, w, h = bounds
    for r in regions:
        if not isinstance(r, (tuple, list)) or len(r) != 4 or any(type(v) is not int for v in r):
            return False
        l, t, right, bottom = r
        if not (x <= l < right <= x + w and y <= t < bottom <= y + h and
                8 <= right - l <= 2500 and 8 <= bottom - t <= 500):
            return False
    return True


def load_regions(bounds, path=CONFIG):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('bounds') == list(bounds) and valid_regions(data.get('regions'), bounds):
            return data['regions']
    except (OSError, ValueError, AttributeError):
        pass
    return []


def save_regions(regions, bounds, path=CONFIG):
    if not valid_regions(regions, bounds):
        raise ValueError('框選範圍不合法。')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'bounds': bounds, 'regions': regions}), encoding='utf-8')


def capture_regions(regions, bounds):
    if tuple(bounds) != desktop_bounds() or not valid_regions(regions, bounds):
        raise ValueError('顯示器配置已改變或尚未設定，請重新框選。')
    # Capture only requested areas during routine lookup; never save pixels.
    return [ImageGrab.grab(bbox=tuple(region), all_screens=True) for region in regions]


class RegionPicker:
    """Select 1–2 rectangles on a frozen screenshot; callback receives crops."""
    def __init__(self, root, image, callback, origin=(0, 0), desktop=False):
        self.image, self.callback, self.origin = image, callback, origin
        self.regions = []
        self.start = None
        self.rectangle = None
        self.finished = False
        self.window = tk.Toplevel(root)
        self.window.title('框選隊友名稱：拖曳 1–2 格，Enter 完成，Esc 取消')
        self.window.attributes('-topmost', True)
        if desktop:
            self.scale = 1.0
            self.window.overrideredirect(True)
            self.window.geometry(f'{image.width}x{image.height}+0+0')
        else:
            self.scale = min(1.0, (root.winfo_screenwidth() - 100) / image.width,
                             (root.winfo_screenheight() - 180) / image.height)
        shown = image.resize((round(image.width * self.scale), round(image.height * self.scale)))
        self.photo = ImageTk.PhotoImage(shown)
        self.canvas = tk.Canvas(self.window, width=shown.width, height=shown.height, highlightthickness=0, cursor='crosshair')
        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.hint = self.canvas.create_text(16, 16, anchor='nw', fill='#ffffff', font=('Microsoft JhengHei UI', 14, 'bold'),
                                            text='拖曳框住一行名稱（最多兩位）｜Enter 完成｜右鍵重選｜Esc 取消')
        box = self.canvas.bbox(self.hint)
        self.canvas.create_rectangle(box[0]-8, box[1]-6, box[2]+8, box[3]+6, fill='#182235', outline='', tags='hint-bg')
        self.canvas.tag_raise(self.hint)
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.bind('<Button-3>', self.reset)
        self.window.bind('<Return>', lambda _: self.finish(True))
        self.window.bind('<Escape>', lambda _: self.finish(False))
        self.window.protocol('WM_DELETE_WINDOW', lambda: self.finish(False))
        self.window.update_idletasks()
        if desktop and os.name == 'nt':
            api = ctypes.windll.user32
            api.GetParent.argtypes = [ctypes.c_void_p]
            api.GetParent.restype = ctypes.c_void_p
            api.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            hwnd = api.GetParent(self.window.winfo_id())
            api.SetWindowPos(hwnd, ctypes.c_void_p(-1), origin[0], origin[1], image.width, image.height, 0x0040)
        self.window.focus_force()
        self.window.grab_set()

    def press(self, event):
        if len(self.regions) >= 2:
            return
        self.start = (event.x, event.y)
        self.rectangle = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='#38e8b5', width=3, tags='selection')

    def drag(self, event):
        if self.start:
            self.canvas.coords(self.rectangle, *self.start, event.x, event.y)

    def release(self, event):
        if not self.start:
            return
        x0, y0 = self.start
        self.start = None
        region = [round(min(x0, event.x) / self.scale), round(min(y0, event.y) / self.scale),
                  round(max(x0, event.x) / self.scale), round(max(y0, event.y) / self.scale)]
        if not valid_regions([region], (0, 0, self.image.width, self.image.height)):
            self.canvas.delete(self.rectangle)
            return
        self.regions.append(region)

    def reset(self, event=None):
        self.regions.clear()
        self.start = None
        self.canvas.delete('selection')

    def finish(self, accept):
        if self.finished or (accept and not self.regions):
            return
        self.finished = True
        self.window.grab_release()
        self.window.destroy()
        if accept:
            crops = [self.image.crop(r) for r in self.regions]
            absolute = [[r[0]+self.origin[0], r[1]+self.origin[1], r[2]+self.origin[0], r[3]+self.origin[1]] for r in self.regions]
            self.callback(absolute, crops)
        else:
            self.callback(None, None)
