"""Packs the Link toolbox to give to someone else: save-editor\\share\\Link Toolbox.zip, which works from any folder.

    Link Toolbox\\
        Link Toolbox.bat     double-click to open
        README.txt           (save-editor\\README.txt: edit that one)
        app\\                the toolbox's scripts (no backups, settings or names cache: those are made there)
        mods\\               the mods that are on in game\\mods (the Mods tab's "Add mods..." installs them);
                             --no-mods leaves them out
        python\\              the Python NX2navi ships, without its site-packages (the toolbox does not use them)

Run:  python\\python.exe save-editor\\make_share_zip.py                  (inside the NX2navi folder)
      python make_share_zip.py --python "C:\\path\\to\\python314"       (anywhere else)
"""
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = HERE.parent / 'python'
OUT = HERE / 'share' / 'Link Toolbox.zip'
APP = ('toolbox.pyw', 'mod_loader.pyw', 'save_editor.pyw', 'nxsave.py', 'oot_catalog.py', 'jpeg_win.py',
       'size_table.py', 'theme.py', 'icons.py')
OPTIONAL = ('icon.ico', 'icon.png')     # the icon picked in the Look tab (made with the default one when missing)
SKIP_PY = ('Lib', '__pycache__')      # (Lib holds only site-packages: 72 MB the toolbox never imports)

BAT = '''@echo off
rem Opens the Link toolbox (mod loader and save editor) with the Python in this folder.
start "" "%~dp0python\\pythonw.exe" "%~dp0app\\toolbox.pyw"
'''

README = '''Link Toolbox - mod loader and save editor for Zelda: Ocarina of Time on Triforce
==============================================================================
Link's Tools, by Cum_Dumpster

Start:   unzip this folder anywhere (Desktop, Documents...), then double-click "Link Toolbox.bat".
         Nothing to install: the Python it needs is in the python folder.

The game folder
    The toolbox finds the game where Triforce put it (it reads Triforce's own setup log). If it cannot,
    it asks once: pick the folder that has Triforce.exe and the romfs folder in it. To change it later:
    the Folders tab.

Tabs
    Mods         switch the mods in the game's mods folder on and off, set which wins, Save and play.
                 Triforce only loads mods from the "mods" folder next to Triforce.exe.
    Save editor  pick a slot. Stats (hearts, magic, rupees, bags, ammo, bottles, keys), Inventory (give or take
                 away items), Progress (story flags), All entries (every value). Click a column heading to sort.
    Folders      another game, mods or saves folder.
    Look         the colours: a theme (dark green, grey, blue, purple, light), the accent, each tab's colour.

Before saving a save: CLOSE THE GAME. The game writes over the save files when it saves.
Every save first copies the old files into app\\backups (the "Backups folder" button opens it).

The first time the save editor opens it reads the names from the game files: that takes a little while once.
Needs Windows 10 or 11.
'''


def share_mods():
    """The mods that are on in the game's mods folder (not starting with _ or -), and the size table."""
    sys.path.insert(0, str(HERE))
    import nxsave
    # (from the Triforce game when there is one, whatever game the toolbox is set to now)
    triforce = next((p for app, p in nxsave.all_game_dirs() if app == 'Triforce'), None)
    mods = (triforce or nxsave.game_dir()) / 'mods'
    print('mods from:', mods)
    return sorted(p for p in mods.iterdir() if p.is_dir() and not p.name.startswith(('_', '-'))
                  and (p / 'romfs').is_dir()) if mods.is_dir() else []


def main():
    global PYTHON
    if '--python' in sys.argv:       # another Python 3.14 folder (with tkinter) to put in the zip
        PYTHON = Path(sys.argv[sys.argv.index('--python') + 1])
    if not (PYTHON / 'pythonw.exe').is_file():
        sys.exit(f'No Python at {PYTHON}: pass --python "<a Python 3.14 folder with pythonw.exe and tkinter>"')
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix('.zip.part')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        root = 'Link Toolbox/'
        z.writestr(root + 'Link Toolbox.bat', BAT.replace('\n', '\r\n'))
        readme = (HERE / 'README.txt').read_text(encoding='utf-8') if (HERE / 'README.txt').is_file() else README
        z.writestr(root + 'README.txt', readme.replace('\r\n', '\n').replace('\n', '\r\n'))
        if (HERE / 'LICENSE').is_file():
            z.write(HERE / 'LICENSE', root + 'LICENSE.txt')
        for name in APP:
            z.write(HERE / name, root + 'app/' + name)
        for name in OPTIONAL:
            if (HERE / name).is_file():
                z.write(HERE / name, root + 'app/' + name)
        if '--no-mods' not in sys.argv:
            shared = share_mods()
            for mod in shared:
                for p in sorted(mod.rglob('*')):
                    if p.is_file():
                        z.write(p, root + 'mods/' + mod.name + '/' + p.relative_to(mod).as_posix(),
                                compress_type=zipfile.ZIP_STORED if p.suffix == '.zs' else zipfile.ZIP_DEFLATED)
            print('mods:', ', '.join(m.name for m in shared) or 'none')
        n = 0
        for p in sorted(PYTHON.rglob('*')):
            rel = p.relative_to(PYTHON)
            if p.is_dir() or rel.parts[0] in SKIP_PY or '__pycache__' in rel.parts:
                continue
            z.write(p, root + 'python/' + rel.as_posix())
            n += 1
    tmp.replace(OUT)
    print(f'{OUT}  {OUT.stat().st_size / 1e6:.1f} MB  ({len(APP)} scripts, {n} Python files)')


if __name__ == '__main__':
    main()
