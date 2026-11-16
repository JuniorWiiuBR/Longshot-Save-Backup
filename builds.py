"""Several builds of a game app (Triforce, Longshot, NX2navi, ...), each in its own folder with its own "mods" folder.

New build: when the toolbox starts, a newer build of the app in use is spotted (its version file, else its program's
date). The mods are copied across (asking first, unless "Bring my mods to new builds without asking" is on) and the
toolbox switches to it; the old build is left as it was.

Shared mods folder (optional): one folder every build uses. Each build's "mods" folder becomes a link to it (a Windows
junction: no admin needed), so any app sees it as its own mods folder; new builds are linked as they are found.
Stopping removes the links (never the shared folder) and copies the mods back into each build.
"""
import os
import shutil
from pathlib import Path
from tkinter import messagebox

import nxsave

TITLE = "Link's Toolbox"


def same(a, b):
    try:
        return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))
    except OSError:
        return False


def mod_folders(mods):
    return sorted(p for p in Path(mods).iterdir() if p.is_dir() and (p / 'romfs').is_dir()) if Path(mods).is_dir() else []


def all_builds():
    """Every game folder found, once (Triforce and NX2navi can share one)."""
    out = []
    for _app, d in nxsave.all_game_dirs():
        if not any(same(d, o) for o in out):
            out.append(Path(d))
    return out


# ------------------------------------------------------------------------------------------------- new builds
def newer_build():
    """(app, version, folder, current folder) when a newer build of the app in use is found, else None."""
    game = nxsave.game_dir()
    app = nxsave.app_of(game)
    if app not in dict(nxsave.APPS):
        return None
    exe = dict(nxsave.APPS)[app]
    found = nxsave.builds_of(app)
    if not found:
        return None
    version, newest = found[0]
    if same(newest, game):
        return None
    if nxsave.version_key(version, newest, exe) <= nxsave.version_key(nxsave.build_version(game, app), game, exe):
        return None
    if nxsave.load_settings().get('build_skipped') == str(newest):
        return None                      # (said "not now" to this one already)
    return app, version, newest, game


def carry(old_game, new_game):
    """Copies the mods (on and off, and their order: the folder names) from the old build to the new one, leaving any
    the new build has already. Returns the names copied."""
    old_mods, new_mods = Path(old_game) / 'mods', Path(new_game) / 'mods'
    new_mods.mkdir(parents=True, exist_ok=True)
    copied = []
    for p in mod_folders(old_mods):
        if p.name.startswith('~'):        # (the size table: built again for the new build)
            continue
        if not (new_mods / p.name).exists():
            shutil.copytree(p, new_mods / p.name)
            copied.append(p.name)
    return copied


def switch_to(new_game, app):
    """The toolbox uses the new build from now on (its own mods and saves folders: the defaults)."""
    s = nxsave.load_settings()
    s.update({'game_dir': str(new_game), 'game_app': app, 'build_skipped': ''})
    old_mods = s.get('mods_dir', '')
    if old_mods and Path(old_mods).name == 'mods' and nxsave.is_game_dir(Path(old_mods).parent):
        s['mods_dir'] = ''               # (it pointed into the old build: the new build's own one now)
    nxsave.save_settings(s)


def rebuild_size_table(game):
    """The ~Size Table for the mods that are on, from that build's game files."""
    import size_table
    mods = nxsave.mods_dir_for(game)
    on = [p.name for p in mod_folders(mods) if not p.name.startswith(('_', '-', '~'))]
    if on:
        size_table.build(mods, on, log=lambda _s: None)


def plain(name):
    import re
    return re.sub(r'^(?:[-_]+)?(?:\d+-)?', '', name) or name


