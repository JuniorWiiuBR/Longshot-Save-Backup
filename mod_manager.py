"""
Lógica dos mods (sem interface): listar, ligar/desligar, ordenar, adicionar (pasta ou .zip) e a tabela de tamanhos.

Adaptado do mod loader do "Link's Toolbox" (por Cum_Dumpster), cujos arquivos nxsave.py e size_table.py
vão junto, sem alterações. Aqui o "jogo" é uma build do Longshot: <build>\\mods.

Como o jogo lê a pasta mods:
    pasta que começa com - ou _  = desligada
    quando dois mods trazem o mesmo arquivo, vence a pasta cujo nome vem por último
Por isso um mod ligado se chama "NN-<nome>" (NN = posição; o último da lista tem o maior número e vence)
e um mod desligado se chama "_<nome>". A pasta "~Size Table" é gerada ao salvar (size_table.py).
"""
import os
import re
import shutil
import tempfile
import threading
import zipfile
from pathlib import Path

PREFIX = re.compile(r'^(?:[-_]+)?(?:\d+-)?')
SIZE_TABLE_FOLDER = '~Size Table'
_override_lock = threading.Lock()


def plain(folder):
    return PREFIX.sub('', folder) or folder


def list_builds(builds_dir):
    """Builds da mais antiga para a mais nova (data de criação)."""
    try:
        items = [os.path.join(builds_dir, d) for d in os.listdir(builds_dir)]
    except Exception:
        return []
    items = [Path(p) for p in items if os.path.isdir(p)]
    items.sort(key=lambda p: os.path.getctime(p))
    return items


class Mod:
    def __init__(self, mods_dir, folder):
        self.folder = folder                      # nome atual em disco
        self.name = plain(folder)
        self.on = not folder.startswith(('-', '_'))
        romfs = Path(mods_dir) / folder / 'romfs'
        self.loads = romfs.is_dir()               # o jogo só carrega mods com romfs
        self.files = set()
        if self.loads:
            for root, _d, names in os.walk(romfs):
                for n in names:
                    self.files.add((Path(root) / n).relative_to(romfs).as_posix().lower())

    @property
    def active(self):
        return self.on and self.loads

    def target(self, place):
        return f'{place:02d}-{self.name}' if self.active else f'_{self.name}'


def scan(mods_dir):
    """Mods da pasta (as pastas que começam com ~ são do próprio loader e não aparecem)."""
    mods_dir = Path(mods_dir)
    if not mods_dir.is_dir():
        return []
    mods = [Mod(mods_dir, p.name) for p in mods_dir.iterdir()
            if p.is_dir() and not p.name.endswith('.old') and not p.name.startswith(('~', '.'))]
    mods.sort(key=lambda m: (not m.active, m.folder.lower() if m.active else m.name.lower()))
    return mods


def clashes(mods):
    """{nome: [(outro, qtd de arquivos em comum, este vence?)]} entre os mods ligados, na ordem da lista."""
    on = [m for m in mods if m.active]
    out = {m.name: [] for m in on}
    for i, a in enumerate(on):
        for j, b in enumerate(on):
            if a is not b:
                n = len(a.files & b.files)
                if n:
                    out[a.name].append((b.name, n, i > j))
    return out


# ------------------------------------------------------------------ tabela de tamanhos
def size_table_status():
    """(True, '') se dá para gerar a tabela de tamanhos; senão (False, motivo)."""
    try:
        import nxsave
    except Exception as e:
        return False, str(e)
    if nxsave.zstd is None:
        return False, 'py314'
    return True, ''


def build_size_table(build_dir, mods_dir, enabled_folders):
    """Gera (ou remove) a pasta ~Size Table para os mods ligados. Retorna quantas entradas mudaram."""
    import nxsave
    import size_table
    with _override_lock:
        previous = nxsave.SETTINGS_OVERRIDE
        nxsave.SETTINGS_OVERRIDE = {'game_dir': str(build_dir)}
        try:
            changed = size_table.build(Path(mods_dir), list(enabled_folders), log=lambda _s: None)
        finally:
            nxsave.SETTINGS_OVERRIDE = previous
    return len(changed)


