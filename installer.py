"""
Instalador do Longshot Save Backup (também serve de desinstalador: Uninstall.exe --uninstall).
- Instala na pasta do usuário (não precisa de administrador).
- Cria atalho no Menu Iniciar (e, se quiser, na Área de Trabalho).
- Registra em "Aplicativos instalados" do Windows, com opção de desinstalar.
- Opção de iniciar com o Windows.
- Detecta versão instalada e atualiza.
"""
import ctypes
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk

from ui_common import (APP_VERSION, BG, CARD, CARD2, GOLD, FG, MUTED, LINE,
                       FlatButton, TriforceBackground, load_logo)

APP_NAME = "Longshot Save Backup"
APP_EXE = "LongshotSaveBackup.exe"
VERSION = APP_VERSION
SHORTCUT = "Longshot Save Backup.lnk"
LOCAL = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
INSTALL_DIR = os.path.join(LOCAL, "Programs", "LongshotSaveBackup")
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LongshotSaveBackup")
START_MENU = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LongshotSaveBackup"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "LongshotSaveBackup"
NO_WINDOW = 0x08000000
DETACHED = 0x00000008

TR = {
    "pt": {
        "win_title": "Instalador - Longshot Save Backup",
        "win_title_un": "Desinstalar - Longshot Save Backup",
        "welcome": "Bem-vindo!",
        "welcome_text": "Este assistente vai instalar o Longshot Save Backup no seu computador.\n\nDestino:\n{dir}",
        "update_text": "Já existe uma versão instalada ({old}).\nEla será atualizada para a versão {new}.\n\nDestino:\n{dir}",
        "opt_desktop": "Criar atalho na Área de Trabalho",
        "opt_start": "Iniciar com o Windows (a música toca ao abrir)",
        "install": "Instalar",
        "update": "Atualizar",
        "cancel": "Cancelar",
        "installing": "Instalando...",
        "step_close": "Fechando o programa se estiver aberto...",
        "step_files": "Copiando arquivos...",
        "step_register": "Registrando no Windows...",
        "step_shortcuts": "Criando atalhos...",
        "step_autostart": "Finalizando configurações...",
        "step_done": "Concluído!",
        "done": "Tudo pronto!",
        "done_text": "O Longshot Save Backup foi instalado com sucesso.",
        "open_now": "Abrir o programa agora",
        "finish": "Concluir",
        "error": "Algo deu errado",
        "error_text": "Não foi possível instalar:\n{err}",
        "close": "Fechar",
        "un_title": "Desinstalar",
        "un_text": "Deseja remover o Longshot Save Backup deste computador?",
        "un_cfg": "Remover também as configurações salvas",
        "un_btn": "Desinstalar",
        "un_done": "Programa removido.",
        "un_done_text": "O Longshot Save Backup foi desinstalado.",
        "un_note": "Seus backups no Google Drive não são apagados.",
        "not_installed": "O programa não parece estar instalado.",
    },
    "en": {
        "win_title": "Setup - Longshot Save Backup",
        "win_title_un": "Uninstall - Longshot Save Backup",
        "welcome": "Welcome!",
        "welcome_text": "This wizard will install Longshot Save Backup on your computer.\n\nDestination:\n{dir}",
        "update_text": "A version is already installed ({old}).\nIt will be updated to version {new}.\n\nDestination:\n{dir}",
        "opt_desktop": "Create a Desktop shortcut",
        "opt_start": "Start with Windows (music plays on launch)",
        "install": "Install",
        "update": "Update",
        "cancel": "Cancel",
        "installing": "Installing...",
        "step_close": "Closing the program if it is open...",
        "step_files": "Copying files...",
        "step_register": "Registering with Windows...",
        "step_shortcuts": "Creating shortcuts...",
        "step_autostart": "Finishing settings...",
        "step_done": "Done!",
        "done": "All set!",
        "done_text": "Longshot Save Backup was installed successfully.",
        "open_now": "Open the program now",
        "finish": "Finish",
        "error": "Something went wrong",
        "error_text": "Could not install:\n{err}",
        "close": "Close",
        "un_title": "Uninstall",
        "un_text": "Do you want to remove Longshot Save Backup from this computer?",
        "un_cfg": "Also remove saved settings",
        "un_btn": "Uninstall",
        "un_done": "Program removed.",
        "un_done_text": "Longshot Save Backup was uninstalled.",
        "un_note": "Your backups on Google Drive are not deleted.",
        "not_installed": "The program does not seem to be installed.",
    },
}


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ---------------------------------------------------------------- operações do sistema
def run_ps(script):
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        creationflags=NO_WINDOW, timeout=60, check=False)


def ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def kill_app():
    subprocess.run(["taskkill", "/F", "/IM", APP_EXE], creationflags=NO_WINDOW,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(1)


def installed_version():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            return winreg.QueryValueEx(k, "DisplayVersion")[0]
    except Exception:
        return None


def system_lang():
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "pt" if (lid & 0xFF) == 0x16 else "en"
    except Exception:
        return "pt"


def copy_with_retry(src, dst, tries=6):
    last = None
    for _ in range(tries):
        try:
            shutil.copy2(src, dst)
            return
        except (PermissionError, OSError) as e:
            last = e
            time.sleep(1)
    raise last


def do_install(desktop, autostart, report):
    import winreg
    exe_dst = os.path.join(INSTALL_DIR, APP_EXE)
    ico_dst = os.path.join(INSTALL_DIR, "icone.ico")
    unins = os.path.join(INSTALL_DIR, "Uninstall.exe")
    frozen = getattr(sys, "frozen", False)

    report(5, "step_close")
    kill_app()

    report(25, "step_files")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    src_exe = resource_path(APP_EXE)
    if not os.path.isfile(src_exe):
        raise FileNotFoundError(APP_EXE)
    copy_with_retry(src_exe, exe_dst)
    copy_with_retry(resource_path("icone.ico"), ico_dst)
    if frozen:
        copy_with_retry(sys.executable, unins)  # o próprio instalador vira o desinstalador
    time.sleep(0.3)

    report(55, "step_register")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, ico_dst)
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, max(1, os.path.getsize(exe_dst) // 1024))
        if frozen:
            winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'"{unins}" --uninstall')

    report(75, "step_shortcuts")
    lines = ["$w = New-Object -ComObject WScript.Shell"]
    lnk_start = os.path.join(START_MENU, SHORTCUT)
    lines += [
        f"$s = $w.CreateShortcut({ps_quote(lnk_start)})",
        f"$s.TargetPath = {ps_quote(exe_dst)}",
        f"$s.WorkingDirectory = {ps_quote(INSTALL_DIR)}",
        f"$s.IconLocation = {ps_quote(ico_dst)}",
        "$s.Save()",
    ]
    if desktop:
        lines += [
            f"$s = $w.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) {ps_quote(SHORTCUT)}))",
            f"$s.TargetPath = {ps_quote(exe_dst)}",
            f"$s.WorkingDirectory = {ps_quote(INSTALL_DIR)}",
            f"$s.IconLocation = {ps_quote(ico_dst)}",
            "$s.Save()",
        ]
    else:
        lines.append(
            f"Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) {ps_quote(SHORTCUT)}) -ErrorAction SilentlyContinue")
    run_ps("; ".join(lines))

    report(92, "step_autostart")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        if autostart:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, f'"{exe_dst}"')
        else:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except FileNotFoundError:
                pass
    report(100, "step_done")


def do_uninstall(remove_cfg):
    import winreg
    kill_app()
    try:
        os.remove(os.path.join(START_MENU, SHORTCUT))
    except OSError:
        pass
    run_ps(f"Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) {ps_quote(SHORTCUT)}) -ErrorAction SilentlyContinue")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, RUN_VALUE)
    except OSError:
        pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass
    if remove_cfg:
        shutil.rmtree(CFG_DIR, ignore_errors=True)


def schedule_delete_install_dir():
    """Apaga a pasta de instalação depois que este processo terminar (ele roda de dentro dela)."""
    subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 4 >nul & rmdir /s /q "{INSTALL_DIR}"',
                     creationflags=NO_WINDOW | DETACHED, close_fds=True)


