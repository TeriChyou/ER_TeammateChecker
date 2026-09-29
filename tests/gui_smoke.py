"""Run separately on a desktop with Tcl/Tk: python -m tests.gui_smoke is not required."""
import time
import tkinter as tk
from er_checker.gui import App
from er_checker.hotkeys import Hotkeys


root = tk.Tk()
root.withdraw()
app = App(root, demo=True)
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
hotkeys = Hotkeys()
message = hotkeys.enable()
assert len(hotkeys.ids) == 2, message
hotkeys.close()
assert not hotkeys.ids
print('PASS: Tk demo, validation, two result tabs, 20 rows each, hotkey registration and cleanup')
