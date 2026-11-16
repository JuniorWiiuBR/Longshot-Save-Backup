"""
Longshot Save Backup
- Vigia a pasta "builds" do Longshot Launcher.
- Quando surge uma build nova (ex.: nightly-123-abcd1234) e ela cria a sua pasta "user",
  COPIA as pastas "user" e "mods" da build antiga para a nova e, ao mesmo tempo, faz o
  backup da pasta "user" antiga no Google Drive (o backup é só da "user").
- Aba "Mods": adiciona mods (pasta ou .zip), liga/desliga, ordena e salva por build
  (lógica adaptada do Link's Toolbox, de Cum_Dumpster).
- Música de fundo (background.mp3) sempre tocando em loop, volume fixo em 40%.
- Idiomas: Português (Brasil) e English. Aba de ajuda inclusa. Fundo animado de triforces.

Só usa a biblioteca padrão do Python (tkinter incluso). Áudio via Windows MCI.
"""
import ctypes
import datetime
import json
import os
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog

import mod_manager as mm
from mods_tab import ModsTab
from ui_common import (APP_VERSION, BG, CARD, CARD2, GOLD, FG, MUTED, LINE,
                       FlatButton, TriforceBackground, load_logo)

APP_NAME = "Longshot Save Backup"
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LongshotSaveBackup")
CFG_FILE = os.path.join(CFG_DIR, "config.json")
USER_DIR = "user"
MODS_DIR = "mods"
BACKUP_ROOT = "LongshotSaves"
POLL_SECONDS = 5
MUSIC_VOLUME = 40  # fixo, em %

DEFAULT_CFG = {
    "builds": "",
    "dest": "",
    "known": [],
    "lang": "pt",
}

# ---------------------------------------------------------------- textos
HELP_PT = 'PRIMEIROS PASSOS (passo a passo)\n\n1) Instale o Google Drive para computador\n   Baixe em google.com/drive/download, instale e entre com a sua conta Google. Ele cria uma unidade (ou pasta) chamada "Google Drive" no Explorador de Arquivos; a letra da unidade pode variar de PC para PC. É por ela que o backup chega à nuvem.\n\n2) Crie a pasta do backup no Google Drive\n   a) Abra o Explorador de Arquivos e entre em "Google Drive" > "Meu Drive".\n   b) Clique com o botão direito num espaço vazio > Novo > Pasta.\n   c) Dê um nome, por exemplo "Longshot Backup".\n   (Dá para usar o próprio "Meu Drive", mas uma pasta só para isso deixa tudo mais organizado.)\n\n3) Diga ao programa onde estão as pastas (aba Principal)\n   - "Pasta das builds": clique em Procurar e escolha a pasta "builds", que fica dentro da pasta de dados do Longshot Launcher (LongshotLauncher-data), no lugar onde você instalou o jogo. Dentro dela ficam as pastas de cada versão do jogo, com nomes parecidos com nightly-123-abcd1234.\n   - "Pasta do Google Drive": clique em Procurar e escolha a pasta que você criou no passo 2. O programa tenta achar o seu "Meu Drive" sozinho, mas confira se é a pasta certa.\n\n4) Clique em "Iniciar detecção de builds" e deixe o programa aberto (pode minimizar).\n   Na primeira vez, as builds que já existem são ignoradas: só as builds novas disparam a cópia.\n\nO QUE ACONTECE\n\nQuando o jogo atualiza e cria uma build nova com uma pasta user dentro, o programa:\n  - COPIA a pasta user e a pasta mods da build antiga para a build nova;\n  - ao mesmo tempo, faz o backup da user antiga no Google Drive (só a user vai para o Drive, a mods não).\nAs pastas da build antiga continuam intactas: nada é movido nem apagado.\n\nABA MODS\n\nEscolha a build (por padrão a mais nova) e gerencie os mods dela:\n  - "Adicionar pasta..." / "Adicionar .zip...": um mod é uma pasta com uma pasta "romfs" dentro. Pode escolher um ou vários .zip; o programa acha os mods lá dentro.\n  - Duplo clique (ou "Ligar/Desligar") liga e desliga. "Subir"/"Descer" mudam a ordem: quando dois mods trocam o mesmo arquivo, vence o que está mais embaixo.\n  - Nada muda de verdade até clicar em "Salvar" (ele renomeia as pastas e atualiza a tabela de tamanhos que os mods ligados precisam). "Salvar e jogar" salva e abre o jogo.\n  - Feche o jogo antes de adicionar ou salvar mods.\nQuando uma build nova é detectada, os mods são copiados e a tabela de tamanhos é refeita para a build nova.\n\nDICAS\n\n- O backup fica em: <sua pasta do Drive>\\LongshotSaves\\user. O programa nunca apaga nada lá.\n- Não existe backup automático: ele só acontece junto com a cópia.\n- "Copiar user agora" (aba Principal) faz a cópia (user e mods) e o backup na hora, entre as duas builds mais recentes.\n- Se a cópia falhar (jogo ou launcher abertos), feche-os: o programa tenta de novo sozinho.\n- Se o backup não chegar ao Drive, abra o app Google Drive (perto do relógio do Windows) e confira se ele está conectado e sincronizando.\n- A música de fundo toca sempre enquanto o programa estiver aberto (volume fixo em 40%).\n- Idioma: use os botões PT-BR / EN no canto superior direito.'

