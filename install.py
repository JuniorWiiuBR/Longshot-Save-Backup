"""Installs Link's Tool Box for this Windows user (no admin needed): copies the unzipped download to
%LOCALAPPDATA%\\Programs\\Link Toolbox, adds Start menu and Desktop shortcuts, and an entry in Windows Settings > Apps
(where it can be uninstalled). Installing over an installed copy upgrades it and keeps the player's own files.

    install.py                         the install window (started by "Install Link Toolbox.bat")
    install.py --uninstall             what Windows Settings > Apps runs to uninstall it
    (tests: --to DIR, --no-registry, --no-shortcuts, --yes)
"""
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

HERE = Path(__file__).resolve().parent          # ...\app of the copy this runs from
SOURCE = HERE.parent                            # the unzipped "Link Toolbox" folder
sys.path.insert(0, str(HERE))
import nxsave  # noqa: E402
import theme  # noqa: E402
import updater  # noqa: E402

NAME = nxsave.APP_NAME
KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkToolbox'
DEFAULT = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs' / 'Link Toolbox'
NOWIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def start_menu():
    return Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / "Link's Tool Box.lnk"


def desktop():
    import icons
    return icons.desktop_folder() / "Link's Tool Box.lnk"


def shortcut(lnk, target):
    """A shortcut to the installed toolbox (target: the install folder), with its icon."""
    q = lambda s: str(s).replace("'", "''")
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(lnk)}'); "
          f"$s.TargetPath='{q(target / 'python' / 'pythonw.exe')}'; $s.Arguments='\"{q(target / 'app' / 'toolbox.pyw')}\"'; "
          f"$s.WorkingDirectory='{q(target / 'app')}'; $s.IconLocation='{q(target / 'app' / 'icon.ico')},0'; "
          "$s.Description='Link''s Tool Box - mod loader and save editor'; $s.Save()")
    Path(lnk).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, timeout=60, creationflags=NOWIN)
    return Path(lnk).exists()


def folder_size_kb(p):
    return sum(f.stat().st_size for f in Path(p).rglob('*') if f.is_file()) // 1024


def register(target, links):
    """The entry in Windows Settings > Apps (this user only)."""
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        py = target / 'python' / 'pythonw.exe'
        for name, value in (('DisplayName', NAME), ('DisplayVersion', nxsave.VERSION), ('Publisher', 'Cum_Dumpster'),
                            ('DisplayIcon', str(target / 'app' / 'icon.ico')), ('InstallLocation', str(target)),
                            ('UninstallString', f'"{py}" "{target / "app" / "install.py"}" --uninstall'),
                            ('URLInfoAbout', f'https://github.com/{updater.REPO}'),
                            ('Shortcuts', '|'.join(str(x) for x in links))):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        for name, value in (('NoModify', 1), ('NoRepair', 1), ('EstimatedSize', folder_size_kb(target))):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)


def installed():
    """(folder, [shortcuts]) of the installed copy, from its Apps entry; None when it is not installed."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            where = winreg.QueryValueEx(k, 'InstallLocation')[0]
            try:
                links = [x for x in winreg.QueryValueEx(k, 'Shortcuts')[0].split('|') if x]
            except OSError:
                links = []
            return Path(where), links
    except OSError:
        return None


def refresh_version():
    """After an update: the Apps entry shows the new version (called by the toolbox when it starts)."""
    found = installed()
    if found and os.path.normcase(str(found[0])) == os.path.normcase(str(SOURCE)):
        import winreg
        links = []
        for lnk in found[1]:            # (Start menu / Desktop shortcuts under the old name: under the new one)
            p = Path(lnk)
            if p.exists() and p.name == 'Link Toolbox.lnk':
                new = p.with_name(f'{NAME}.lnk')
                if shortcut(new, SOURCE):
                    try:
                        p.unlink()
                    except OSError:
                        pass
                    p = new
            links.append(str(p))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, 'DisplayVersion', 0, winreg.REG_SZ, nxsave.VERSION)
            winreg.SetValueEx(k, 'DisplayName', 0, winreg.REG_SZ, NAME)
            winreg.SetValueEx(k, 'Shortcuts', 0, winreg.REG_SZ, '|'.join(links))


def copy_in(target):
    """Copies the download into target; an installed copy there keeps the player's own files."""
    target.mkdir(parents=True, exist_ok=True)
    cmd = ['robocopy', str(SOURCE), str(target), '/E', '/R:3', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
           '/XF', *updater.KEEP_FILES, 'Install Link Toolbox.bat', '/XD', *updater.KEEP_DIRS]
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=NOWIN)
    if r.returncode >= 8:
        raise OSError(f'copying failed (robocopy {r.returncode}): {r.stdout.strip()[-300:]}')
    # the icon in use: the download's own when the install has none yet
    for name in ('icon.ico', 'icon.png'):
        if not (target / 'app' / name).exists() and (HERE / name).exists():
            (target / 'app' / name).write_bytes((HERE / name).read_bytes())
    bring_own_files(target)


