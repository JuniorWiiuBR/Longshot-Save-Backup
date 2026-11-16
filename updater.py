"""Updates for Link's Tool Box from its GitHub releases (Windows): find the latest release, download its Windows zip,
and put it in place of this copy once the toolbox has closed, keeping what is the player's own (settings, backups,
the names read from the game, the icon picked), then start the toolbox again.

    latest()                     the newest release: {'version', 'notes', 'url', 'size', 'page'}
    is_newer(version)            whether it is newer than this copy (VERSION)
    can_update()                 '' when this copy can update itself, else why not
    start(url, progress)         downloads and unpacks; then the toolbox closes and a small script copies it in
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import nxsave

VERSION = nxsave.VERSION
REPO = 'losava/Links-Toolbox'
API = f'https://api.github.com/repos/{REPO}/releases/latest'
ASSET = 'Link.Toolbox.zip'                  # the Windows download's name on GitHub
APP = Path(__file__).resolve().parent      # ...\Link Toolbox\app
ROOT = APP.parent                          # ...\Link Toolbox
AGENT = 'Link-Toolbox-updater'             # (no personal details are sent: just this name)
# the player's own files, never replaced by an update
KEEP_FILES = ('toolbox_settings.json', 'names-cache-*.json', 'names-cache.json', 'icon.ico', 'icon.png',
              'Link Toolbox.lnk', "Link's Tool Box.lnk", 'toolbox.log')
KEEP_DIRS = ('backups',)


def parse(version):
    """'v1.1.6' -> (1, 1, 6)"""
    return tuple(int(x) for x in re.findall(r'\d+', version or '')[:3]) or (0,)


def is_newer(version):
    return parse(version) > parse(VERSION)


def latest(timeout=15):
    req = urllib.request.Request(API, headers={'User-Agent': AGENT, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        rel = json.loads(r.read())
    asset = next((a for a in rel.get('assets', []) if a.get('name') == ASSET), None)
    return {'version': rel.get('tag_name', ''), 'notes': rel.get('body') or '', 'page': rel.get('html_url', ''),
            'url': asset and asset.get('browser_download_url'), 'size': asset and asset.get('size')}


def can_update():
    """'' when this copy can update itself, else the reason it can't."""
    if os.name != 'nt':
        return 'Updating by itself is for the Windows download. On Linux, download the new version from GitHub.'
    if (APP / '.git').exists():
        return 'This copy is a development folder (git): update it with git, not here.'
    if not (ROOT / 'python' / 'pythonw.exe').is_file():
        return "This copy is not the one from the Link's Tool Box download (no python folder next to it)."
    try:
        probe = ROOT / '.update-test'
        probe.write_text('x')
        probe.unlink()
    except OSError:
        return f'{ROOT} cannot be written to.'
    return ''


def download(url, dest, progress=lambda done, total: None):
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        done = 0
        while True:
            chunk = r.read(1 << 18)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            progress(done, total)


def unpack(zip_path, work):
    """Unpacks the download; returns its 'Link Toolbox' folder after checking it is one."""
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(work)
    new = Path(work) / 'Link Toolbox'
    for need in ('app/toolbox.pyw', 'app/nxsave.py', 'python/pythonw.exe'):
        if not (new / need).is_file():
            raise ValueError(f"the download has no {need}: not a Link's Tool Box download")
    return new


SCRIPT = r'''@echo off
rem Link's Tool Box update: waits for the toolbox to close, copies the new version in, starts it again.
title Updating Link's Tool Box
:wait
tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul && (timeout /t 1 /nobreak >nul & goto wait)
robocopy "{new}" "{root}" /E /XF {keep_files} /XD {keep_dirs} /R:5 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo The update could not be copied in. Close every Link's Tool Box window and try again.
  pause
  exit /b 1
)
{restart}
rd /s /q "{work}" 2>nul
'''


def start(source, progress=lambda done, total: None, restart=True):
    """Downloads the new version (source: its URL, or a local zip) and unpacks it, then starts the script that copies it
    in once this toolbox has closed. The caller closes the toolbox right after."""
    why = can_update()
    if why:
        raise RuntimeError(why)
    work = Path(tempfile.mkdtemp(prefix='link-toolbox-update-'))
    zip_path = work / 'Link Toolbox.zip'
    if re.match(r'https?://', str(source)):
        download(source, zip_path, progress)
    else:
        shutil.copy(source, zip_path)
    new = unpack(zip_path, work / 'new')
    script = work / 'update.bat'
    again = f'start "" "{ROOT}\\python\\pythonw.exe" "{ROOT}\\app\\toolbox.pyw"' if restart else 'rem (no restart)'
    script.write_text(SCRIPT.format(pid=os.getpid(), new=new, root=ROOT, work=work, restart=again,
                                    keep_files=' '.join(f'"{k}"' for k in KEEP_FILES),
                                    keep_dirs=' '.join(f'"{k}"' for k in KEEP_DIRS)), encoding='mbcs')
    subprocess.Popen(['cmd', '/c', str(script)], cwd=str(work),
                     creationflags=subprocess.CREATE_NEW_CONSOLE if '--show-update' in sys.argv
                     else getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return script
