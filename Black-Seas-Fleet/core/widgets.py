# ui/widgets.py
"""
Widgets reutilizables y estilos para la UI.
"""
import tkinter as tk
from tkinter import ttk
from core.utils import NAVAL_BG, NAVAL_PANEL, NAVAL_TEXT, FONT_NORMAL, FONT_TITLE

def aplicar_estilos(root):
    """
    Configura estilos ttk y valores por defecto para que las ventanas usen
    NAVAL_BG como fondo visual en lugar del color azul por defecto.
    """
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("Naval.TFrame", background=NAVAL_BG)
    style.configure("Naval.TLabel", background=NAVAL_BG, foreground=NAVAL_TEXT, font=FONT_NORMAL)
    style.configure("Title.TLabel", background=NAVAL_BG, foreground="#c9a66b", font=FONT_TITLE)

    style.configure("Naval.TEntry", fieldbackground=NAVAL_BG, background=NAVAL_BG, foreground=NAVAL_TEXT)
    style.configure("Naval.TCombobox", fieldbackground=NAVAL_BG, background=NAVAL_BG, foreground=NAVAL_TEXT)

    style.configure("Naval.Treeview", background=NAVAL_BG, fieldbackground=NAVAL_BG, foreground=NAVAL_TEXT)
    style.configure("Naval.Treeview.Heading", background=NAVAL_BG, foreground=NAVAL_TEXT, font=("Garamond", 10, "bold"))

    style.configure("Naval.TButton", background=NAVAL_PANEL, foreground=NAVAL_TEXT)

class LabeledEntry(ttk.Frame):
    """Entrada con etiqueta a la izquierda, adaptada para usar estilos NAVAL."""
    def __init__(self, parent, label: str, var: tk.StringVar = None, width: int = 20):
        super().__init__(parent, style="Naval.TFrame")
        self.var = var or tk.StringVar()
        lbl = ttk.Label(self, text=label, style="Naval.TLabel")
        lbl.pack(side="left")
        self.entry = ttk.Entry(self, textvariable=self.var, width=width, style="Naval.TEntry")
        self.entry.pack(side="left", padx=(6, 0))

    def get(self):
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)