def refresh_size_table(build_dir, mods_dir):
    """Refaz a tabela para os mods ligados dessa build. Retorna (estado, detalhe):
    ('built', n) | ('none', 0) | ('skip', motivo) | ('error', mensagem)."""
    ok, why = size_table_status()
    if not ok:
        return 'skip', why
    try:
        folders = [m.folder for m in scan(mods_dir) if m.active]
        n = build_size_table(build_dir, mods_dir, folders)
        return ('built', n) if n else ('none', 0)
    except Exception as e:
        return 'error', str(e)


# ------------------------------------------------------------------ salvar
def apply(build_dir, mods_dir, mods):
    """Renomeia as pastas para os nomes-alvo (passando por nomes temporários) e atualiza a tabela de tamanhos.
    Retorna (renomeadas, (estado, detalhe) da tabela)."""
    mods_dir = Path(mods_dir)
    on = [m for m in mods if m.active]
    plan = []
    for m in mods:
        new = m.target(on.index(m) + 1 if m in on else 0)
        if new != m.folder:
            plan.append((m, new))
    if len({m.name for m in mods}) != len(mods):
        raise ValueError('duas pastas têm o mesmo nome sem o prefixo / two folders share the same name')
    temp = []
    for m, new in plan:
        t = mods_dir / f'.renaming-{m.name}'
        (mods_dir / m.folder).rename(t)
        temp.append((m, t, new))
    for m, t, new in temp:
        t.rename(mods_dir / new)
        m.folder = new
    state = refresh_size_table(build_dir, mods_dir)
    return len(temp), state


# ------------------------------------------------------------------ adicionar
def collect(src, root_name=None, depth=3):
    """[(pasta, nome)] dos mods dentro de src: uma pasta com romfs é um mod; senão procura até `depth` níveis."""
    src = Path(src)
    if (src / 'romfs').is_dir():
        return [(src, root_name or plain(src.name))]
    found = []

    def walk(d, level):
        try:
            kids = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            return
        for k in kids:
            if (k / 'romfs').is_dir():
                found.append((k, plain(k.name)))
            elif level > 0 and not k.name.startswith('.'):
                walk(k, level - 1)
    walk(src, depth)
    return found


def extract_zip(zip_path):
    """Extrai o .zip numa pasta temporária (com proteção contra caminhos fora da pasta). Retorna a pasta."""
    work = Path(tempfile.mkdtemp(prefix='lsb-mod-'))
    base = work.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            dest = (work / info.filename).resolve()
            if base != dest and base not in dest.parents:
                shutil.rmtree(work, ignore_errors=True)
                raise ValueError(f'caminho inseguro no zip: {info.filename}')
        z.extractall(work)
    return work


def install(mods_dir, items, replace):
    """Copia mods [(pasta, nome)] para a pasta mods. replace(nome) diz se sobrescreve um mod que já existe
    (mesmo nome sem prefixo). Retorna (adicionados, substituídos, ignorados)."""
    mods_dir = Path(mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)
    have = {plain(p.name).lower(): p for p in mods_dir.iterdir() if p.is_dir() and not p.name.startswith('~')}
    added, replaced, skipped = [], [], []
    for i, (src, name) in enumerate(items):
        old = have.get(name.lower())
        if old is not None:
            if not replace(name):
                skipped.append(name)
                continue
            shutil.rmtree(old)
            replaced.append(name)
        else:
            added.append(name)
        # um mod novo entra ligado, depois dos outros: "Salvar" numera direito
        dest = mods_dir / f'9{i:02d}-{name}'
        shutil.copytree(src, dest)
        have[name.lower()] = dest
    return added, replaced, skipped


# ------------------------------------------------------------------ jogo
def game_running():
    """Nome do programa do jogo se estiver aberto, senão ''."""
    try:
        import nxsave
        return nxsave.game_running()
    except Exception:
        return ''


def game_exe(build_dir):
    try:
        import nxsave
        for exe in nxsave.GAME_EXES:
            p = nxsave.program(build_dir, exe)
            if p:
                return p
    except Exception:
        pass
    return None