OWN_FILES = ('toolbox_settings.json', 'names-cache-*.json')   # (what the player set up in a copy they used)


def bring_own_files(target):
    """Installing from a portable copy that was used: its settings (game, folders, shared builds, look...), names
    lists and save backups come along, so nothing has to be set up again. Only into an install that has no settings of
    its own: an installed copy's own are never replaced. Returns the names brought."""
    import shutil
    app = target / 'app'
    if (app / 'toolbox_settings.json').exists() or not (HERE / 'toolbox_settings.json').is_file():
        return []
    brought = []
    for pattern in OWN_FILES:
        for f in HERE.glob(pattern):
            if f.is_file() and not (app / f.name).exists():
                shutil.copy2(f, app / f.name)
                brought.append(f.name)
    backups = HERE / 'backups'
    if backups.is_dir():
        (app / 'backups').mkdir(parents=True, exist_ok=True)
        for b in backups.iterdir():
            dest = app / 'backups' / b.name
            if not dest.exists():
                (shutil.copytree if b.is_dir() else shutil.copy2)(b, dest)
        brought.append('backups')
    return brought


def install(target, desk=True, menu=True, reg=True, links=True):
    if nxsave.game_running():
        raise RuntimeError('Close the game first.')
    if os.path.normcase(str(target.resolve())) != os.path.normcase(str(SOURCE.resolve())):
        copy_in(target)
    made = []
    if links:
        for want, lnk in ((menu, start_menu()), (desk, desktop())):
            if want and shortcut(lnk, target):
                made.append(lnk)
    if reg:
        register(target, made)
    return made


def is_installed_copy():
    """True when this copy is the installed one (its Apps entry points here)."""
    found = installed()
    return bool(found) and os.path.normcase(str(found[0].resolve())) == os.path.normcase(str(SOURCE.resolve()))


def uninstall(yes=False, parent=None):
    """Asks (unless yes), then removes the shortcuts, the Apps entry and the files; the files go once every toolbox
    window running from them has closed. parent: the toolbox's window (the Updates tab's Uninstall button), which
    must close right after this returns True."""
    found = installed()
    target, links = found if found else (SOURCE, [])
    root = parent
    if root is None:
        root = tk.Tk()
        root.withdraw()
    if not yes and not messagebox.askyesno(
            f'Uninstall {NAME}', f'Uninstall the {NAME} app?\n\nThis removes only the toolbox app:\n  {target}\n  its '
            'Start menu and Desktop shortcuts\n  its entry in Windows Settings > Apps\n\nThe game, your game saves '
            'and your mods are NOT touched.', icon='warning', parent=root):
        return False
    keep = True if yes else messagebox.askyesnocancel(
        f'Uninstall {NAME}', "Keep the toolbox's save backups and its settings (in its app folder)?\n\nYes: keep "
        'them.   No: delete them too.\n\n(These are only the copies the toolbox made. Your real game saves are in '
        'the game\'s own folder and stay either way.)', parent=root)
    if keep is None:
        return False
    for lnk in links + [str(start_menu()), str(desktop())]:
        try:
            p = Path(lnk)
            if p.suffix == '.lnk' and p.exists() and ('Link Toolbox' in p.name or nxsave.APP_NAME in p.name):
                p.unlink()
        except OSError:
            pass
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, KEY)
    except OSError:
        pass
    # the files go once this program (running from them) has closed
    t = str(target)
    if keep:
        steps = (f'rd /s /q "{t}\\python" & rd /s /q "{t}\\mods" & del /q "{t}\\*.bat" "{t}\\*.txt" "{t}\\*.lnk" & '
                 f'del /q "{t}\\app\\*.py" "{t}\\app\\*.pyw" "{t}\\app\\names-cache*.json" & '
                 f'rd /s /q "{t}\\app\\__pycache__"')
    else:
        steps = f'rd /s /q "{t}"'
    # (waits for this program to close: its Python is in the folder being removed)
    script = Path(os.environ.get('TEMP', str(Path.home()))) / f'link-toolbox-uninstall-{os.getpid()}.bat'
    script.write_text('@echo off\r\n:wait\r\n'
                      f'tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul && '
                      '(timeout /t 1 /nobreak >nul & goto wait)\r\n'
                      f'timeout /t 1 /nobreak >nul\r\n{steps.replace(" & ", chr(13) + chr(10))}\r\n'
                      'del "%~f0"\r\n', encoding='mbcs')
    subprocess.Popen(['cmd', '/c', str(script)], creationflags=NOWIN)
    if not yes:
        messagebox.showinfo(f'Uninstall {NAME}', f'The {NAME} app is uninstalled. The game and your saves are '
                            'untouched.' + (f'\n\nKept: {t}\\app\\backups and the settings.'
                                                               if keep else '') +
                            ('\n\nThe toolbox closes now.' if parent is not None else ''), parent=root)
    if parent is None:
        root.destroy()
    return True


