"""
Elementos visuais compartilhados pelo app e pelo instalador:
cores, botão flat moderno e o fundo animado com mini triforces.
"""
import base64
import math
import random
import tkinter as tk

APP_VERSION = "3.0.1"

BG = "#0c0e1d"
CARD = "#161a30"
CARD2 = "#20254a"
CARD2_H = "#2c3366"
LINE = "#2c3260"
GOLD = "#f5c030"
GOLD_H = "#ffd75a"
FG = "#eceefb"
MUTED = "#8f94b8"
DARK_TXT = "#1a1400"

ICON_PNG_B64 = (
    "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"
)


def load_logo():
    """Logo pequeno (PNG embutido). Precisa de uma janela Tk já criada."""
    return tk.PhotoImage(data=base64.b64decode("".join(ICON_PNG_B64.split())))


class FlatButton(tk.Label):
    """Botão plano e moderno, com efeito ao passar o mouse."""

    def __init__(self, parent, text="", command=None, primary=False):
        self._command = command
        self._base = GOLD if primary else CARD2
        self._hover = GOLD_H if primary else CARD2_H
        super().__init__(parent, text=text, bg=self._base,
                         fg=DARK_TXT if primary else FG,
                         font=("Segoe UI", 10, "bold"), padx=16, pady=8, cursor="hand2")
        self.bind("<Enter>", lambda e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda e: self.configure(bg=self._base))
        self.bind("<Button-1>", lambda e: self._command() if self._command else None)

    def set_active(self, active):
        """Usado em abas/idiomas: ativo = dourado."""
        self._base = GOLD if active else CARD2
        self._hover = GOLD_H if active else CARD2_H
        self.configure(bg=self._base, fg=DARK_TXT if active else FG)

    def set_command(self, command):
        self._command = command


class TriforceBackground:
    """Fundo animado: mini triforces douradas (discretas) subindo e balançando."""

    SHADES = ["#25230f", "#2e2a12", "#3a3315", "#483f17", "#574a18"]

    def __init__(self, canvas, count=28):
        self.c = canvas
        self.w, self.h = 820, 600
        self.items = []
        self._uid = 0
        canvas.bind("<Configure>", self._on_resize)
        for _ in range(count):
            self._spawn(anywhere=True)
        self._tick()

    def _on_resize(self, event):
        self.w, self.h = max(event.width, 200), max(event.height, 200)

    def _spawn(self, anywhere, item=None):
        size = random.randint(10, 30)
        x = random.uniform(0, self.w)
        y = random.uniform(0, self.h) if anywhere else self.h + size * 2
        shade = self.SHADES[min(len(self.SHADES) - 1, (size - 10) // 5)]
        self._uid += 1
        tag = f"tf{self._uid}"
        hh = size * 0.866
        x = float(x)
        polys = [
            [x, y - hh, x - size / 4, y - hh / 2, x + size / 4, y - hh / 2],
            [x - size / 4, y - hh / 2, x - size / 2, y, x, y],
            [x + size / 4, y - hh / 2, x, y, x + size / 2, y],
        ]
        for p in polys:
            self.c.create_polygon(p, fill=shade, outline="", tags=(tag, "tfbg"))
        info = {"tag": tag, "y": y, "size": size, "speed": random.uniform(0.25, 0.95),
                "sway": random.uniform(0.15, 0.7), "phase": random.uniform(0, 6.28)}
        self.items.append(info)
        self.c.tag_lower(tag)
        return info

    def _tick(self):
        try:
            for it in list(self.items):
                it["phase"] += 0.03
                dx = math.sin(it["phase"]) * it["sway"]
                dy = -it["speed"]
                self.c.move(it["tag"], dx, dy)
                it["y"] += dy
                if it["y"] < -it["size"] * 2:
                    self.c.delete(it["tag"])
                    self.items.remove(it)
                    self._spawn(anywhere=False)
            self.c.after(33, self._tick)
        except tk.TclError:
            pass  # janela fechada