HELP_EN = 'FIRST STEPS (step by step)\n\n1) Install Google Drive for desktop\n   Download it at google.com/drive/download, install it and sign in with your Google account. It creates a drive (or folder) called "Google Drive" in File Explorer; the drive letter can differ from PC to PC. That is how the backup reaches the cloud.\n\n2) Create the backup folder on Google Drive\n   a) Open File Explorer and go to "Google Drive" > "My Drive".\n   b) Right-click an empty space > New > Folder.\n   c) Give it a name, for example "Longshot Backup".\n   (You can use "My Drive" itself, but a folder just for this keeps things tidy.)\n\n3) Tell the program where the folders are (Main tab)\n   - "Builds folder": click Browse and choose the "builds" folder, which is inside the Longshot Launcher data folder (LongshotLauncher-data), wherever you installed the game. Inside it are the folders for each game version, with names like nightly-123-abcd1234.\n   - "Google Drive folder": click Browse and choose the folder you created in step 2. The program tries to find your "My Drive" by itself, but check that it is the right one.\n\n4) Click "Start build detection" and keep the program open (you can minimize it).\n   The first time, builds that already exist are ignored: only new builds trigger the copy.\n\nWHAT HAPPENS\n\nWhen the game updates and creates a new build with a user folder inside, the program:\n  - COPIES the user folder and the mods folder from the old build to the new build;\n  - at the same time, backs the old user folder up to Google Drive (only user goes to the Drive, not mods).\nThe old build\'s folders stay untouched: nothing is moved or deleted.\n\nMODS TAB\n\nPick the build (the newest by default) and manage its mods:\n  - "Add folder..." / "Add .zip...": a mod is a folder with a "romfs" folder inside. You can pick one or several .zip files; the program finds the mods inside.\n  - Double-click (or "Turn on/off") switches a mod. "Move up"/"Move down" change the order: when two mods replace the same file, the lower one wins.\n  - Nothing really changes until you click "Save" (it renames the folders and updates the size table the mods that are on need). "Save and play" saves and opens the game.\n  - Close the game before adding or saving mods.\nWhen a new build is detected, the mods are copied and the size table is rebuilt for the new build.\n\nTIPS\n\n- The backup lives in: <your Drive folder>\\LongshotSaves\\user. The program never deletes anything there.\n- There is no automatic backup: it only happens together with the copy.\n- "Copy user now" (Main tab) does the copy (user and mods) and the backup right away, between the two newest builds.\n- If the copy fails (game or launcher open), close them: the program retries by itself.\n- If the backup does not reach the Drive, open the Google Drive app (near the Windows clock) and check that it is connected and syncing.\n- The background music always plays while the program is open (volume fixed at 40%).\n- Language: use the PT-BR / EN buttons at the top right.'

