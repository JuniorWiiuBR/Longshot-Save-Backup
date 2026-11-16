"""New Longshot builds: Longshot's launcher builds every version into a new folder, whose mods folder starts empty. When
the toolbox starts (and Longshot is the game in use), a newer build is spotted: the mods are copied across (asking
first, unless "Bring my mods to new builds automatically" is on) and the toolbox switches to the new build. The old
build is left as it was. With a shared mods folder (HOS_MODS) there is nothing to copy: only the switch.
"""
import os
import shutil
from pathlib import Path
from tkinter import messagebox

import nxsave


def same(a, b):
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


def mod_folders(mods):
    return sorted(p for p in Path(mods).iterdir() if p.is_dir() and (p / 'romfs').is_dir()) if Path(mods).is_dir() else []


def newer_build():
    """(version, folder, current folder) when a Longshot build newer than the one in use is found, else None."""
    game = nxsave.game_dir()
    if nxsave.app_of(game) != 'Longshot':
        return None
    builds = nxsave.longshot_builds()
    if not builds:
        return None
    version, newest = builds[0]
    if same(newest, game):
        return None
    if nxsave.version_key(version, newest) <= nxsave.version_key(nxsave.longshot_version(game), game):
        return None
    if nxsave.load_settings().get('longshot_build_skipped') == str(newest):
        return None                      # (said "not now" to this one already)
    return version, newest, game


def carry(old_game, new_game, log=lambda text: None):
    """Copies the mods (on and off, and their order: the folder names) from the old build to the new one, leaving any
    the new build has already; then builds the size table there. Returns the names copied."""
    old_mods, new_mods = Path(old_game) / 'mods', Path(new_game) / 'mods'
    new_mods.mkdir(parents=True, exist_ok=True)
    copied = []
    for p in mod_folders(old_mods):
        if p.name.startswith('~'):        # (the size table: built again below, for the new build's own game files)
            continue
        if not (new_mods / p.name).exists():
            shutil.copytree(p, new_mods / p.name)
            copied.append(p.name)
    return copied


def switch_to(new_game):
    """The toolbox uses the new build from now on (its own mods and saves folders: the defaults)."""
    s = nxsave.load_settings()
    old_mods = s.get('mods_dir', '')
    s.update({'game_dir': str(new_game), 'game_app': 'Longshot', 'longshot_build_skipped': ''})
    if old_mods and Path(old_mods).name == 'mods' and nxsave.program(Path(old_mods).parent, 'longshot.exe'):
        s['mods_dir'] = ''               # (it pointed into the old build: the new build's own one now)
    nxsave.save_settings(s)


def rebuild_size_table(new_game):
    """The ~Size Table for the mods that are on, from the new build's game files."""
    import size_table
    mods = nxsave.mods_dir_for(new_game, 'Longshot')
    on = [p.name for p in mod_folders(mods) if not p.name.startswith(('_', '-', '~'))]
    if on:
        size_table.build(mods, on, log=lambda _s: None)


def check(parent):
    """At start: offers (or, when set to, does) the move to a newer Longshot build. True when the toolbox switched."""
    found = newer_build()
    if not found:
        return False
    version, newest, current = found
    shared = nxsave.shared_mods()
    mods = [] if shared else [p for p in mod_folders(Path(current) / 'mods') if not p.name.startswith('~')]
    auto = nxsave.load_settings().get('carry_mods') is True
    if not auto:
        what = (f'Your mods are in the shared mods folder ({shared}), so the new build uses them already.'
                if shared else f'Copy your {len(mods)} mod{"s" if len(mods) != 1 else ""} from the build you use now '
                f'({nxsave.longshot_version(current) or Path(current).name}) to it?' if mods else
                'The build you use now has no mods to bring.')
        if not messagebox.askyesno("Link's Toolbox: new Longshot build",
                                   f'A newer Longshot build was found: {version or newest.name}\n  {newest}\n\n{what}\n\n'
                                   'Yes: ' + ('copy them and ' if mods else '') + 'switch the toolbox to the new build '
                                   '(the old one is left as it is).\nNo: not now (this build is not offered again).',
                                   parent=parent):
            nxsave.save_settings({**nxsave.load_settings(), 'longshot_build_skipped': str(newest)})
            return False
    copied = carry(current, newest) if mods else []
    switch_to(newest)
    try:
        rebuild_size_table(newest)
    except Exception:
        pass                              # (the Mods tab's Save builds it too)
    if not auto:
        messagebox.showinfo("Link's Toolbox", f'Now using Longshot {version or newest.name}.' +
                            (f'\n\nCopied {len(copied)} mod{"s" if len(copied) != 1 else ""}: ' + ', '.join(
                                nxsave_plain(n) for n in copied) if copied else ''), parent=parent)
    return True


def nxsave_plain(name):
    import re
    return re.sub(r'^(?:[-_]+)?(?:\d+-)?', '', name) or name
