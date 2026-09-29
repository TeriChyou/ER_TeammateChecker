"""Desktop QA on our own synthetic name window; live mode queries DAK.GG."""
import argparse
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageTk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from er_checker.capture import enable_dpi_awareness, desktop_bounds, RegionPicker
from er_checker.gui import App

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
enable_dpi_awareness()
root = tk.Tk()
app = App(root, demo=not args.live)
root.geometry('980x820+30+30')
panel = tk.Toplevel(root)
panel.title('ER OCR TEST — synthetic names, not a game screenshot')
panel.geometry('520x210+1100+80')
panel.attributes('-topmost', True)
sample = Image.new('RGB', (520, 210), '#1c2333')
draw = ImageDraw.Draw(sample)
font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 28)
draw.text((20, 25), '페이블', font=font, fill='white')
draw.text((20, 110), '백수', font=font, fill='white')
photo = ImageTk.PhotoImage(sample)
label = tk.Label(panel, image=photo, borderwidth=0)
label.pack()
root.update()
x, y = label.winfo_rootx(), label.winfo_rooty()
app.ocr.bounds = desktop_bounds()
app.ocr.regions = [[x+10, y+15, x+340, y+65], [x+10, y+100, x+340, y+150]]
app.ocr.capture()
deadline = time.monotonic() + 100
while app.busy and time.monotonic() < deadline:
    root.update()
    time.sleep(0.025)
assert not app.busy, 'Workflow did not finish'
assert app.names.get() == '페이블, 백수', app.names.get()
assert len(app.tabs.tabs()) == 2, app.status.get()
rows = []
for tab in app.tabs.tabs():
    frame = app.tabs.nametowidget(tab)
    def trees(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == 'Treeview':
                yield child
            yield from trees(child)
    found = list(trees(frame))
    assert found, [child.cget('text') for child in frame.winfo_children() if child.winfo_class() == 'TLabel']
    rows.append(len(found[0].get_children()))
    assert rows[-1] > 0
panel.destroy()
app.tabs.select(app.tabs.tabs()[0])
root.update()
artifact = ROOT / 'artifacts'
artifact.mkdir(exist_ok=True)
ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(artifact / 'ocr-dak-ui.png')

# Exercise the actual picker event callbacks and image scaling without relying
# on system mouse injection. These are local widget tests, not game interaction.
selected = []
picker = RegionPicker(root, sample, lambda regions, crops: selected.append((regions, crops)))
from types import SimpleNamespace
picker.press(SimpleNamespace(x=10, y=15))
picker.drag(SimpleNamespace(x=340, y=65))
picker.release(SimpleNamespace(x=340, y=65))
picker.finish(True)
assert selected[0][0] == [[10, 15, 340, 65]]
assert selected[0][1][0].size == (330, 50)
app.close()
report = {'input': 'Synthetic Korean names displayed in a real desktop window',
          'names': ['페이블', '백수'], 'provider': 'live DAK.GG' if args.live else 'demo',
          'rows': rows, 'capture': 'Pillow desktop capture, two regions', 'picker': 'callbacks and crop dimensions verified'}
(artifact / 'qa-workflow.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