TR = {
    "pt": {
        "title": "Longshot Save Backup",
        "tab_main": "Principal",
        "tab_help": "Ajuda",
        "builds": "Pasta das builds",
        "dest": "Pasta do Google Drive",
        "browse": "Procurar",
        "desc": "Quando uma build nova for detectada: as pastas user e mods antigas são COPIADAS para a nova "
                "e, ao mesmo tempo, a pasta user é enviada em backup para o Drive (o backup é só da user).",
        "start": "Iniciar detecção de builds",
        "stop": "Parar detecção de builds",
        "copy_now": "Copiar user agora",
        "st_idle": "● Parado",
        "st_wait": "● Aguardando build nova...",
        "log_choose_drive": "Primeiro uso: escolha a pasta das builds e a pasta do Google Drive (veja o passo a passo na aba Ajuda) e clique em Iniciar detecção de builds.",
        "log_started": "Detecção de builds iniciada. (Sem backup automático: só ao copiar a user.)",
        "log_stopped": "Detecção de builds parada.",
        "log_no_builds": "Escolha a pasta das builds (a pasta \"builds\" dentro de LongshotLauncher-data).",
        "log_no_drive": "Escolha a pasta do Google Drive (veja na aba Ajuda como criá-la).",
        "log_detected": "Build nova detectada: {name}. Aguardando terminar de gravar...",
        "log_new": "Build nova: {new} | user antiga: {old}",
        "log_no_old": "{name}: sem build antiga com user para copiar.",
        "log_copy_ok": "Cópia concluída: user -> {name}",
        "log_mods_ok": "Cópia concluída: mods -> {name}",
        "log_mods_err": "Erro ao copiar a pasta mods ({err}).",
        "log_copy_err": "Erro ao copiar a user ({err}). Feche o jogo/launcher; tentarei de novo.",
        "log_bkp_ok": "Backup concluído: {n} arquivo(s) enviados para {path}",
        "log_bkp_err": "Erro no backup ({err}).",
        "log_drive_off": "Backup: pasta do Google Drive indisponível.",
        "log_one_build": "Só existe uma build; nada para copiar.",
        "log_err": "Erro: {err}",
        "tab_mods": "Mods",
        "mods_title": "Mods",
        "mods_build": "Build",
        "mods_refresh": "Atualizar",
        "mods_open": "Abrir pasta mods",
        "mods_col_n": "#",
        "mods_col_state": "Estado",
        "mods_col_name": "Mod",
        "mods_on": "Ligado",
        "mods_off": "Desligado",
        "mods_noromfs": "Sem romfs",
        "mods_add_folder": "Adicionar pasta...",
        "mods_add_zip": "Adicionar .zip...",
        "mods_toggle": "Ligar/Desligar",
        "mods_up": "Subir",
        "mods_down": "Descer",
        "mods_save": "Salvar",
        "mods_save_play": "Salvar e jogar",
        "mods_none": "Nenhuma build encontrada. Confira a pasta das builds na aba Principal.",
        "mods_no_folder": "Esta build ainda não tem a pasta mods. Adicione um mod para criá-la.",
        "mods_count": "{n} mod(s) nesta build",
        "mods_dirty": "● alterações não salvas",
        "mods_saved": "Salvo.",
        "mods_saving": "Salvando...",
        "mods_extracting": "Extraindo o zip...",
        "mods_hint": "Duplo clique liga/desliga. O que fica mais embaixo vence quando dois mods trocam o mesmo arquivo.",
        "mods_clash": "{name} troca {n} arquivo(s) que {other} também troca: {who}.",
        "mods_wins": "este vence",
        "mods_loses": "o outro vence",
        "mods_game_open": "Feche o jogo ({game}) antes de mexer nos mods.",
        "mods_discard": "Esquecer as alterações que você ainda não salvou?",
        "mods_pick_folder": "Pasta de um mod (com romfs dentro) ou pasta com vários mods",
        "mods_pick_zip": "Escolha o(s) .zip do(s) mod(s)",
        "mods_none_found": "Não achei mods em:\n{src}\n\nUm mod é uma pasta com uma pasta \"romfs\" dentro.",
        "mods_replace_q": "\"{name}\" já existe. Substituir por esta cópia?",
        "mods_added": "Adicionados: {n}. Clique em Salvar para usar.",
        "mods_nothing": "Nada novo para adicionar.",
        "mods_copy_err": "Não foi possível copiar os mods:\n{err}",
        "mods_save_err": "Não foi possível salvar os mods:\n{err}",
        "mods_zip_err": "Não foi possível abrir {zip}:\n{err}",
        "mods_no_exe": "Não achei o executável do jogo nesta build.",
        "mods_cannot_on": "Este mod não tem pasta romfs, então o jogo não o carrega.",
        "log_mods_added": "Mods adicionados: {n}. (Clique em Salvar na aba Mods para usar.)",
        "log_mods_saved": "Mods salvos na build {name}: {n} pasta(s) renomeada(s).",
        "log_st_built": "Tabela de tamanhos atualizada ({n} entradas alteradas).",
        "log_st_none": "Nenhum mod ligado precisa de tabela de tamanhos; vale a do próprio jogo.",
        "log_st_skip": "Tabela de tamanhos NÃO gerada: {why}",
        "log_st_err": "Erro ao gerar a tabela de tamanhos ({err}).",
        "st_py314": "o programa foi compilado com um Python anterior ao 3.14, que essa tabela exige.",
        "log_music_missing": "Música de fundo não encontrada (background.mp3).",
        "log_music_err": "Não consegui tocar a música de fundo.",
        "help": HELP_PT,
    },
    "en": {
        "title": "Longshot Save Backup",
        "tab_main": "Main",
        "tab_help": "Help",
        "builds": "Builds folder",
        "dest": "Google Drive folder",
        "browse": "Browse",
        "desc": "When a new build is detected: the old user and mods folders are COPIED to the new one "
                "and, at the same time, the user folder is backed up to the Drive (only user is backed up).",
        "start": "Start build detection",
        "stop": "Stop build detection",
        "copy_now": "Copy user now",
        "st_idle": "● Stopped",
        "st_wait": "● Waiting for a new build...",
        "log_choose_drive": "First use: choose the builds folder and the Google Drive folder (see the step by step on the Help tab) and click Start build detection.",
        "log_started": "Build detection started. (No automatic backup: only when copying the user folder.)",
        "log_stopped": "Build detection stopped.",
        "log_no_builds": "Choose the builds folder (the \"builds\" folder inside LongshotLauncher-data).",
        "log_no_drive": "Choose the Google Drive folder (see the Help tab for how to create it).",
        "log_detected": "New build detected: {name}. Waiting for it to finish writing...",
        "log_new": "New build: {new} | old user: {old}",
        "log_no_old": "{name}: no older build with a user folder to copy.",
        "log_copy_ok": "Copy finished: user -> {name}",
        "log_mods_ok": "Copy finished: mods -> {name}",
        "log_mods_err": "Error copying the mods folder ({err}).",
        "log_copy_err": "Error copying the user folder ({err}). Close the game/launcher; I'll retry.",
        "log_bkp_ok": "Backup finished: {n} file(s) sent to {path}",
        "log_bkp_err": "Backup error ({err}).",
        "log_drive_off": "Backup: Google Drive folder unavailable.",
        "log_one_build": "There is only one build; nothing to copy.",
        "log_err": "Error: {err}",
        "tab_mods": "Mods",
        "mods_title": "Mods",
        "mods_build": "Build",
        "mods_refresh": "Refresh",
        "mods_open": "Open mods folder",
        "mods_col_n": "#",
        "mods_col_state": "State",
        "mods_col_name": "Mod",
        "mods_on": "On",
        "mods_off": "Off",
        "mods_noromfs": "No romfs",
        "mods_add_folder": "Add folder...",
        "mods_add_zip": "Add .zip...",
        "mods_toggle": "Turn on/off",
        "mods_up": "Move up",
        "mods_down": "Move down",
        "mods_save": "Save",
        "mods_save_play": "Save and play",
        "mods_none": "No build found. Check the builds folder on the Main tab.",
        "mods_no_folder": "This build has no mods folder yet. Add a mod to create it.",
        "mods_count": "{n} mod(s) in this build",
        "mods_dirty": "● unsaved changes",
        "mods_saved": "Saved.",
        "mods_saving": "Saving...",
        "mods_extracting": "Extracting the zip...",
        "mods_hint": "Double-click turns a mod on/off. The lower one in the list wins when two mods replace the same file.",
        "mods_clash": "{name} replaces {n} file(s) that {other} also replaces: {who}.",
        "mods_wins": "this one wins",
        "mods_loses": "the other one wins",
        "mods_game_open": "Close the game ({game}) before changing mods.",
        "mods_discard": "Forget the changes you have not saved?",
        "mods_pick_folder": "A mod folder (with romfs inside) or a folder with several mods",
        "mods_pick_zip": "Choose the mod .zip file(s)",
        "mods_none_found": "No mods found in:\n{src}\n\nA mod is a folder with a \"romfs\" folder inside.",
        "mods_replace_q": "\"{name}\" is already there. Replace it with this copy?",
        "mods_added": "Added: {n}. Click Save to use them.",
        "mods_nothing": "Nothing new to add.",
        "mods_copy_err": "The mods could not be copied:\n{err}",
        "mods_save_err": "The mods could not be saved:\n{err}",
        "mods_zip_err": "Could not open {zip}:\n{err}",
        "mods_no_exe": "Could not find the game program in this build.",
        "mods_cannot_on": "This mod has no romfs folder, so the game does not load it.",
        "log_mods_added": "Mods added: {n}. (Click Save on the Mods tab to use them.)",
        "log_mods_saved": "Mods saved in build {name}: {n} folder(s) renamed.",
        "log_st_built": "Size table updated ({n} entries changed).",
        "log_st_none": "No mod that is on needs a size table; the game's own is used.",
        "log_st_skip": "Size table NOT generated: {why}",
        "log_st_err": "Error generating the size table ({err}).",
        "st_py314": "the program was built with a Python older than 3.14, which that table needs.",
        "log_music_missing": "Background music not found (background.mp3).",
        "log_music_err": "Could not play the background music.",
        "help": HELP_EN,
    },
}


