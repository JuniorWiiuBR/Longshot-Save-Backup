"""The Link toolbox: the mod loader and the save editor in one window, a tab each.

    Mods          switch the mods in game/mods on and off, set their order, Save and play (mod_loader.pyw)
    Save editor   every entry of a save by name, the Give buttons (save_editor.pyw)
    Folders       use another game, mods or saves folder (kept in toolbox_settings.json, which the two use on
                  their own too)
    Look          the theme, the accent colour and each tab's colour (theme.py)

Run:  python\\pythonw.exe save-editor\\toolbox.pyw      (or Link Toolbox.bat). The two still open on their own too.
"""
import importlib.util
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nxsave  # noqa: E402
import theme  # noqa: E402
from tkinter import colorchooser  # noqa: E402

BASE_TITLE = 'Link toolbox'
CREDIT = 'Cum_Dumpster'      # the watermark along the bottom of the window


def load(name):
    """A .pyw module of this folder (import does not look at .pyw files)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.pyw'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod_loader = save_editor = None     # (loaded by main once the game's folder is known: they read it when loaded)


def ask_game_dir(root):
    """On a PC where the game is not where it usually is: ask once for its folder, kept in the settings."""
    messagebox.showinfo(BASE_TITLE, 'Where is the game?\n\nPick the folder that has Triforce.exe in it (the game '
                        'folder Triforce built, with the romfs folder inside).', parent=root)
    while True:
        path = filedialog.askdirectory(parent=root, title='The game folder (with Triforce.exe)', mustexist=True)
        if not path:
            return False
        if nxsave.is_game_dir(path):
            nxsave.save_settings({**nxsave.load_settings(), 'game_dir': os.path.normpath(path)})
            return True
        if not messagebox.askretrycancel(BASE_TITLE, f'{path}\n\nhas no Triforce.exe or romfs folder.', parent=root):
            return False


def load_tools():
    global mod_loader, save_editor
    mod_loader = load('mod_loader')
    save_editor = load('save_editor')



class Toolbox:
    def __init__(self, root):
        self.root = root
        root.title(BASE_TITLE)
        root.geometry('1100x720')
        root.minsize(760, 440)
        self.titles = {}
        ttk.Label(root, text=f"Link's Tools  ·  by {CREDIT}", foreground=theme.FAINT,
                  font=('Segoe UI', 8, 'italic')).pack(side='bottom', anchor='e', padx=10, pady=(0, 4))
        self.book = ttk.Notebook(root)
        self.book.pack(fill='both', expand=True, padx=6, pady=6)
        self.mods = mod_loader.App(self.book, on_title=lambda t: self.set_title('mods', t), after_play=self.after_play)
        self.book.add(self.mods, text='Mods')
        self.saves = save_editor.App(self.book, on_title=lambda t: self.set_title('saves', t))
        self.book.add(self.saves, text='Save editor')
        self.folders = self.make_folders_tab()
        self.book.add(self.folders, text='Folders')
        self.look = self.make_look_tab()
        self.book.add(self.look, text='Look')
        theme.color_tabs(self.book, ['Mods', 'Save editor', 'Folders', 'Look'])
        self.book.bind('<<NotebookTabChanged>>', lambda _e: self.on_tab(), add='+')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.on_tab()

    # -- the Folders tab: where the mods and the saves are, when not the usual places
    def make_folders_tab(self):
        tab = ttk.Frame(self.book, padding=16)
        tab.columnconfigure(1, weight=1)
        settings = nxsave.load_settings()
        self.game_var = tk.StringVar(value=settings.get('game_dir', ''))
        self.mods_var = tk.StringVar(value=settings.get('mods_dir', ''))
        self.save_var = tk.StringVar(value=settings.get('save_dir', ''))
        self.game_at_start = nxsave.game_dir()
        rows = (('Game folder', self.game_var, self.found_game(),
                 'The folder with Triforce.exe and romfs. Changing it takes effect when the toolbox is opened again.'),
                ('Mods folder', self.mods_var, mod_loader.DEFAULT_MODS,
                 'The folder of mod folders the Mods tab lists and switches on and off.'),
                ('Saves folder', self.save_var, nxsave.game_dir() / 'user' / 'save',
                 "A save's own folder (the one with slot_01, slot_02...), or a folder of those: the latest is used."))
        r = 0
        for label, var, default, hint in rows:
            ttk.Label(tab, text=label, font=('Segoe UI', 10, 'bold')).grid(row=r, column=0, sticky='w', pady=(10, 0))
            ttk.Entry(tab, textvariable=var).grid(row=r, column=1, sticky='ew', padx=8, pady=(10, 0))
            ttk.Button(tab, text='Browse...', command=lambda v=var, d=default: self.browse(v, d)).grid(
                row=r, column=2, pady=(10, 0))
            ttk.Button(tab, text='Default', command=lambda v=var: v.set('')).grid(row=r, column=3, padx=(6, 0),
                                                                                    pady=(10, 0))
            ttk.Label(tab, text=f'{hint}\nEmpty: the default, {default}', foreground=theme.MUTED).grid(
                row=r + 1, column=1, columnspan=3, sticky='w', padx=8)
            r += 2
        ttk.Label(tab, text='Triforce itself only loads mods from the mods folder next to Triforce.exe '
                            f'({mod_loader.DEFAULT_MODS}). Mods kept anywhere else can be switched here but '
                            'the game will not see them, unless that folder is next to another Triforce.exe '
                            '(then Save and play starts that one).',
                  foreground=theme.WARN, wraplength=760, justify='left').grid(row=r, column=0, columnspan=4,
                                                                              sticky='w', pady=(18, 0))
        bar = ttk.Frame(tab)
        bar.grid(row=r + 1, column=0, columnspan=4, sticky='e', pady=(18, 0))
        self.folders_status = ttk.Label(bar, text='', foreground=theme.SOFT)
        self.folders_status.pack(side='left', padx=(0, 12))
        ttk.Button(bar, text='Apply', command=self.apply_folders).pack(side='left')
        return tab

    # -- the Look tab: the theme, the accent colour and each tab's colour
    def make_look_tab(self):
        tab = ttk.Frame(self.book, padding=16)
        t = nxsave.load_settings().get('theme') or {}
        self.look_preset = tk.StringVar(value=theme.PRESET)
        self.look_accent = t.get('accent') or theme.DEFAULT_ACCENT
        self.look_tabs = dict(theme.TAB_COLORS)
        self.swatches = {}

        top = ttk.LabelFrame(tab, text='Theme', padding=(12, 8))
        top.pack(fill='x')
        ttk.Label(top, text='Colours').grid(row=0, column=0, sticky='w')
        box = ttk.Combobox(top, textvariable=self.look_preset, values=list(theme.PRESETS), state='readonly',
                           width=20)
        box.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=3)
        box.bind('<<ComboboxSelected>>', lambda _e: self.apply_look())
        ttk.Label(top, text='Accent').grid(row=1, column=0, sticky='w')
        self.swatch(top, 1, 'accent', lambda: self.look_accent)
        ttk.Label(top, text='headings, box titles, the buttons\' focus', foreground=theme.MUTED).grid(
            row=1, column=4, sticky='w', padx=(10, 0))

        tabs = ttk.LabelFrame(tab, text='Tab colours', padding=(12, 8))
        tabs.pack(fill='x', pady=(12, 0))
        groups = (('Toolbox', ('Mods', 'Save editor', 'Folders', 'Look')),
                  ('Save editor', ('Stats', 'Inventory', 'Progress', 'All entries')))
        for c, (title, names) in enumerate(groups):
            ttk.Label(tabs, text=title, foreground=theme.MUTED).grid(row=0, column=c * 5, sticky='w', pady=(0, 4))
            for r, name in enumerate(names, 1):
                ttk.Label(tabs, text=name).grid(row=r, column=c * 5, sticky='w', padx=(0, 10))
                self.swatch(tabs, r, name, lambda n=name: self.look_tabs[n], col=c * 5 + 1)
            tabs.columnconfigure(c * 5 + 4, minsize=60)

        bar = ttk.Frame(tab)
        bar.pack(fill='x', pady=(16, 0))
        ttk.Button(bar, text='Everything back to default', command=self.reset_look).pack(side='left')
        self.look_status = ttk.Label(bar, text='Changes show at once. A few hint texts take the new colours when '
                                               'the toolbox opens again.', foreground=theme.MUTED)
        self.look_status.pack(side='left', padx=(14, 0))
        return tab

    def swatch(self, parent, row, key, get, col=1):
        """A square of a colour, a Pick button and a Default button, in a row of a grid."""
        sw = tk.Label(parent, width=4, background=get(), relief='solid', borderwidth=1, cursor='hand2')
        sw.grid(row=row, column=col, sticky='w', padx=(10, 6), pady=3)
        sw.bind('<Button-1>', lambda _e: self.pick_color(key))
        ttk.Button(parent, text='Pick...', command=lambda: self.pick_color(key)).grid(row=row, column=col + 1,
                                                                                     sticky='w')
        ttk.Button(parent, text='Default', command=lambda: self.default_color(key)).grid(row=row, column=col + 2,
                                                                                        sticky='w', padx=(6, 0))
        self.swatches[key] = sw

    def pick_color(self, key):
        now = self.look_accent if key == 'accent' else self.look_tabs[key]
        _rgb, color = colorchooser.askcolor(color=now, parent=self.root,
                                            title='Accent colour' if key == 'accent' else f'Colour of the {key} tab')
        if not color:
            return
        if key == 'accent':
            self.look_accent = color
        else:
            self.look_tabs[key] = color
        self.apply_look()

    def default_color(self, key):
        if key == 'accent':
            self.look_accent = theme.DEFAULT_ACCENT
        else:
            self.look_tabs[key] = theme.DEFAULT_TABS[key]
        self.apply_look()

    def reset_look(self):
        self.look_preset.set(theme.DEFAULT_PRESET)
        self.look_accent = theme.DEFAULT_ACCENT
        self.look_tabs = dict(theme.DEFAULT_TABS)
        self.apply_look()

    def apply_look(self):
        """Keeps the choice in the settings and puts it on everything open."""
        tabs = {k: v for k, v in self.look_tabs.items() if v.lower() != theme.DEFAULT_TABS[k].lower()}
        look = {'preset': self.look_preset.get(), 'accent': self.look_accent, 'tabs': tabs}
        settings = {**nxsave.load_settings(), 'theme': look}
        try:
            nxsave.save_settings(settings)
        except OSError as err:
            self.look_status['text'] = f'Could not keep the choice: {err}'
        theme.refresh(self.root, settings)
        for key, sw in self.swatches.items():
            sw.configure(background=self.look_accent if key == 'accent' else self.look_tabs[key])
        self.saves.restyle()
        self.mods.restyle()

    @staticmethod
    def found_game():
        """Where the game is found when none is picked."""
        saved = nxsave.load_settings()
        nxsave.SETTINGS_OVERRIDE = {k: v for k, v in saved.items() if k != 'game_dir'}
        try:
            return nxsave.find_game_dir() or '(not found)'
        finally:
            nxsave.SETTINGS_OVERRIDE = None

    def browse(self, var, default):
        start = var.get() or str(default)
        path = filedialog.askdirectory(parent=self.root, initialdir=start if os.path.isdir(start) else None,
                                       mustexist=True)
        if path:
            var.set(os.path.normpath(path))

    def apply_folders(self):
        mods_dir, save_dir = self.mods_var.get().strip().strip('"'), self.save_var.get().strip().strip('"')
        game = self.game_var.get().strip().strip('"')
        if game and not nxsave.is_game_dir(game):
            messagebox.showerror('Folders', f'{game}\n\nhas no Triforce.exe or romfs folder: not the game folder.',
                                 parent=self.root)
            return
        for path, what in ((mods_dir, 'mods'), (save_dir, 'saves')):
            if path and not os.path.isdir(path):
                messagebox.showerror('Folders', f'The {what} folder is not there:\n{path}', parent=self.root)
                return
        if save_dir and not nxsave.save_dirs_in(save_dir):
            if not messagebox.askyesno('Folders', f'No save was found in\n{save_dir}\n\nUse it anyway?',
                                       parent=self.root):
                return
        if not (self.mods.may_close() and self.saves.may_close()):     # (each asks about its changes not saved)
            return
        same = lambda a, b: bool(a) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
        if same(mods_dir, mod_loader.DEFAULT_MODS):
            mods_dir = ''
        if same(save_dir, nxsave.game_dir() / 'user' / 'save'):
            save_dir = ''
        self.mods_var.set(mods_dir)
        self.save_var.set(save_dir)
        nxsave.save_settings({**nxsave.load_settings(), 'mods_dir': mods_dir, 'save_dir': save_dir,
                              'game_dir': os.path.normpath(game) if game else ''})
        if not same(str(nxsave.game_dir()), self.game_at_start):
            messagebox.showinfo('Folders', 'The game folder changed: close the toolbox and open it again to use it.',
                                parent=self.root)
            self.folders_status['text'] = 'Saved. Open the toolbox again for the new game folder.'
            return
        mod_loader.set_mods_dir(mods_dir or None)
        self.mods.dirty = False
        self.mods.reload()
        self.saves.load_file_list()
        self.folders_status['text'] = (f'Saved. Mods tab: {len(self.mods.mods)} mods. Save editor: '
                                       f'{self.saves.save_file.path if self.saves.save_file else "no save found"}')

    def current(self):
        sel = self.book.select()
        return ('mods' if sel == str(self.mods) else 'saves' if sel == str(self.saves) else
                'look' if sel == str(getattr(self, 'look', None)) else 'folders')

    def set_title(self, which, text):
        """Each tab says what it would call its window; the window shows the one in front, and a * on a tab's name
        while it has changes not saved."""
        self.titles[which] = text
        tab = getattr(self, which, None)          # (None while that tab is still being made: it reports early)
        if tab is None or str(tab) not in self.book.tabs():
            return
        self.book.tab(tab, text=('* ' if text.startswith('* ') else '') + ('Mods' if which == 'mods' else 'Save editor'))
        if which == self.current():
            self.root.title(f'{BASE_TITLE} - {text.lstrip("* ")}' if not text.startswith('* ')
                            else f'* {BASE_TITLE} - {text[2:]}')

    def on_tab(self):
        which = self.current()
        if which == 'mods':
            self.mods.fill()          # (the game may have been started or closed since)
        if which in ('folders', 'look'):
            self.root.title(f'{BASE_TITLE} - {which.title()}')
            return
        self.set_title(which, self.titles.get(which, ''))

    def after_play(self):
        """The game is starting: the toolbox goes, unless the save editor has edits not saved."""
        if self.saves.may_close():
            self.root.destroy()

    def close(self):
        if self.mods.may_close() and self.saves.may_close():
            self.root.destroy()


def main():
    root = tk.Tk()
    theme.apply(root)
    if nxsave.find_game_dir() is None and '--selftest' not in sys.argv:
        root.withdraw()
        if not ask_game_dir(root):
            root.destroy()
            return
        root.deiconify()
    load_tools()
    box = Toolbox(root)
    if '--selftest' in sys.argv:      # open both tabs, switch between them, close: nothing is written
        def done():
            print('tabs:', [box.book.tab(t, 'text') for t in box.book.tabs()], '| title:', root.title(),
                  '| mods listed:', len(box.mods.mods), '| save file:', box.saves.save_file.path if box.saves.save_file else None)
            root.destroy()
        root.report_callback_exception = lambda *a: (print('ERROR', a[1]), root.destroy())
        root.after(300, lambda: box.book.select(box.saves))
        root.after(900, lambda: box.book.select(box.folders))
        root.after(1200, lambda: box.book.select(box.mods))
        root.after(1800, done)
    root.mainloop()


if __name__ == '__main__':
    main()