def window():
    root = tk.Tk()
    theme.apply(root)
    try:
        import icons
        icons.apply(root)
    except Exception:
        pass
    root.title(f'Install {NAME} {nxsave.VERSION}')
    root.resizable(False, False)
    frm = ttk.Frame(root, padding=18)
    frm.pack(fill='both', expand=True)
    frm.columnconfigure(1, weight=1)
    found = installed()
    ttk.Label(frm, text=f'{NAME} {nxsave.VERSION}', font=(theme.FAMILY, 13, 'bold')).grid(row=0, column=0,
                                                                                      columnspan=3, sticky='w')
    used = (HERE / 'toolbox_settings.json').is_file()
    ttk.Label(frm, text=('Upgrades the installed copy: your settings, backups and icon are kept.' if found else
                         'Installs it for you (no admin needed), with shortcuts and an entry in Windows Settings > '
                         'Apps to uninstall it. Updates then come from its Updates tab, and your settings stay put.' +
                         ('\n\nThe settings and backups of this copy come along: your game, folders, shared builds '
                          'and look stay as you set them.' if used else '')),
              foreground=theme.SOFT, wraplength=560, justify='left').grid(row=1, column=0, columnspan=3, sticky='w',
                                                                          pady=(4, 12))
    ttk.Label(frm, text='Install to').grid(row=2, column=0, sticky='w')
    where = tk.StringVar(value=str(found[0] if found else DEFAULT))
    ttk.Entry(frm, textvariable=where, width=60).grid(row=2, column=1, sticky='ew', padx=8)
    ttk.Button(frm, text='Browse...', command=lambda: where.set(
        os.path.normpath(filedialog.askdirectory(parent=root) or where.get()))).grid(row=2, column=2)
    desk, menu = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    ttk.Checkbutton(frm, text='Shortcut on the Desktop', variable=desk).grid(row=3, column=1, sticky='w',
                                                                             padx=8, pady=(10, 0))
    ttk.Checkbutton(frm, text='Shortcut in the Start menu', variable=menu).grid(row=4, column=1, sticky='w', padx=8)
    status = ttk.Label(frm, text='', foreground=theme.SOFT)
    status.grid(row=5, column=0, columnspan=3, sticky='w', pady=(12, 0))
    bar = ttk.Frame(frm)
    bar.grid(row=6, column=0, columnspan=3, sticky='e', pady=(12, 0))

    def go():
        target = Path(where.get().strip().strip('"'))
        status['text'] = 'Installing...'
        root.update()
        try:
            install(target, desk.get(), menu.get())
        except Exception as err:
            status['text'] = ''
            messagebox.showerror(NAME, f'It could not be installed:\n{err}', parent=root)
            return
        py = target / 'python' / 'pythonw.exe'
        if messagebox.askyesno(NAME, f'{NAME} is installed in\n{target}\n\nOpen it now? (You can delete the '
                               'unzipped folder you installed from.)', parent=root):
            subprocess.Popen([str(py), str(target / 'app' / 'toolbox.pyw')], cwd=str(target / 'app'))
        root.destroy()
    ttk.Button(bar, text='Cancel', command=root.destroy).pack(side='right')
    ttk.Button(bar, text='Upgrade' if found else 'Install', command=go).pack(side='right', padx=(0, 8))
    root.mainloop()


if __name__ == '__main__':
    if '--uninstall' in sys.argv:
        uninstall(yes='--yes' in sys.argv)
    elif '--to' in sys.argv:          # (tests, or a scripted install without the window)
        print(install(Path(arg('--to')), reg='--no-registry' not in sys.argv, links='--no-shortcuts' not in sys.argv))
    else:
        window()