# ---------------------------------------------------------------- recursos / config
def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if not cfg["dest"]:
        cfg["dest"] = detect_drive()
    if cfg["lang"] not in TR:
        cfg["lang"] = "pt"
    return cfg


def save_cfg(cfg):
    os.makedirs(CFG_DIR, exist_ok=True)
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def detect_drive():
    names = ["Meu Drive", "My Drive"]
    for letter in "GHIJKLMNOPQRSTUVWXYZ":
        for n in names:
            p = f"{letter}:\\{n}"
            if os.path.isdir(p):
                return p
    home = os.path.expanduser("~")
    for p in (os.path.join(home, "Google Drive"), os.path.join(home, "Meu Drive")):
        if os.path.isdir(p):
            return p
    return ""


_mutex_handle = None


def ensure_single_instance():
    """Evita abrir duas cópias (duas músicas tocando ao mesmo tempo)."""
    global _mutex_handle
    if os.name != "nt":
        return True
    kernel = ctypes.windll.kernel32
    _mutex_handle = kernel.CreateMutexW(None, False, "LongshotSaveBackup_SingleInstance")
    if kernel.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0, "O Longshot Save Backup já está aberto.\nLongshot Save Backup is already running.",
            APP_NAME, 0x40)
        return False
    return True


# ---------------------------------------------------------------- música (Windows MCI)
class Music:
    """Música em loop, volume fixo. Sem controle de parar: se parar, volta sozinha."""
    ALIAS = "lsbbgm"

    def __init__(self, path, volume):
        self.path = path
        self.volume = volume
        self.winmm = ctypes.windll.winmm if os.name == "nt" else None
        self.opened = False

    def _cmd(self, command):
        if not self.winmm:
            return 1, ""
        buf = ctypes.create_unicode_buffer(256)
        err = self.winmm.mciSendStringW(command, buf, 255, 0)
        return err, buf.value

    def start(self):
        """Retorna 'ok', 'missing' ou 'error'."""
        if not os.path.isfile(self.path):
            return "missing"
        if not self.winmm:
            return "error"
        self.close()
        err, _ = self._cmd(f'open "{self.path}" type mpegvideo alias {self.ALIAS}')
        if err:
            return "error"
        self.opened = True
        self._cmd(f"setaudio {self.ALIAS} volume to {self.volume * 10}")
        err, _ = self._cmd(f"play {self.ALIAS} repeat")
        if err:
            self._cmd(f"play {self.ALIAS}")
        return "ok"

    def keep_playing(self):
        """Chamado a cada segundo: garante tocando, em loop e no volume certo."""
        if not self.opened:
            return self.start()
        err, mode = self._cmd(f"status {self.ALIAS} mode")
        mode = mode.strip().lower()
        if err:
            return self.start()
        if mode == "paused":
            self._cmd(f"play {self.ALIAS}")
        elif mode != "playing":
            e, _ = self._cmd(f"play {self.ALIAS} from 0 repeat")
            if e:
                self._cmd(f"play {self.ALIAS} from 0")
        self._cmd(f"setaudio {self.ALIAS} volume to {self.volume * 10}")
        return "ok"

    def close(self):
        if self.opened:
            self._cmd(f"stop {self.ALIAS}")
            self._cmd(f"close {self.ALIAS}")
            self.opened = False


