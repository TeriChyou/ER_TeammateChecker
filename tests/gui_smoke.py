"""Run separately on a desktop with Tcl/Tk: python -m tests.gui_smoke is not required."""
import time
import tkinter as tk
from er_checker.gui import App
from er_checker.hotkeys import Hotkeys


root = tk.Tk()
root.withdraw()
app = App(root, demo=True)
app.provider.set('官方 API')
app.names.set('')
app.lookup()
assert not app.busy
app.names.set('甲, 乙')
app.season.set('invalid')
app.lookup()
assert not app.busy
app.season.set('')
app.lookup()
deadline = time.monotonic() + 5
while app.busy and time.monotonic() < deadline:
    root.update()
    time.sleep(0.02)
assert not app.busy
assert len(app.tabs.tabs()) == 2
for tab in app.tabs.tabs():
    frame = app.tabs.nametowidget(tab)
    table_frame = frame.winfo_children()[-1]
    tree = next(child for child in table_frame.winfo_children() if child.winfo_class() == 'Treeview')
    assert len(tree.get_children()) == 20
app.close()
# OCR event routing: confidence gating, candidate selection, and cancellation.
from PIL import Image
from er_checker.ocr import Candidate
from unittest.mock import Mock
root = tk.Tk()
root.withdraw()
app = App(root, demo=True)
app.provider.set('官方 API')
app.update_provider()
root.update()
assert app.api_row.winfo_manager() == 'pack'
app.provider.set('DAK.GG（免 Key）')
app.update_provider()
assert not app.api_row.winfo_manager()
app.ocr.worker = Mock()
app.lookup = Mock()
app.ocr.reserve()
app.ocr.start_ocr([Image.new('RGB', (200, 40)), Image.new('RGB', (200, 40))])
assert app.names.get() == ''
app.ocr.complete([[Candidate('甲', 40, '繁中'), Candidate('乙', 30, '繁中')], [Candidate('페이블', 97, '韓')]])
app.lookup.assert_not_called()
app.ocr.boxes[0].current(1)
app.ocr.choose()
assert app.names.get() == '乙, 페이블'
app.ocr.complete([[Candidate('백수', 97, '韓')], [Candidate('페이블', 97, '韓')]])
app.lookup.assert_called_once()
app.lookup.reset_mock()
app.cancel.set()
app.ocr.complete([[Candidate('백수', 97, '韓')], [Candidate('페이블', 97, '韓')]])
app.lookup.assert_not_called()
app.close()
hotkeys = Hotkeys()
message = hotkeys.enable()
assert len(hotkeys.ids) == 2, message
hotkeys.close()
assert not hotkeys.ids
print('PASS: Tk demo, validation, two result tabs, 20 rows each, hotkey registration and cleanup')
