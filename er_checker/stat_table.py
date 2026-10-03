"""Sortable character table with numeric keys separate from display text."""
from tkinter import ttk
from .analytics import sorted_rows


class CharacterTable(ttk.Frame):
    COLUMNS = {'name': '角色', 'games': '場次', 'rp': '累積 RP',
               'average_rp': '場均 RP（≥3場）', 'win_rate': '勝率',
               'kills': '平均擊殺', 'damage': '平均傷害'}

    def __init__(self, parent, rows):
        super().__init__(parent)
        self.rows = rows
        self.sort_column, self.descending = 'games', True
        self.tree = ttk.Treeview(self, columns=tuple(self.COLUMNS), show='headings', height=7)
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        for col in self.COLUMNS:
            self.tree.column(col, width=140 if col == 'average_rp' else 100, minwidth=65, anchor='center')
            self.tree.heading(col, command=lambda c=col: self.sort(c))
        self.draw()

    def sort(self, column):
        self.descending = not self.descending if self.sort_column == column else column != 'name'
        self.sort_column = column
        self.draw()

    def draw(self):
        for col, title in self.COLUMNS.items():
            self.tree.heading(col, text=title + ((' ▼' if self.descending else ' ▲') if col == self.sort_column else ''))
        self.tree.delete(*self.tree.get_children())
        for row in sorted_rows(self.rows, self.sort_column, self.descending):
            values = []
            for col in self.COLUMNS:
                value = row.get(col)
                if value is None:
                    value = '不足 3 場' if col == 'average_rp' and row.get('games') is not None and row['games'] < 3 else '—'
                elif col in ('rp', 'average_rp'):
                    value = f'{value:+,.1f}' if col == 'average_rp' else f'{value:+,.0f}'
                elif col == 'win_rate':
                    value = f'{value:g}%'
                elif isinstance(value, (float, int)):
                    value = f'{value:,.0f}' if col in ('games', 'damage') else f'{value:g}'
                values.append(value)
            self.tree.insert('', 'end', values=values)