# ---------------------------------------------------------------- helpers
def list_builds(builds_dir):
    """Builds ordenadas da mais antiga para a mais nova (data de criação)."""
    try:
        items = [os.path.join(builds_dir, d) for d in os.listdir(builds_dir)]
    except Exception:
        return []
    items = [p for p in items if os.path.isdir(p)]
    items.sort(key=lambda p: os.path.getctime(p))
    return items


def has_user(build):
    return os.path.isdir(os.path.join(build, USER_DIR))


def signature(path):
    """(quantidade de arquivos, maior data de modificação, tamanho total)."""
    count, newest, size = 0, 0.0, 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                st = os.stat(os.path.join(root, name))
            except OSError:
                continue
            count += 1
            size += st.st_size
            newest = max(newest, st.st_mtime)
    return (count, newest, size)


def wait_quiet(path, seconds=5, timeout=120):
    """Espera a pasta parar de mudar (jogo/launcher terminou de escrever)."""
    end = time.time() + timeout
    last = signature(path)
    stable_since = time.time()
    while time.time() < end:
        time.sleep(1)
        cur = signature(path)
        if cur != last:
            last, stable_since = cur, time.time()
        elif time.time() - stable_since >= seconds:
            return True
    return False


def sync_copy(src, dst):
    """Copia só o que é novo/alterado (sem apagar nada no destino)."""
    copied = 0
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            s = os.path.join(root, name)
            d = os.path.join(target_dir, name)
            try:
                ss = os.stat(s)
                if os.path.exists(d):
                    ds = os.stat(d)
                    if ds.st_size == ss.st_size and ds.st_mtime >= ss.st_mtime - 1:
                        continue
                shutil.copy2(s, d)
                copied += 1
            except OSError:
                continue
    return copied