def check(parent):
    """At start: links new builds to the shared mods folder (when it is on), and offers (or, when set to, does) the
    move to a newer build of the app in use. True when the toolbox switched."""
    if nxsave.shared_folder():
        if parent is not None:
            import busy
            busy.run(parent, 'Linking new builds to the shared mods folder...', ensure_links)
        else:
            ensure_links()
    found = newer_build()
    if not found:
        return False
    app, version, newest, current = found
    shared = nxsave.shared_folder()
    mods = [] if shared else [p for p in mod_folders(Path(current) / 'mods') if not p.name.startswith('~')]
    auto = nxsave.load_settings().get('carry_mods') is True
    if not auto:
        what = (f'Your mods are in the shared mods folder, so the new build has them already.' if shared else
                f'Copy your {len(mods)} mod{"s" if len(mods) != 1 else ""} from the build you use now '
                f'({nxsave.build_version(current, app) or Path(current).name}) to it?' if mods else
                'The build you use now has no mods to bring.')
        if not messagebox.askyesno(f'{TITLE}: new {app} build',
                                   f'A newer {app} build was found: {version or newest.name}\n  {newest}\n\n{what}\n\n'
                                   'Yes: ' + ('copy them and ' if mods else '') + 'switch the toolbox to the new build '
                                   '(the old one is left as it is).\nNo: not now (this build is not offered again).',
                                   parent=parent):
            nxsave.save_settings({**nxsave.load_settings(), 'build_skipped': str(newest)})
            return False
    def work():
        got = carry(current, newest) if mods else []
        switch_to(newest, app)
        try:
            rebuild_size_table(newest)
        except Exception:
            pass                          # (the Mods tab's Save builds it too)
        return got
    if parent is not None:
        import busy
        copied = busy.run(parent, f'Bringing your mods to {app} {version or newest.name} and building its size '
                          'table...', work)
    else:
        copied = work()
    if not auto:
        messagebox.showinfo(TITLE, f'Now using {app} {version or newest.name}.' +
                            (f'\n\nCopied {len(copied)} mod{"s" if len(copied) != 1 else ""}: ' +
                             ', '.join(plain(n) for n in copied) if copied else ''), parent=parent)
    return True


# ------------------------------------------------------------------------------------------ shared mods folder
def link_build(game, shared):
    """Makes a build's mods folder a link to the shared folder; its own mods are moved into the shared one first
    (any that clash stay in 'mods (before sharing)'). True when it was linked now."""
    mods = Path(game) / 'mods'
    if nxsave.is_link(mods):
        if same(nxsave.link_target(mods), shared):
            return False
        nxsave.remove_link(mods)          # (a link somewhere else: pointed at the shared folder instead)
    elif mods.is_dir():
        for p in list(mods.iterdir()):
            if not (Path(shared) / p.name).exists() and not p.name.startswith('~'):
                shutil.move(str(p), str(Path(shared) / p.name))
        left = list(mods.iterdir())
        if left:
            keep = mods.with_name('mods (before sharing)')
            n = 2
            while keep.exists():
                keep, n = mods.with_name(f'mods (before sharing {n})'), n + 1
            mods.rename(keep)
        else:
            mods.rmdir()
    nxsave.make_link(mods, shared)
    return True


def ensure_links():
    """Sharing on: every build found (new ones too) uses the shared folder. Returns the builds linked now."""
    shared = nxsave.shared_folder()
    if not shared:
        return []
    Path(shared).mkdir(parents=True, exist_ok=True)
    done = []
    for game in all_builds():
        try:
            if link_build(game, shared):
                done.append(game)
        except OSError:
            pass
    return done


def start_sharing(shared):
    """Turns the shared mods folder on: every build's mods are moved into it, and their mods folders become links."""
    shared = Path(shared)
    shared.mkdir(parents=True, exist_ok=True)
    nxsave.save_settings({**nxsave.load_settings(), 'shared_mods': str(shared)})
    linked, failed = [], []
    for game in all_builds():
        try:
            link_build(game, shared)
            linked.append(game)
        except OSError as err:
            failed.append(f'{game}: {err}')
    try:
        rebuild_size_table(nxsave.game_dir())
    except Exception:
        pass
    return linked, failed


def stop_sharing(copy_back=True):
    """Turns it off: the links are removed (the shared folder itself is left as it is), and each build gets its own
    mods folder again, with a copy of the shared mods when copy_back."""
    shared = nxsave.shared_folder()
    done = []
    for game in all_builds():
        mods = Path(game) / 'mods'
        if nxsave.is_link(mods) and (shared is None or same(nxsave.link_target(mods), shared)):
            nxsave.remove_link(mods)
            mods.mkdir(exist_ok=True)
            if copy_back and shared:
                for p in mod_folders(shared):
                    if not p.name.startswith('~') and not (mods / p.name).exists():
                        shutil.copytree(p, mods / p.name)
            done.append(game)
            try:
                rebuild_size_table(game)
            except Exception:
                pass
    s = nxsave.load_settings()
    s['shared_mods'] = ''
    nxsave.save_settings(s)
    if nxsave.shared_mods():              # (the Longshot-only HOS_MODS of v1.1.7, when it was set)
        try:
            nxsave.set_shared_mods(None)
        except OSError:
            pass
    return done
