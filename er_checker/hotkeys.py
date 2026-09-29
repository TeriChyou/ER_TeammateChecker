"""Thread-local Windows RegisterHotKey; no keyboard hooks or key logging."""
import ctypes
import sys
import queue
import threading
import time
from ctypes import wintypes


class Hotkeys:
    def __init__(self):
        self.ids = []
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.thread = None
        self.user32 = None
        if sys.platform == 'win32':
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL
            self.user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
            self.user32.PeekMessageW.restype = wintypes.BOOL

    def enable(self):
        self.close()
        if self.user32 is None:
            return '全域快捷鍵只支援 Windows。'
        self.stop.clear()
        ready = threading.Event()
        self.thread = threading.Thread(target=self.run, args=(ready,), daemon=True)
        self.thread.start()
        ready.wait()
        if not self.ids:
            return '快捷鍵被占用或無法註冊，請使用視窗按鈕。'
        return 'Ctrl+Alt+E 顯示／隱藏；Ctrl+Alt+Q 查詢目前輸入。'

    def run(self, ready):
        # Tk consumes its own thread's messages. Keep WM_HOTKEY on a dedicated
        # message thread, and register/unregister on that same owning thread.
        for identifier, key in [(1, ord('E')), (2, ord('Q'))]:
            if not self.user32.RegisterHotKey(None, identifier, 0x4003, key):
                self.unregister()
                ready.set()
                return
            self.ids.append(identifier)
        ready.set()
        try:
            msg = wintypes.MSG()
            while not self.stop.is_set():
                while self.user32.PeekMessageW(ctypes.byref(msg), None, 0x0312, 0x0312, 1):
                    if msg.wParam in self.ids:
                        self.events.put(msg.wParam)
                time.sleep(0.02)
        finally:
            self.unregister()

    def poll(self):
        events = []
        try:
            while True:
                events.append(self.events.get_nowait())
        except queue.Empty:
            pass
        return events

    def unregister(self):
        for identifier in self.ids:
            self.user32.UnregisterHotKey(None, identifier)
        self.ids.clear()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join()
            self.thread = None
        self.poll()