# ---------------------------------------------------------------- app
class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_cfg()
        self.lang = self.cfg["lang"]
        self.q = queue.Queue()
        self.ui_q = queue.Queue()      # funções para rodar na thread da interface
        self.stop_evt = threading.Event()
        self.thread = None
        self.running = False
        self.tab = "main"
        self.music = Music(resource_path("background.mp3"), MUSIC_VOLUME)
        self.music_warned = False

        root.geometry("900x660")
        root.minsize(780, 580)
        root.configure(bg=BG)
        try:
            root.iconbitmap(resource_path("icone.ico"))
        except Exception:
            pass

        self.v_builds = tk.StringVar(value=self.cfg["builds"])
        self.v_dest = tk.StringVar(value=self.cfg["dest"])
        self.v_status = tk.StringVar()

        self._build_ui()
        self.apply_lang()
        self.show_tab("main")

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(200, self.pump)
        root.after(300, self.music_tick)

        if self.cfg["dest"] and os.path.isdir(self.cfg["builds"]):
            self.start()
        else:
            self.log(self.t("log_choose_drive"))

    # ---- textos
    def t(self, key, **kw):
        s = TR[self.lang].get(key) or TR["en"][key]
        return s.format(**kw) if kw else s

    # ---- UI
    def _entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, bg=CARD2, fg=FG, insertbackground=GOLD,
                        bd=0, relief="flat", font=("Segoe UI", 10),
                        highlightthickness=1, highlightbackground=LINE, highlightcolor=GOLD)

    def _build_ui(self):
        # fundo animado
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bgfx = TriforceBackground(self.canvas)

        # cabeçalho
        self.logo = load_logo()
        self.canvas.create_image(24, 14, image=self.logo, anchor="nw")
        self.canvas.create_text(84, 38, text="Longshot Save Backup", fill=GOLD, anchor="w",
                                font=("Segoe UI", 20, "bold"))

        tabs = tk.Frame(self.root, bg=BG)
        tabs.place(x=24, y=74)
        self.tab_main_btn = FlatButton(tabs, "", lambda: self.show_tab("main"))
        self.tab_main_btn.pack(side="left", padx=(0, 6))
        self.tab_mods_btn = FlatButton(tabs, "", lambda: self.show_tab("mods"))
        self.tab_mods_btn.pack(side="left", padx=(0, 6))
        self.tab_help_btn = FlatButton(tabs, "", lambda: self.show_tab("help"))
        self.tab_help_btn.pack(side="left")
        self.lang_en = FlatButton(self.root, "EN", lambda: self.set_lang("en"))
        self.lang_en.place(relx=1.0, x=-24, y=74, anchor="ne")
        self.lang_pt = FlatButton(self.root, "PT-BR", lambda: self.set_lang("pt"))
        self.lang_pt.place(relx=1.0, x=-84, y=74, anchor="ne")

        # cartão de conteúdo
        self.card = tk.Frame(self.root, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.card.place(x=24, y=124, relwidth=1, width=-48, relheight=1, height=-148)

        # ---- aba principal
        self.frame_main = tk.Frame(self.card, bg=CARD)
        fm = self.frame_main
        fm.grid_columnconfigure(1, weight=1)
        fm.grid_rowconfigure(5, weight=1)

        self.lbl_builds = tk.Label(fm, bg=CARD, fg=FG, font=("Segoe UI", 10, "bold"))
        self.lbl_builds.grid(row=0, column=0, sticky="w", padx=(18, 8), pady=(18, 0))
        self._entry(fm, self.v_builds).grid(row=0, column=1, sticky="we", pady=(18, 0), ipady=6)
        self.btn_browse1 = FlatButton(fm, "", lambda: self.browse(self.v_builds))
        self.btn_browse1.grid(row=0, column=2, padx=(8, 18), pady=(18, 0))

        self.lbl_dest = tk.Label(fm, bg=CARD, fg=FG, font=("Segoe UI", 10, "bold"))
        self.lbl_dest.grid(row=1, column=0, sticky="w", padx=(18, 8), pady=(12, 0))
        self._entry(fm, self.v_dest).grid(row=1, column=1, sticky="we", pady=(12, 0), ipady=6)
        self.btn_browse2 = FlatButton(fm, "", lambda: self.browse(self.v_dest))
        self.btn_browse2.grid(row=1, column=2, padx=(8, 18), pady=(12, 0))

        self.lbl_desc = tk.Label(fm, bg=CARD, fg=MUTED, wraplength=700, justify="left",
                                 font=("Segoe UI", 9))
        self.lbl_desc.grid(row=2, column=0, columnspan=3, sticky="w", padx=18, pady=(14, 10))

        bar = tk.Frame(fm, bg=CARD)
        bar.grid(row=3, column=0, columnspan=3, sticky="we", padx=18)
        self.btn_toggle = FlatButton(bar, "", self.toggle, primary=True)
        self.btn_toggle.pack(side="left", padx=(0, 8))
        self.btn_copy = FlatButton(bar, "", self.copy_now_async)
        self.btn_copy.pack(side="left")
        tk.Label(bar, textvariable=self.v_status, bg=CARD, fg=GOLD,
                 font=("Segoe UI", 10, "bold")).pack(side="right")

        self.log_box = tk.Text(fm, bg="#0e1126", fg=FG, bd=0, relief="flat", state="disabled",
                               wrap="word", font=("Consolas", 10), padx=10, pady=8,
                               highlightthickness=1, highlightbackground=LINE)
        self.log_box.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=18, pady=(14, 18))

        # ---- aba mods
        self.frame_mods = ModsTab(self.card, self)

        # ---- aba ajuda
        self.frame_help = tk.Frame(self.card, bg=CARD)
        self.help_box = tk.Text(self.frame_help, bg="#0e1126", fg=FG, bd=0, relief="flat",
                                wrap="word", font=("Segoe UI", 10), padx=16, pady=14,
                                highlightthickness=1, highlightbackground=LINE)
        sb = tk.Scrollbar(self.frame_help, command=self.help_box.yview)
        self.help_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=18, padx=(0, 18))
        self.help_box.pack(side="left", fill="both", expand=True, padx=(18, 0), pady=18)

    def show_tab(self, name):
        self.tab = name
        frames = {"main": self.frame_main, "mods": self.frame_mods, "help": self.frame_help}
        for f in frames.values():
            f.pack_forget()
        frames[name].pack(fill="both", expand=True)
        if name == "mods":
            self.frame_mods.reload()
        self.tab_main_btn.set_active(name == "main")
        self.tab_mods_btn.set_active(name == "mods")
        self.tab_help_btn.set_active(name == "help")

    def apply_lang(self):
        self.root.title(f'{self.t("title")} {APP_VERSION}')
        self.tab_main_btn.configure(text=self.t("tab_main"))
        self.tab_help_btn.configure(text=self.t("tab_help"))
        self.tab_mods_btn.configure(text=self.t("tab_mods"))
        self.frame_mods.apply_lang()
        self.lang_pt.set_active(self.lang == "pt")
        self.lang_en.set_active(self.lang == "en")
        self.lbl_builds.configure(text=self.t("builds"))
        self.lbl_dest.configure(text=self.t("dest"))
        self.btn_browse1.configure(text=self.t("browse"))
        self.btn_browse2.configure(text=self.t("browse"))
        self.lbl_desc.configure(text=self.t("desc"))
        self.btn_toggle.configure(text=self.t("stop" if self.running else "start"))
        self.btn_copy.configure(text=self.t("copy_now"))
        self.v_status.set(self.t("st_wait" if self.running else "st_idle"))
        self.help_box.configure(state="normal")
        self.help_box.delete("1.0", "end")
        self.help_box.insert("1.0", self.t("help"))
        self.help_box.configure(state="disabled")

    def set_lang(self, lang):
        self.lang = lang
        self.cfg["lang"] = lang
        save_cfg(self.cfg)
        self.apply_lang()

    def browse(self, var):
        p = filedialog.askdirectory(initialdir=var.get() or "/")
        if p:
            var.set(os.path.normpath(p))
            self.save_from_ui()

    def log(self, msg):
        self.q.put(f"[{datetime.datetime.now():%H:%M:%S}] {msg}")

    def call_main(self, fn):
        """Agenda fn para rodar na thread da interface (pode ser chamado de qualquer thread)."""
        self.ui_q.put(fn)

    def pump(self):
        while True:
            try:
                fn = self.ui_q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as e:  # um erro numa tarefa não pode parar a interface
                self.q.put(f"[{datetime.datetime.now():%H:%M:%S}] {self.t('log_err', err=e)}")
        try:
            while True:
                line = self.q.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", line + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self.pump)

    def save_from_ui(self):
        self.cfg["builds"] = self.v_builds.get().strip()
        self.cfg["dest"] = self.v_dest.get().strip()
        save_cfg(self.cfg)

    def on_close(self):
        self.stop_evt.set()
        self.save_from_ui()
        self.music.close()
        self.root.destroy()

    # ---- música (sempre tocando, 40%)
    def music_tick(self):
        res = self.music.keep_playing()
        if res in ("missing", "error") and not self.music_warned:
            self.music_warned = True
            self.log(self.t("log_music_missing" if res == "missing" else "log_music_err"))
        self.root.after(1000, self.music_tick)

    # ---- controle
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        self.save_from_ui()
        if not os.path.isdir(self.cfg["builds"]):
            self.log(self.t("log_no_builds"))
            return
        if not self.cfg["dest"] or not os.path.isdir(self.cfg["dest"]):
            self.log(self.t("log_no_drive"))
            return
        if not self.cfg["known"]:  # primeira execução: builds atuais são "conhecidas"
            self.cfg["known"] = [os.path.basename(b) for b in list_builds(self.cfg["builds"])]
            save_cfg(self.cfg)
        self.stop_evt.clear()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.running = True
        self.apply_lang()
        self.log(self.t("log_started"))

    def stop(self):
        self.stop_evt.set()
        self.running = False
        self.apply_lang()
        self.log(self.t("log_stopped"))

    # ---- núcleo
    def dest_user(self):
        return os.path.join(self.cfg["dest"], BACKUP_ROOT, USER_DIR)

    def copy_and_backup(self, new_build):
        """Copia user e mods da build antiga para a nova E faz backup da user no Drive, ao mesmo tempo.
        Retorna True se a cópia da user para a build nova deu certo."""
        builds = list_builds(self.cfg["builds"])
        olds = [b for b in builds if b != new_build and has_user(b)
                and os.path.getctime(b) <= os.path.getctime(new_build)]
        if not olds:
            self.log(self.t("log_no_old", name=os.path.basename(new_build)))
            return True
        old = olds[-1]
        old_user = os.path.join(old, USER_DIR)
        new_user = os.path.join(new_build, USER_DIR)
        old_mods = os.path.join(old, MODS_DIR)
        new_mods = os.path.join(new_build, MODS_DIR)
        result = {"copy": False}

        self.log(self.t("log_new", new=os.path.basename(new_build), old=os.path.basename(old)))

        def do_copy():
            try:
                os.makedirs(new_user, exist_ok=True)
                shutil.copytree(old_user, new_user, dirs_exist_ok=True)
                result["copy"] = True
                self.log(self.t("log_copy_ok", name=os.path.basename(new_build)))
            except Exception as e:
                self.log(self.t("log_copy_err", err=e))

        def skip_size_table(dirpath, names):
            # a "~Size Table" é da build antiga: na nova ela é refeita a partir do romfs dela
            if os.path.normcase(os.path.abspath(dirpath)) == os.path.normcase(os.path.abspath(old_mods)):
                return [n for n in names if n.startswith("~")]
            return []

        def do_mods():
            if not os.path.isdir(old_mods):
                return  # build antiga não tem mods: nada a copiar
            try:
                os.makedirs(new_mods, exist_ok=True)
                shutil.copytree(old_mods, new_mods, dirs_exist_ok=True, ignore=skip_size_table)
                self.log(self.t("log_mods_ok", name=os.path.basename(new_build)))
            except Exception as e:
                self.log(self.t("log_mods_err", err=e))
                return
            state, detail = mm.refresh_size_table(new_build, new_mods)
            if state == "built":
                self.log(self.t("log_st_built", n=detail))
            elif state == "none":
                self.log(self.t("log_st_none"))
            elif state == "skip":
                self.log(self.t("log_st_skip", why=self.t("st_py314") if detail == "py314" else detail))
            else:
                self.log(self.t("log_st_err", err=detail))

        def do_backup():
            try:
                if not os.path.isdir(self.cfg["dest"]):
                    self.log(self.t("log_drive_off"))
                    return
                n = sync_copy(old_user, self.dest_user())
                self.log(self.t("log_bkp_ok", n=n, path=self.dest_user()))
            except Exception as e:
                self.log(self.t("log_bkp_err", err=e))

        threads = [threading.Thread(target=fn, daemon=True) for fn in (do_copy, do_mods, do_backup)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.call_main(self.frame_mods.reload)
        return result["copy"]

    def check_new_builds(self):
        known = set(self.cfg["known"])
        for b in list_builds(self.cfg["builds"]):
            name = os.path.basename(b)
            if name in known or not has_user(b):
                continue  # já conhecida, ou ainda não criou a user
            self.log(self.t("log_detected", name=name))
            wait_quiet(os.path.join(b, USER_DIR))
            if self.copy_and_backup(b):
                known.add(name)
                self.cfg["known"] = sorted(known)
                save_cfg(self.cfg)
            else:
                return  # falhou a cópia: tenta de novo no próximo ciclo

    def loop(self):
        while not self.stop_evt.is_set():
            try:
                self.check_new_builds()
            except Exception as e:
                self.log(self.t("log_err", err=e))
            self.stop_evt.wait(POLL_SECONDS)

    # ---- botão manual
    def copy_now_async(self):
        """Força copiar a user (e mods) da build anterior para a mais nova e fazer o backup."""
        self.save_from_ui()

        def job():
            try:
                builds = list_builds(self.cfg["builds"])
                if len(builds) < 2:
                    self.log(self.t("log_one_build"))
                    return
                if self.copy_and_backup(builds[-1]):
                    self.cfg["known"] = sorted({os.path.basename(b) for b in builds})
                    save_cfg(self.cfg)
            except Exception as e:
                self.log(self.t("log_err", err=e))

        threading.Thread(target=job, daemon=True).start()


if __name__ == "__main__":
    if ensure_single_instance():
        root = tk.Tk()
        App(root)
        root.mainloop()
