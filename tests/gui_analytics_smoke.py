"""Desktop-only smoke test: python -c \"import runpy; runpy.run_path('tests/gui_analytics_smoke.py')\"."""
import tkinter as tk
from er_checker.gui import App
from er_checker.dak import parse_snapshot
from er_checker.analytics import character_stats, recent_analysis
from er_checker.stat_table import CharacterTable


root = tk.Tk()
root.withdraw()
app = App(root, demo=True)
result = parse_snapshot({'name': 'Test', 'recentEmpty': True}, 'Test', 3)
result['character_stats'] = character_stats([
    {'name': 'Few', 'games': '2', 'rp': '900', 'rpDirection': 'up-arrow'},
    {'name': 'Loss', 'games': '3', 'rp': '120', 'rpDirection': 'down-arrow'},
    {'name': 'Gain', 'games': '12', 'rp': '120', 'rpDirection': 'up-arrow'},
])
result['recent_analysis'] = recent_analysis([{'mode': '排位'}] * 12 + [{'mode': '一般'}] * 8)
app.render('result', result)
root.update()


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


table = next(w for w in descendants(root) if isinstance(w, CharacterTable))
tree = table.tree


def names():
    return [tree.item(i, 'values')[0] for i in tree.get_children()]


assert names() == ['Gain', 'Loss', 'Few']
root.tk.call(tree.heading('average_rp', 'command'))
assert names() == ['Gain', 'Loss', 'Few']
root.tk.call(tree.heading('average_rp', 'command'))
assert names() == ['Loss', 'Gain', 'Few']
assert tree.item(tree.get_children()[-1], 'values')[3] == '不足 3 場'
assert '▲' in tree.heading('average_rp', 'text')
labels = [w.cget('text') for w in descendants(root) if w.winfo_class() == 'TLabel']
assert any('排位：12 場（60%）' in text for text in labels)
assert any('無法判定' in text for text in labels)
app.close()
print('PASS: character header sorting, signed RP, sample gate, mode percentages and unknown premade state')
