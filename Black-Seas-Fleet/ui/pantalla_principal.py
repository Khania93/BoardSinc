# ui/pantalla_principal.py
"""
Pantalla principal versión 1.7 (sin scroll vertical en la interfaz).
Correcciones:
- _calcular_total_para_estado acepta tanto BarcoEstado (dataclass) como dicts (guardando compatibilidad).
- El botón Astillero abre VentanaMejoras pasando el objeto BarcoEstado.
- Manejo robusto de lectura de referencia_id desde dicts/objetos.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from core.datos import DatosJuego
from core.modelo import BarcoEstado
from core.calculos import calcular_coste_barco
from core.guardar import guardar_partida, cargar_partida
from core.utils import (
    PUNTOS_COL,
    COL_FACCION,
    COL_TIPO,
    COL_NOMBRE,
    COL_TAMANO,
    TRIP_MOD,
    NAVAL_BG,
    is_renombre,
)

from ui.ventana_mejoras import VentanaMejoras
from ui.ventana_ficha import mostrar_ficha_barco

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
BG_IMAGE = ASSETS_DIR / "fondos" / "bg_generador.png"

_BEIGE = "#f5e6d3"
_DARK_BROWN = "#4b2e2a"
_MAX_BG_DIM = 3000


class GeneradorFlotaApp(tk.Tk):
    def __init__(self, player_name: str | None = None, loaded_fleet_path: str | None = None):
        super().__init__()
        self.title("Generador de Flota - Black Seas")
        self._default_w, self._default_h = 1400, 780
        self.geometry(f"{self._default_w}x{self._default_h}")
        self.minsize(1100, 650)
        self.configure(bg=NAVAL_BG)

        self._canvas = tk.Canvas(self, highlightthickness=0, bg=NAVAL_BG)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self.bind("<Configure>", self._on_resize)
        self._last_size = (self.winfo_width(), self.winfo_height())

        self.datos = DatosJuego()
        self.flota_actual: list[BarcoEstado] = []
        self.puntos_totales = 0
        self._next_id = 1
        self._left_visible = True

        self.nombre_jugador = player_name or (sys.argv[1] if len(sys.argv) > 1 else "Tripulante")

        self._create_persistent_ui()
        self.after(20, self._load_background_image)
        self.after(40, self._place_widgets)
        self._cargar_facciones_y_barcos()

        if loaded_fleet_path:
            try:
                self._cargar_partida_desde_archivo(loaded_fleet_path)
            except Exception:
                logger.exception("Error cargando partida al inicio")

    def _create_persistent_ui(self):
        style = ttk.Style()
        try:
            style.configure("Custom.Treeview",
                            background=NAVAL_BG,
                            fieldbackground=NAVAL_BG,
                            foreground=_DARK_BROWN)
            style.configure("Custom.Treeview.Heading",
                            background=NAVAL_BG,
                            foreground=_DARK_BROWN,
                            font=("Garamond", 10, "bold"))
            style.configure("Custom.TCombobox", fieldbackground=NAVAL_BG, background=NAVAL_BG, foreground=_DARK_BROWN)
            style.map("Custom.Treeview",
                      background=[("selected", NAVAL_BG)],
                      foreground=[("selected", _DARK_BROWN)])
        except Exception:
            pass

        self._player_text = self._canvas.create_text(
            20, 18, text=f"Jugador: {self.nombre_jugador}", anchor="w",
            font=("Garamond", 13, "bold"), fill=_DARK_BROWN, tags="top_row"
        )
        self._restantes_text = self._canvas.create_text(
            0, 18, text=f"Puntos restantes: 3000", anchor="e",
            font=("Garamond", 13, "bold"), fill=_DARK_BROWN, tags="top_row"
        )

        self._label_faccion = self._canvas.create_text(20, 56, text="Facción:", anchor="nw",
                                                       font=("Garamond", 11), fill=_DARK_BROWN, tags="controls_row")

        self.combo_faccion = ttk.Combobox(self._canvas, values=[], state="readonly", width=28, style="Custom.TCombobox")
        self.combo_faccion.bind("<<ComboboxSelected>>", self.on_faccion_cambiada)
        self._combo_item = self._canvas.create_window(90, 56, window=self.combo_faccion, anchor="nw", tags="controls_row")

        self.entry_puntos_objetivo = tk.Entry(self._canvas, width=8, bg=_BEIGE, fg=_DARK_BROWN, relief=tk.FLAT, justify="center")
        self.entry_puntos_objetivo.insert(0, "3000")
        self._puntos_item = self._canvas.create_window(420, 56, window=self.entry_puntos_objetivo, anchor="nw", tags="controls_row")

        self.btn_minus = tk.Button(self._canvas, text="-10", bg=_BEIGE, fg=_DARK_BROWN, command=lambda: self._ajustar_puntos(-10), relief=tk.FLAT)
        self.btn_plus = tk.Button(self._canvas, text="+10", bg=_BEIGE, fg=_DARK_BROWN, command=lambda: self._ajustar_puntos(10), relief=tk.FLAT)
        self._btn_minus_item = self._canvas.create_window(500, 56, window=self.btn_minus, anchor="nw", tags="controls_row")
        self._btn_plus_item = self._canvas.create_window(560, 56, window=self.btn_plus, anchor="nw", tags="controls_row")

        self.btn_clear = tk.Button(self._canvas, text="Limpiar", bg=_BEIGE, fg=_DARK_BROWN, command=self._reset_puntos_objetivo, relief=tk.FLAT)
        self._btn_clear_item = self._canvas.create_window(620, 56, window=self.btn_clear, anchor="nw", tags="controls_row")

        self.btn_toggle_left = tk.Button(self._canvas, text="Ocultar panel Barcos", bg=_BEIGE, fg=_DARK_BROWN, command=self._toggle_left_panel, relief=tk.FLAT)
        self._btn_toggle_item = self._canvas.create_window(740, 56, window=self.btn_toggle_left, anchor="nw", tags="controls_row")

        # Left: barcos disponibles (sin scroll vertical)
        self.frame_barcos = tk.Frame(self._canvas, bg=NAVAL_BG)
        cols_barcos = [COL_FACCION, COL_TIPO, COL_NOMBRE, PUNTOS_COL, COL_TAMANO]
        self.tree_barcos = ttk.Treeview(self.frame_barcos, columns=cols_barcos, show="headings", selectmode="browse", style="Custom.Treeview")
        for col in cols_barcos:
            self.tree_barcos.heading(col, text=col, anchor="center")
            ancho = 120
            if col == COL_NOMBRE:
                ancho = 220
            elif col == PUNTOS_COL:
                ancho = 90
            self.tree_barcos.column(col, width=ancho, anchor="center", stretch=False)
        # No vertical scrollbar for tree_barcos
        self.tree_barcos.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tree_barcos.tag_configure("disabled", foreground="gray", background=NAVAL_BG)
        self.tree_barcos.bind("<<TreeviewSelect>>", self._on_tree_barcos_select)
        self._frame_barcos_item = self._canvas.create_window(20, 110, window=self.frame_barcos, anchor="nw", tags="center_windows", width=420, height=460)

        # Right: flota actual (sin scroll vertical, horizontal kept)
        self.frame_flota = tk.Frame(self._canvas, bg=NAVAL_BG)
        arm_cols = []
        zones = ["BABOR", "ESTRIBOR", "PROA", "POPA"]
        types = ["CAÑON_PESADO", "CAÑON_LIGERO", "CARRONADAS", "MORTEROS"]
        for z in zones:
            for t in types:
                arm_cols.append(f"{z} - {t.replace('_', ' ')}")

        cols_flota = [
            COL_FACCION, COL_TIPO, COL_NOMBRE, COL_TAMANO,
            "VIDA (actual/total)", "RUPTURA", "TASA DE NUDOS", "ANGULO", "TRIPULACIÓN", "HAB. ESPECIAL"
        ] + arm_cols

        self.tree_flota = ttk.Treeview(self.frame_flota, columns=cols_flota, show="headings", style="Custom.Treeview")
        try:
            ttk.Style().configure("Custom.Treeview.Heading", font=("Garamond", 10, "bold"), foreground=_DARK_BROWN, background=NAVAL_BG)
        except Exception:
            pass

        for col in cols_flota:
            self.tree_flota.heading(col, text=col, anchor="center")
            if col in (COL_NOMBRE,):
                width = 220
            elif col in ("VIDA (actual/total)", "TRIPULACIÓN", "HAB. ESPECIAL"):
                width = 120
            elif col in ("RUPTURA", "TASA DE NUDOS", "ANGULO"):
                width = 100
            elif any(col.startswith(z) for z in zones):
                width = 90
            else:
                width = 100
            self.tree_flota.column(col, width=width, anchor="center", stretch=False)

        # No vertical scrollbar; keep horizontal scrollbar (beige)
        hscrollbar_flota = tk.Scrollbar(self.frame_flota, orient=tk.HORIZONTAL, command=self.tree_flota.xview, bg=_BEIGE, troughcolor=_BEIGE, activebackground=_BEIGE)
        self.tree_flota.configure(xscrollcommand=hscrollbar_flota.set)

        self.tree_flota.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        hscrollbar_flota.pack(side=tk.BOTTOM, fill=tk.X)

        # BIND doble clic -> método que existe ahora
        self.tree_flota.bind("<Double-1>", self._doble_click_barco)
        self._frame_flota_item = self._canvas.create_window(460, 110, window=self.frame_flota, anchor="nw", tags="center_windows", width=880, height=460)

        # Buttons
        self.btn_add_barco = tk.Button(self._canvas, text="Añadir", bg=_BEIGE, fg=_DARK_BROWN, command=self.anadir_barco_a_flota, relief=tk.FLAT)
        self.btn_quitar = tk.Button(self._canvas, text="Quitar", bg=_BEIGE, fg=_DARK_BROWN, command=self.quitar_barco_de_flota, relief=tk.FLAT)
        self.btn_astillero = tk.Button(self._canvas, text="Astillero", bg=_BEIGE, fg=_DARK_BROWN, command=self.configurar_barco, relief=tk.FLAT)
        self.btn_ver = tk.Button(self._canvas, text="Ver ficha", bg=_BEIGE, fg=_DARK_BROWN, command=self.ver_ficha_seleccionada, relief=tk.FLAT)
        self.btn_guardar = tk.Button(self._canvas, text="Guardar", bg=_BEIGE, fg=_DARK_BROWN, command=self._guardar_flota, relief=tk.FLAT)

        self._btn_add_item = self._canvas.create_window(20, 590, window=self.btn_add_barco, anchor="nw", tags="bottom_row")
        self._btn_quitar_item = self._canvas.create_window(120, 590, window=self.btn_quitar, anchor="nw", tags="bottom_row")
        self._btn_astillero_item = self._canvas.create_window(220, 590, window=self.btn_astillero, anchor="nw", tags="bottom_row")
        self._btn_ver_item = self._canvas.create_window(340, 590, window=self.btn_ver, anchor="nw", tags="bottom_row")
        self._btn_guardar_item = self._canvas.create_window(460, 590, window=self.btn_guardar, anchor="nw", tags="bottom_row")

    # -------------------------
    # Background / resize
    # -------------------------
    def _load_background_image(self):
        if not BG_IMAGE.exists():
            return
        try:
            if PIL_AVAILABLE:
                img = Image.open(BG_IMAGE).convert("RGBA")
                self._bg_orig = img
                w = max(1, self.winfo_width() or self._default_w)
                h = max(1, self.winfo_height() or self._default_h)
                scale = max(w / img.width, h / img.height)
                target = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                resized = img.resize(target, Image.LANCZOS)
                self._bg_photo = ImageTk.PhotoImage(resized, master=self._canvas)
            else:
                self._bg_photo = tk.PhotoImage(master=self._canvas, file=str(BG_IMAGE))
            if self._bg_photo:
                cw = self._canvas.winfo_width() or self._default_w
                ch = self._canvas.winfo_height() or self._default_h
                iw = self._bg_photo.width()
                ih = self._bg_photo.height()
                x = (cw - iw) // 2
                y = (ch - ih) // 2
                if getattr(self, "_bg_item_id", None) and self._canvas.type(self._bg_item_id) == "image":
                    self._canvas.itemconfig(self._bg_item_id, image=self._bg_photo)
                    self._canvas.coords(self._bg_item_id, x, y)
                else:
                    self._bg_item_id = self._canvas.create_image(x, y, anchor="nw", image=self._bg_photo, tags="bg_image")
                    self._canvas.tag_lower(self._bg_item_id)
        except Exception:
            logger.exception("Error cargando imagen de fondo")

    def _resize_background(self):
        if not PIL_AVAILABLE or getattr(self, "_bg_orig", None) is None:
            return
        try:
            w = max(1, self.winfo_width())
            h = max(1, self.winfo_height())
            img = self._bg_orig
            scale = max(w / img.width, h / img.height)
            new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            resized = img.resize(new_size, Image.LANCZOS)
            self._bg_photo = ImageTk.PhotoImage(resized, master=self._canvas)
            if getattr(self, "_bg_item_id", None) and self._canvas.type(self._bg_item_id) == "image":
                self._canvas.itemconfig(self._bg_item_id, image=self._bg_photo)
                cw = self._canvas.winfo_width() or self._default_w
                ch = self._canvas.winfo_height() or self._default_h
                iw = self._bg_photo.width()
                ih = self._bg_photo.height()
                x = (cw - iw) // 2
                y = (ch - ih) // 2
                self._canvas.coords(self._bg_item_id, x, y)
            else:
                cw = self._canvas.winfo_width() or self._default_w
                ch = self._canvas.winfo_height() or self._default_h
                iw = self._bg_photo.width()
                ih = self._bg_photo.height()
                x = (cw - iw) // 2
                y = (ch - ih) // 2
                self._bg_item_id = self._canvas.create_image(x, y, anchor="nw", image=self._bg_photo, tags="bg_image")
                self._canvas.tag_lower(self._bg_item_id)
        except Exception:
            logger.exception("Error redimensionando imagen de fondo")

    def _place_widgets(self):
        cw = self.winfo_width() or self._default_w
        ch = self.winfo_height() or self._default_h
        top_y = 18
        left_margin = 20
        right_margin = 20
        self._canvas.coords(self._player_text, left_margin, top_y)
        label_x = cw - right_margin - 20
        self._canvas.coords(self._restantes_text, label_x, top_y)
        label_faccion_x = left_margin
        self._canvas.coords(self._label_faccion, label_faccion_x, top_y + 38)
        self._canvas.coords(self._combo_item, label_faccion_x + 70, top_y + 38)
        entry_x = label_faccion_x + 320
        self._canvas.coords(self._puntos_item, entry_x, top_y + 38)
        self._canvas.coords(self._btn_minus_item, entry_x + 80, top_y + 38)
        self._canvas.coords(self._btn_plus_item, entry_x + 140, top_y + 38)
        self._canvas.coords(self._btn_clear_item, entry_x + 200, top_y + 38)
        self._canvas.coords(self._btn_toggle_item, entry_x + 280, top_y + 38)

        padding = 20
        center_top = 110
        center_height = max(200, ch - 260)
        if self._left_visible:
            left_w = int(cw * 0.30)
            right_w = cw - left_w - (padding * 4)
            left_x = padding
            right_x = left_x + left_w + (padding * 2)
            try:
                self._canvas.itemconfigure(self._frame_barcos_item, state="normal")
            except Exception:
                pass
            self._canvas.coords(self._frame_barcos_item, left_x, center_top)
            self._canvas.itemconfigure(self._frame_barcos_item, width=left_w, height=center_height)
            self.frame_barcos.configure(width=left_w, height=center_height)
            self._canvas.coords(self._frame_flota_item, right_x, center_top)
            self._canvas.itemconfigure(self._frame_flota_item, width=right_w, height=center_height)
            self.frame_flota.configure(width=right_w, height=center_height)
        else:
            try:
                self._canvas.itemconfigure(self._frame_barcos_item, state="hidden")
            except Exception:
                pass
            right_x = padding
            right_w = cw - (padding * 2)
            self._canvas.coords(self._frame_flota_item, right_x, center_top)
            self._canvas.itemconfigure(self._frame_flota_item, width=right_w, height=center_height)
            self.frame_flota.configure(width=right_w, height=center_height)

        btn_widgets = [self.btn_add_barco, self.btn_quitar, self.btn_astillero, self.btn_ver, self.btn_guardar]
        btn_items = [self._btn_add_item, self._btn_quitar_item, self._btn_astillero_item, self._btn_ver_item, self._btn_guardar_item]
        btn_widths = []
        for w in btn_widgets:
            try:
                w.update_idletasks()
                btn_widths.append(w.winfo_reqwidth())
            except Exception:
                btn_widths.append(100)
        spacing = 20
        total_btns_width = sum(btn_widths) + spacing * (len(btn_widths) - 1)
        center_x = cw // 2
        start_x = center_x - total_btns_width // 2
        btns_y = center_top + center_height + 12
        cur_x = start_x
        for idx, btn_item in enumerate(btn_items):
            self._canvas.coords(btn_item, cur_x, btns_y)
            cur_x += btn_widths[idx] + spacing
        try:
            if getattr(self, "_bg_item_id", None):
                self._canvas.tag_lower(self._bg_item_id)
        except Exception:
            pass

    def _toggle_left_panel(self):
        self._left_visible = not self._left_visible
        if self._left_visible:
            self.btn_toggle_left.config(text="Ocultar panel Barcos")
        else:
            self.btn_toggle_left.config(text="Mostrar panel Barcos")
        self._place_widgets()
        self.update_idletasks()

    def _reset_puntos_objetivo(self):
        self.entry_puntos_objetivo.delete(0, tk.END)
        self.entry_puntos_objetivo.insert(0, "3000")
        self._actualizar_puntos_restantes()

    def _cargar_facciones_y_barcos(self):
        try:
            facs = self.datos.list_barcos()
            facs_set = set()
            for r in facs:
                for k, v in r.items():
                    lk = str(k).lower()
                    if ("facc" in lk or "facción" in lk) and v is not None and str(v).strip():
                        facs_set.add(str(v).strip())
            facs_list = sorted(facs_set)
        except Exception:
            facs_list = []
        self.combo_faccion["values"] = facs_list
        self.combo_faccion.set("")

    def on_faccion_cambiada(self, event=None):
        self.actualizar_lista_barcos()

    def actualizar_lista_barcos(self):
        fac = self.combo_faccion.get()
        self.tree_barcos.delete(*self.tree_barcos.get_children())
        if not fac:
            return
        try:
            barcos = self.datos.list_barcos()
            for r in barcos:
                fac_val = None
                nom_val = None
                tipo_val = None
                puntos_val = None
                tam_val = None
                for k, v in r.items():
                    lk = str(k).lower()
                    if ("facc" in lk or "facción" in lk) and fac_val is None:
                        fac_val = v
                    if "nom" in lk and nom_val is None:
                        nom_val = v
                    if "tipo" in lk and tipo_val is None:
                        tipo_val = v
                    if "punt" in lk or "cost" in lk:
                        if puntos_val is None:
                            puntos_val = v
                    if "tam" in lk or "tama" in lk:
                        if tam_val is None:
                            tam_val = v
                if fac_val is None:
                    continue
                if str(fac_val).strip() != str(fac).strip():
                    continue
                valores = [fac_val or "", tipo_val or "", nom_val or "", puntos_val or 0, tam_val or ""]
                self.tree_barcos.insert("", tk.END, values=valores)
        except Exception:
            logger.exception("Error actualizando lista de barcos")

    def _on_tree_barcos_select(self, event):
        pass

    def _ajustar_puntos(self, cantidad):
        try:
            actual = int(self.entry_puntos_objetivo.get())
        except Exception:
            actual = 0
        nuevo = max(0, actual + cantidad)
        nuevo = int(round(nuevo / 10.0) * 10)
        self.entry_puntos_objetivo.delete(0, tk.END)
        self.entry_puntos_objetivo.insert(0, str(nuevo))
        self._actualizar_puntos_restantes()

    def _actualizar_puntos_restantes(self):
        try:
            objetivo = int(self.entry_puntos_objetivo.get())
        except Exception:
            objetivo = 0
        usados = sum(self._calcular_total_para_estado(b) for b in self.flota_actual)
        restantes = max(0, objetivo - usados)
        self._canvas.itemconfigure(self._restantes_text, text=f"Puntos restantes: {restantes}")

    def anadir_barco_a_flota(self):
        sel = self.tree_barcos.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un barco.")
            return
        valores = self.tree_barcos.item(sel[0], "values")
        if not valores:
            messagebox.showerror("Error", "Registro inválido.")
            return
        nombre = valores[2]
        tipo = valores[1]
        identificador = nombre or tipo
        base = self.datos.build_barco_base(identificador)
        if not base:
            messagebox.showerror("Error", "No se encontró el barco en el reglamento (Excel).")
            return

        vida_base = 0
        for k, v in base.items():
            if "vida" in str(k).lower():
                try:
                    vida_base = int(float(v or 0))
                except Exception:
                    vida_base = 0
                break
        trip = None
        for k, v in base.items():
            if "tripul" in str(k).lower():
                trip = v
                break

        estado = BarcoEstado(
            referencia_id=identificador,
            id_interno=self._next_id,
            id_custom="",
            estado="ACTIVO",
            vida_actual=vida_base,
            tripulacion_actual=trip,
            mejoras_instaladas=[],
            oficial_ref=None,
            danos_activos=[],
            disparos={},
            observaciones="",
        )
        self._next_id += 1
        self.flota_actual.append(estado)
        self._insertar_en_tree_flota(estado)
        self.puntos_totales = sum(self._calcular_total_para_estado(b) for b in self.flota_actual)
        self._actualizar_puntos_restantes()

    def _get_ref_from_estado(self, estado):
        """
        Helper: acepta BarcoEstado o dict-like and returns referencia_id string.
        """
        try:
            if isinstance(estado, dict):
                return estado.get("referencia_id") or estado.get("referencia") or estado.get("REF") or estado.get("NOMBRE") or estado.get("Nombre")
            return getattr(estado, "referencia_id", None)
        except Exception:
            return None

    def _calcular_total_para_estado(self, estado) -> int:
        """
        Calcula el coste total del barco. Acepta BarcoEstado o dict (compatibilidad).
        """
        try:
            # Determine referencia id robustly
            ref = self._get_ref_from_estado(estado)
            base = self.datos.build_barco_base(ref)
            if not base:
                return 0

            # Extraer puntos base
            base_points = 0
            for k, v in base.items():
                lk = str(k).lower()
                if "punt" in lk or "cost" in lk:
                    try:
                        base_points = int(float(v or 0))
                    except Exception:
                        base_points = 0
                    break

            # Tripulación: preferir estado, fallback a base
            trip_val = None
            try:
                if isinstance(estado, dict):
                    trip_val = estado.get("tripulacion_actual") or estado.get("tripulacion") or estado.get("TRIPULACIÓN")
                else:
                    trip_val = getattr(estado, "tripulacion_actual", None)
            except Exception:
                trip_val = None
            trip_val = trip_val or base.get("TRIPULACIÓN") or base.get("Tripulación") or "REGULAR"
            trip_mod = TRIP_MOD.get(str(trip_val).upper(), 1.0)

            # Normalizar mejoras: obtener definiciones desde datos.get_mejora_by_name
            mejoras_names = []
            if isinstance(estado, dict):
                mejoras_names = estado.get("mejoras_instaladas") or []
            else:
                mejoras_names = getattr(estado, "mejoras_instaladas", []) or []

            mejoras_defs = []
            for mname in (mejoras_names or []):
                try:
                    mdef = self.datos.get_mejora_by_name(mname)
                except Exception:
                    mdef = None
                if mdef:
                    coste_val = None
                    if isinstance(mdef, dict):
                        for mk, mv in mdef.items():
                            if "punt" in str(mk).lower() or "cost" in str(mk).lower():
                                try:
                                    coste_val = int(float(mv or 0))
                                except Exception:
                                    coste_val = 0
                                break
                    norm = {"NOMBRE": mname, "COSTE": coste_val if coste_val is not None else 0}
                    if isinstance(mdef, dict):
                        norm.update(mdef)
                    mejoras_defs.append(norm)
                else:
                    mejoras_defs.append({"NOMBRE": mname, "COSTE": 0})

            # Oficial: intentar obtener definición normalizada
            oficial_ref = None
            if isinstance(estado, dict):
                oficial_ref = estado.get("oficial_ref") or estado.get("oficial")
            else:
                oficial_ref = getattr(estado, "oficial_ref", None)

            oficial_def = None
            if oficial_ref:
                try:
                    od = self.datos.get_oficial_by_name_or_id(oficial_ref)
                except Exception:
                    od = None
                if od and isinstance(od, dict):
                    puntos_of = 0
                    for ok, ov in od.items():
                        if "punt" in str(ok).lower() or "cost" in str(ok).lower():
                            try:
                                puntos_of = int(float(ov or 0))
                            except Exception:
                                puntos_of = 0
                            break
                    oficial_def = dict(od)
                    oficial_def.setdefault("Puntos", puntos_of)
                else:
                    oficial_def = od

            # Intentar usar la función central de cálculo (preferible)
            try:
                total = calcular_coste_barco(base_points, trip_mod, mejoras_defs, oficial_def, capturado=( (estado.get("estado") if isinstance(estado, dict) else getattr(estado, "estado", "")) == "CAPTURADO"))
                if isinstance(total, (int, float)) and int(total) >= 0:
                    return int(total)
            except Exception:
                logger.exception("calcular_coste_barco falló, aplicando fallback")

            # Fallback manual
            try:
                suma_mejoras = 0
                for m in mejoras_defs:
                    if isinstance(m, dict):
                        coste = 0
                        for k, v in m.items():
                            if "punt" in str(k).lower() or "cost" in str(k).lower():
                                try:
                                    coste = int(float(v or 0))
                                except Exception:
                                    coste = 0
                                break
                        suma_mejoras += coste
                puntos_oficial = 0
                if isinstance(oficial_def, dict):
                    for k, v in oficial_def.items():
                        if "punt" in str(k).lower() or "cost" in str(k).lower():
                            try:
                                puntos_oficial = int(float(v or 0))
                            except Exception:
                                puntos_oficial = 0
                            break
                subtotal = base_points + suma_mejoras + puntos_oficial
                total_calc = subtotal * float(trip_mod)
                return int(round(total_calc))
            except Exception:
                logger.exception("Fallback cálculo puntos falló")
                return int(base_points)
        except Exception:
            logger.exception("Error calculando coste para estado %s", getattr(estado, "id_interno", "<unknown>"))
            return 0

    def _insertar_en_tree_flota(self, estado: BarcoEstado):
        base = self.datos.build_barco_base(estado.referencia_id) or {}
        fac = base.get("Facción") or base.get("FACCION") or ""
        tipo = base.get("TIPO") or base.get("Tipo") or ""
        nombre = base.get("NOMBRE") or base.get("Nombre") or estado.referencia_id
        tam = base.get("TAMAÑO") or base.get("TAMANO") or base.get("Tamaño") or ""
        vida_total = 0
        for k, v in (base or {}).items():
            if "vida" in str(k).lower():
                try:
                    vida_total = int(float(v or 0))
                except Exception:
                    vida_total = 0
                break
        vida_actual = getattr(estado, "vida_actual", vida_total)
        puntos = self._calcular_total_para_estado(estado)
        valores = [fac, tipo, nombre, tam, f"{vida_actual}/{vida_total}", base.get("RUPTURA") or "", base.get("TASA DE NUDOS") or "", base.get("ANGULO") or "", getattr(estado, "tripulacion_actual", "") or "", base.get("HABILIDAD") or ""]
        # append armamento placeholders
        zones = ["BABOR", "ESTRIBOR", "PROA", "POPA"]
        types = ["CAÑON_PESADO", "CAÑON_LIGERO", "CARRONADAS", "MORTEROS"]
        for z in zones:
            for t in types:
                valores.append("")  # simplified for display
        self.tree_flota.insert("", tk.END, values=valores, tags=())
        # update puntos totales display
        self.puntos_totales = sum(self._calcular_total_para_estado(b) for b in self.flota_actual)
        self._actualizar_puntos_restantes()

    # Placeholder methods for missing features (to avoid crashes)
    def quitar_barco_de_flota(self):
        sel = self.tree_flota.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un barco de la flota.")
            return
        # remove first selected and corresponding estado
        try:
            idx = self.tree_flota.index(sel[0])
            self.tree_flota.delete(sel[0])
            if 0 <= idx < len(self.flota_actual):
                del self.flota_actual[idx]
            self._actualizar_puntos_restantes()
        except Exception:
            logger.exception("Error quitando barco de la flota")

    def configurar_barco(self):
        # Open astillero for selected barco in flota
        sel = self.tree_flota.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un barco de la flota para configurar.")
            return
        idx = self.tree_flota.index(sel[0])
        if idx < 0 or idx >= len(self.flota_actual):
            messagebox.showerror("Error", "Índice de barco inválido.")
            return
        estado = self.flota_actual[idx]
        try:
            VentanaMejoras(self, self.datos, estado, lambda b: self._on_barco_actualizado(b))
        except Exception:
            logger.exception("Error abriendo Astillero")

    def _on_barco_actualizado(self, barco_estado):
        # Called by VentanaMejoras after in-place update
        try:
            # refresh tree and points
            # naive approach: clear and reinsert all
            for iid in self.tree_flota.get_children():
                self.tree_flota.delete(iid)
            for b in self.flota_actual:
                self._insertar_en_tree_flota(b)
            self._actualizar_puntos_restantes()
        except Exception:
            logger.exception("Error actualizando vista tras cambios en barco")

    def ver_ficha_seleccionada(self):
        sel = self.tree_flota.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un barco de la flota para ver su ficha.")
            return
        idx = self.tree_flota.index(sel[0])
        if idx < 0 or idx >= len(self.flota_actual):
            messagebox.showerror("Error", "Índice de barco inválido.")
            return
        estado = self.flota_actual[idx]
        try:
            mostrar_ficha_barco(self, estado, self.datos)
        except Exception:
            logger.exception("Error mostrando ficha de barco")

    def _doble_click_barco(self, event):
        # On double click open ficha
        self.ver_ficha_seleccionada()

    # Minimal stubs for save/load to avoid NameError if called
    def _guardar_flota(self):
        try:
            guardar_partida([b.to_save_dict() for b in self.flota_actual])
            messagebox.showinfo("Guardado", "Partida guardada correctamente.")
        except Exception:
            logger.exception("Error guardando partida")
            messagebox.showerror("Error", "No se pudo guardar la partida.")

    # Resize handler
    def _on_resize(self, event):
        # debounce heavy operations
        try:
            self._resize_background()
            self._place_widgets()
        except Exception:
            pass
