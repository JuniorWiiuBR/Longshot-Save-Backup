"""
Aba "Mods": lista os mods da build escolhida (<build>\\mods), adiciona por pasta ou .zip, liga/desliga,
muda a ordem e salva (renomeia as pastas e atualiza a tabela de tamanhos).
Lógica em mod_manager.py (adaptada do Link's Toolbox, de Cum_Dumpster).
"""
import os
import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import mod_manager as mm
from ui_common import BG, CARD, CARD2, CARD2_H, GOLD, FG, MUTED, LINE, FlatButton

TREE_BG = "#0e1126"


class ModsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=CARD)
        self.app = app
        self.mods = []
        self.dirty = False
        self.busy = False
        self.build = None          # Path da build escolhida
        self.builds = []           # nomes das builds (da mais nova para a mais antiga)
        self._style()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.lbl_build = tk.Label(self, bg=CARD, fg=FG, font=("Segoe UI", 10, "bold"))
        self.lbl_build.grid(row=0, column=0, sticky="w", padx=(18, 8), pady=(16, 0))
        self.v_build = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.v_build, state="readonly", style="Mods.TCombobox")
        self.combo.grid(row=0, column=1, sticky="we", pady=(16, 0), ipady=3)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.on_build_change())
        top_btns = tk.Frame(self, bg=CARD)
        top_btns.grid(row=0, column=2, padx=(8, 18), pady=(16, 0))
        self.btn_refresh = FlatButton(top_btns, "", self.reload)
        self.btn_refresh.pack(side="left", padx=(0, 6))
        self.btn_open = FlatButton(top_btns, "", self.open_dir)
        self.btn_open.pack(side="left")

        box = tk.Frame(self, bg=CARD)
        box.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=18, pady=(12, 0))
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(box, columns=("n", "state", "name"), show="headings",
                                 selectmode="browse", style="Mods.Treeview")
        self.tree.column("n", width=44, anchor="center", stretch=False)
        self.tree.column("state", width=110, anchor="w", stretch=False)
        self.tree.column("name", width=400, anchor="w")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview, style="Mods.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("on", foreground=FG)
        self.tree.tag_configure("off", foreground=MUTED)
        self.tree.tag_configure("bad", foreground="#ff8f7a")
        self.tree.tag_configure("clash", foreground="#e8c46a")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_note())
        self.tree.bind("<Double-1>", lambda e: self.toggle())

        self.note = tk.Label(self, bg=CARD, fg=MUTED, justify="left", anchor="w", wraplength=700,
                             font=("Segoe UI", 9))
        self.note.grid(row=2, column=0, columnspan=3, sticky="we", padx=18, pady=(8, 0))

        row1 = tk.Frame(self, bg=CARD)
        row1.grid(row=3, column=0, columnspan=3, sticky="we", padx=18, pady=(10, 0))
        self.btn_add_folder = FlatButton(row1, "", self.add_folder, primary=True)
        self.btn_add_folder.pack(side="left", padx=(0, 6))
        self.btn_add_zip = FlatButton(row1, "", self.add_zip, primary=True)
        self.btn_add_zip.pack(side="left", padx=(0, 14))
        self.btn_toggle = FlatButton(row1, "", self.toggle)
        self.btn_toggle.pack(side="left", padx=(0, 6))
        self.btn_up = FlatButton(row1, "", lambda: self.move(-1))
        self.btn_up.pack(side="left", padx=(0, 6))
        self.btn_down = FlatButton(row1, "", lambda: self.move(1))
        self.btn_down.pack(side="left")

        row2 = tk.Frame(self, bg=CARD)
        row2.grid(row=4, column=0, columnspan=3, sticky="we", padx=18, pady=(8, 16))
        self.btn_save = FlatButton(row2, "", self.save, primary=True)
        self.btn_save.pack(side="left", padx=(0, 6))
        self.btn_play = FlatButton(row2, "", lambda: self.save(play=True))
        self.btn_play.pack(side="left")
        self.status = tk.Label(row2, bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold"))
        self.status.pack(side="right")

    # ---- estilo escuro para Treeview / Combobox / Scrollbar
    def _style(self):
        s = ttk.Style(self.app.root)
        s.theme_use("clam")
        s.configure("Mods.Treeview", background=TREE_BG, fieldbackground=TREE_BG, foreground=FG,
                    rowheight=26, borderwidth=0, font=("Segoe UI", 10))
        s.map("Mods.Treeview", background=[("selected", CARD2_H)], foreground=[("selected", GOLD)])
        s.configure("Mods.Treeview.Heading", background=CARD2, foreground=GOLD, relief="flat",
                    font=("Segoe UI", 9, "bold"), borderwidth=0, padding=(6, 5))
        s.map("Mods.Treeview.Heading", background=[("active", CARD2_H)])
        s.configure("Mods.TCombobox", fieldbackground=CARD2, background=CARD2, foreground=FG,
                    arrowcolor=GOLD, bordercolor=LINE, lightcolor=CARD2, darkcolor=CARD2,
                    selectbackground=CARD2, selectforeground=FG)
        s.map("Mods.TCombobox", fieldbackground=[("readonly", CARD2)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", CARD2)], selectforeground=[("readonly", FG)])
        s.configure("Mods.Vertical.TScrollbar", background=CARD2, troughcolor=TREE_BG, bordercolor=TREE_BG,
                    arrowcolor=MUTED, lightcolor=CARD2, darkcolor=CARD2)
        self.app.root.option_add("*TCombobox*Listbox.background", CARD2)
        self.app.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.app.root.option_add("*TCombobox*Listbox.selectBackground", CARD2_H)
        self.app.root.option_add("*TCombobox*Listbox.selectForeground", GOLD)

    def t(self, key, **kw):
        return self.app.t(key, **kw)

    # ---- textos
    def apply_lang(self):
        self.lbl_build.configure(text=self.t("mods_build"))
        self.btn_refresh.configure(text=self.t("mods_refresh"))
        self.btn_open.configure(text=self.t("mods_open"))
        self.tree.heading("n", text=self.t("mods_col_n"))
        self.tree.heading("state", text=self.t("mods_col_state"))
        self.tree.heading("name", text=self.t("mods_col_name"))
        self.btn_add_folder.configure(text=self.t("mods_add_folder"))
        self.btn_add_zip.configure(text=self.t("mods_add_zip"))
        self.btn_toggle.configure(text=self.t("mods_toggle"))
        self.btn_up.configure(text=self.t("mods_up"))
        self.btn_down.configure(text=self.t("mods_down"))
        self.btn_save.configure(text=self.t("mods_save"))
        self.btn_play.configure(text=self.t("mods_save_play"))
        self.fill(keep=self.selected_folder())

    # ---- builds / lista
    def reload(self):
        builds = mm.list_builds(self.app.cfg["builds"])
        self.builds = [b.name for b in reversed(builds)]          # da mais nova para a mais antiga
        self.combo.configure(values=self.builds)
        if self.build is None or self.build.name not in self.builds:
            self.v_build.set(self.builds[0] if self.builds else "")
        self.load_build()

    def on_build_change(self):
        if self.dirty and not messagebox.askyesno(self.t("mods_title"), self.t("mods_discard"), parent=self):
            self.v_build.set(self.build.name if self.build else "")
            return
        self.load_build()

    def load_build(self):
        name = self.v_build.get()
        self.build = Path(self.app.cfg["builds"]) / name if name else None
        self.dirty = False
        self.mods = mm.scan(self.build / "mods") if self.build else []
        self.fill()

    def mods_dir(self):
        return self.build / "mods"

    def selected_folder(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def selected(self):
        f = self.selected_folder()
        return next((m for m in self.mods if m.folder == f), None)

    def fill(self, keep=None):
        self.tree.delete(*self.tree.get_children())
        clash = mm.clashes(self.mods)
        place = 0
        for m in self.mods:
            if m.active:
                place += 1
                tag = "clash" if clash.get(m.name) else "on"
                self.tree.insert("", "end", iid=m.folder, values=(place, self.t("mods_on"), m.name), tags=(tag,))
            elif not m.loads:
                self.tree.insert("", "end", iid=m.folder, values=("-", self.t("mods_noromfs"), m.name), tags=("bad",))
            else:
                self.tree.insert("", "end", iid=m.folder, values=("-", self.t("mods_off"), m.name), tags=("off",))
        if keep and self.tree.exists(keep):
            self.tree.selection_set(keep)
        self.update_status()
        self.show_note()

    def update_status(self):
        if not self.build:
            self.status.configure(text=self.t("mods_none"))
        elif not self.mods_dir().is_dir():
            self.status.configure(text=self.t("mods_no_folder"))
        else:
            text = self.t("mods_count", n=len(self.mods))
            if self.dirty:
                text += "   " + self.t("mods_dirty")
            self.status.configure(text=text)

    def show_note(self):
        m = self.selected()
        if m is None or not m.active:
            self.note.configure(text=self.t("mods_hint"))
            return
        rows = mm.clashes(self.mods).get(m.name) or []
        if not rows:
            self.note.configure(text=self.t("mods_hint"))
            return
        lines = [self.t("mods_clash", name=m.name, n=n, other=other,
                        who=self.t("mods_wins" if wins else "mods_loses")) for other, n, wins in rows[:4]]
        self.note.configure(text="\n".join(lines))

    # ---- ligar/desligar e ordem
    def game_busy(self):
        game = mm.game_running()
        if game:
            messagebox.showwarning(self.t("mods_title"), self.t("mods_game_open", game=game), parent=self)
        return bool(game)

    def toggle(self):
        m = self.selected()
        if m is None:
            return
        if not m.loads:
            messagebox.showinfo(self.t("mods_title"), self.t("mods_cannot_on"), parent=self)
            return
        m.on = not m.on
        on = [x for x in self.mods if x.active and x is not m]
        if m.on:
            on.append(m)                                     # o recém-ligado vai para o fim (e vence)
        off = sorted([x for x in self.mods if not x.active], key=lambda x: x.name.lower())
        self.mods = on + off
        self.dirty = True
        self.fill(keep=m.folder)

    def move(self, d):
        m = self.selected()
        if m is None or not m.active:
            return
        on = [x for x in self.mods if x.active]
        i = on.index(m)
        j = i + d
        if not 0 <= j < len(on):
            return
        on[i], on[j] = on[j], on[i]
        self.mods = on + [x for x in self.mods if not x.active]
        self.dirty = True
        self.fill(keep=m.folder)

    # ---- adicionar
    def add_folder(self):
        if not self.build or self.game_busy():
            return
        path = filedialog.askdirectory(parent=self, mustexist=True, title=self.t("mods_pick_folder"))
        if not path:
            return
        items = mm.collect(path)
        if not items:
            messagebox.showinfo(self.t("mods_title"), self.t("mods_none_found", src=path), parent=self)
            return
        self._install(items)

    def add_zip(self):
        if not self.build or self.game_busy():
            return
        paths = filedialog.askopenfilenames(parent=self, title=self.t("mods_pick_zip"),
                                            filetypes=[("ZIP", "*.zip"), ("*", "*.*")])
        if not paths:
            return
        items, temps = [], []
        self.status.configure(text=self.t("mods_extracting"))
        self.update_idletasks()
        try:
            for zp in paths:
                try:
                    work = mm.extract_zip(zp)
                except Exception as e:
                    messagebox.showerror(self.t("mods_title"), self.t("mods_zip_err", zip=os.path.basename(zp), err=e),
                                         parent=self)
                    continue
                temps.append(work)
                found = mm.collect(work, root_name=Path(zp).stem)
                if not found:
                    messagebox.showinfo(self.t("mods_title"), self.t("mods_none_found", src=os.path.basename(zp)),
                                        parent=self)
                items += found
            if items:
                self._install(items)
        finally:
            for w in temps:
                shutil.rmtree(w, ignore_errors=True)
            self.update_status()

    def _install(self, items):
        try:
            added, replaced, _skipped = mm.install(
                self.mods_dir(), items,
                lambda name: messagebox.askyesno(self.t("mods_title"), self.t("mods_replace_q", name=name), parent=self))
        except OSError as e:
            messagebox.showerror(self.t("mods_title"), self.t("mods_copy_err", err=e), parent=self)
            self.load_build()
            return
        self.mods = mm.scan(self.mods_dir())
        self.dirty = bool(added or replaced)
        self.fill()
        if added or replaced:
            self.status.configure(text=self.t("mods_added", n=len(added) + len(replaced)))
            self.app.log(self.t("log_mods_added", n=len(added) + len(replaced)))
        else:
            self.status.configure(text=self.t("mods_nothing"))

    # ---- salvar / jogar
    def save(self, play=False):
        if not self.build or self.busy or self.game_busy():
            return
        if play and not mm.game_exe(self.build):
            messagebox.showerror(self.t("mods_title"), self.t("mods_no_exe"), parent=self)
            return
        self.busy = True
        self.status.configure(text=self.t("mods_saving"))
        build, mods_dir, mods = self.build, self.mods_dir(), list(self.mods)

        def job():
            try:
                result = mm.apply(build, mods_dir, mods)
                err = None
            except Exception as e:  # noqa: BLE001
                result, err = None, e
            self.app.call_main(lambda: self._saved(build, result, err, play))

        import threading
        threading.Thread(target=job, daemon=True).start()

    def _saved(self, build, result, err, play):
        self.busy = False
        if err is not None:
            messagebox.showerror(self.t("mods_title"), self.t("mods_save_err", err=err), parent=self)
            self.load_build()
            return
        renamed, (state, detail) = result
        self.app.log(self.t("log_mods_saved", name=build.name, n=renamed))
        if state == "built":
            self.app.log(self.t("log_st_built", n=detail))
        elif state == "none":
            self.app.log(self.t("log_st_none"))
        elif state == "skip":
            self.app.log(self.t("log_st_skip", why=self.t("st_py314") if detail == "py314" else detail))
        else:
            self.app.log(self.t("log_st_err", err=detail))
        self.load_build()
        self.status.configure(text=self.t("mods_saved"))
        if play:
            exe = mm.game_exe(build)
            if exe:
                try:
                    subprocess.Popen([str(exe)], cwd=str(exe.parent))
                except OSError as e:
                    messagebox.showerror(self.t("mods_title"), str(e), parent=self)

    def open_dir(self):
        if not self.build:
            return
        d = self.mods_dir()
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(d))  # Windows
        except (AttributeError, OSError):
            pass