# ---------------------------------------------------------------- interface
class Setup:
    def __init__(self, root, uninstall):
        self.root = root
        self.uninstall = uninstall
        self.lang = system_lang()
        self.state = "confirm" if uninstall else "welcome"
        self.v_desktop = tk.BooleanVar(value=True)
        self.v_autostart = tk.BooleanVar(value=False)
        self.v_open = tk.BooleanVar(value=True)
        self.v_cfg = tk.BooleanVar(value=False)
        self.old_version = installed_version()
        self.progress = 0
        self.progress_key = "step_close"
        self.error = ""
        self.q = queue.Queue()
        self.pending_delete = False

        root.protocol("WM_DELETE_WINDOW", self.close_window)
        root.geometry("680x460")
        root.resizable(False, False)
        root.configure(bg=BG)
        try:
            root.iconbitmap(resource_path("icone.ico"))
        except Exception:
            pass

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bgfx = TriforceBackground(self.canvas, count=22)
        self.logo = load_logo()
        self.canvas.create_image(24, 12, image=self.logo, anchor="nw")
        self.canvas.create_text(84, 36, text="Longshot Save Backup", fill=GOLD, anchor="w",
                                font=("Segoe UI", 18, "bold"))

        self.lang_en = FlatButton(root, "EN", lambda: self.set_lang("en"))
        self.lang_en.place(relx=1.0, x=-24, y=22, anchor="ne")
        self.lang_pt = FlatButton(root, "PT-BR", lambda: self.set_lang("pt"))
        self.lang_pt.place(relx=1.0, x=-84, y=22, anchor="ne")

        self.card = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.card.place(x=24, y=84, relwidth=1, width=-48, relheight=1, height=-108)

        self.render()
        root.after(100, self.poll)

    def t(self, key, **kw):
        s = TR[self.lang][key]
        return s.format(**kw) if kw else s

    def set_lang(self, lang):
        self.lang = lang
        self.render()

    def _label(self, text, size=10, bold=False, color=FG, **kw):
        return tk.Label(self.card, text=text, bg=CARD, fg=color, justify="left", anchor="w",
                        font=("Segoe UI", size, "bold" if bold else "normal"), wraplength=560, **kw)

    def _check(self, text, var):
        return tk.Checkbutton(self.card, text=text, variable=var, bg=CARD, fg=FG, selectcolor=CARD2,
                              activebackground=CARD, activeforeground=FG, font=("Segoe UI", 10),
                              anchor="w", bd=0, highlightthickness=0)

    def render(self):
        self.root.title(self.t("win_title_un" if self.uninstall else "win_title") + f" {VERSION}")
        self.lang_pt.set_active(self.lang == "pt")
        self.lang_en.set_active(self.lang == "en")
        for w in self.card.winfo_children():
            w.destroy()
        pad = {"padx": 26}
        c = self.card

        if self.state == "welcome":
            self._label(self.t("welcome"), 18, True, GOLD).pack(anchor="w", pady=(22, 8), **pad)
            if self.old_version:
                txt = self.t("update_text", old=self.old_version, new=VERSION, dir=INSTALL_DIR)
            else:
                txt = self.t("welcome_text", dir=INSTALL_DIR)
            self._label(txt, 10, False, MUTED).pack(anchor="w", pady=(0, 14), **pad)
            self._check(self.t("opt_desktop"), self.v_desktop).pack(anchor="w", pady=2, **pad)
            self._check(self.t("opt_start"), self.v_autostart).pack(anchor="w", pady=2, **pad)
            bar = tk.Frame(c, bg=CARD)
            bar.pack(side="bottom", fill="x", padx=26, pady=20)
            FlatButton(bar, self.t("update" if self.old_version else "install"), self.begin_install,
                       primary=True).pack(side="right")
            FlatButton(bar, self.t("cancel"), self.root.destroy).pack(side="right", padx=(0, 8))

        elif self.state == "installing":
            self._label(self.t("installing"), 18, True, GOLD).pack(anchor="w", pady=(22, 8), **pad)
            self.lbl_step = self._label(self.t(self.progress_key), 10, False, MUTED)
            self.lbl_step.pack(anchor="w", pady=(0, 14), **pad)
            self.bar_canvas = tk.Canvas(c, height=16, bg=CARD2, highlightthickness=0, bd=0)
            self.bar_canvas.pack(fill="x", padx=26)
            self.bar_canvas.bind("<Configure>", lambda e: self.draw_bar())
            self.draw_bar()

        elif self.state == "done":
            self._label(self.t("done"), 18, True, GOLD).pack(anchor="w", pady=(22, 8), **pad)
            self._label(self.t("done_text"), 10, False, MUTED).pack(anchor="w", pady=(0, 14), **pad)
            self._check(self.t("open_now"), self.v_open).pack(anchor="w", pady=2, **pad)
            bar = tk.Frame(c, bg=CARD)
            bar.pack(side="bottom", fill="x", padx=26, pady=20)
            FlatButton(bar, self.t("finish"), self.finish, primary=True).pack(side="right")

        elif self.state == "error":
            self._label(self.t("error"), 18, True, "#ff7a7a").pack(anchor="w", pady=(22, 8), **pad)
            self._label(self.t("error_text", err=self.error), 10, False, MUTED).pack(anchor="w", **pad)
            bar = tk.Frame(c, bg=CARD)
            bar.pack(side="bottom", fill="x", padx=26, pady=20)
            FlatButton(bar, self.t("close"), self.root.destroy, primary=True).pack(side="right")

        elif self.state == "confirm":  # desinstalar
            self._label(self.t("un_title"), 18, True, GOLD).pack(anchor="w", pady=(22, 8), **pad)
            self._label(self.t("un_text"), 10, False, FG).pack(anchor="w", pady=(0, 6), **pad)
            self._label(self.t("un_note"), 9, False, MUTED).pack(anchor="w", pady=(0, 14), **pad)
            self._check(self.t("un_cfg"), self.v_cfg).pack(anchor="w", pady=2, **pad)
            bar = tk.Frame(c, bg=CARD)
            bar.pack(side="bottom", fill="x", padx=26, pady=20)
            FlatButton(bar, self.t("un_btn"), self.begin_uninstall, primary=True).pack(side="right")
            FlatButton(bar, self.t("cancel"), self.root.destroy).pack(side="right", padx=(0, 8))

        elif self.state == "uninstalled":
            self._label(self.t("un_done"), 18, True, GOLD).pack(anchor="w", pady=(22, 8), **pad)
            self._label(self.t("un_done_text"), 10, False, MUTED).pack(anchor="w", pady=(0, 6), **pad)
            self._label(self.t("un_note"), 9, False, MUTED).pack(anchor="w", **pad)
            bar = tk.Frame(c, bg=CARD)
            bar.pack(side="bottom", fill="x", padx=26, pady=20)
            FlatButton(bar, self.t("close"), self.close_window, primary=True).pack(side="right")

    def close_window(self):
        if self.pending_delete:
            try:
                schedule_delete_install_dir()
            except Exception:
                pass
        self.root.destroy()

    def draw_bar(self):
        try:
            w = self.bar_canvas.winfo_width()
            self.bar_canvas.delete("all")
            self.bar_canvas.create_rectangle(0, 0, w * self.progress / 100.0, 16, fill=GOLD, width=0)
        except tk.TclError:
            pass

    # ---- ações
    def begin_install(self):
        self.state = "installing"
        self.progress, self.progress_key = 0, "step_close"
        self.render()
        desktop, autostart = self.v_desktop.get(), self.v_autostart.get()

        def report(pct, key):
            self.q.put(("progress", pct, key))

        def worker():
            try:
                do_install(desktop, autostart, report)
                self.q.put(("done",))
            except Exception as e:
                self.q.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def begin_uninstall(self):
        remove_cfg = self.v_cfg.get()
        try:
            do_uninstall(remove_cfg)
            self.pending_delete = True
            self.state = "uninstalled"
        except Exception as e:
            self.error, self.state = str(e), "error"
        self.render()

    def poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "progress":
                    self.progress, self.progress_key = msg[1], msg[2]
                    if self.state == "installing":
                        self.lbl_step.configure(text=self.t(self.progress_key))
                        self.draw_bar()
                elif msg[0] == "done":
                    self.state = "done"
                    self.render()
                elif msg[0] == "error":
                    self.error, self.state = msg[1], "error"
                    self.render()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finish(self):
        if self.v_open.get():
            try:
                subprocess.Popen([os.path.join(INSTALL_DIR, APP_EXE)], cwd=INSTALL_DIR,
                                 creationflags=NO_WINDOW | DETACHED, close_fds=True)
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    uninstall_mode = "--uninstall" in sys.argv
    root = tk.Tk()
    Setup(root, uninstall_mode)
    root.mainloop()
