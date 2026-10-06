# ui/ventana_mejoras.py
"""
Ventana "Astillero" — lógica corregida y completa.

Este módulo implementa la ventana modal de configuración de un único barco
(respetando estética, distribución y callbacks existentes). Solo modifica
la lógica interna para cumplir las reglas oficiales del proyecto:
- Barcos de renombre (TIPO != NOMBRE o RENOMBRE == True) sin mejoras, tripulación
  forzada a VETERANA y tripulación oculta.
- Barcos genéricos (TIPO == NOMBRE) pueden llevar mejoras según su tamaño.
- Ranuras de mejoras creadas exactamente según el tamaño (XL/L/M/S/T).
- Mejores cargadas exclusivamente desde la hoja MEJORAS del Excel (o API datos).
- Incompatibilidad entre Sobreartillado y Carronadas Extra.
- Multiplicadores de tripulación y redondeo a la decena superior.
- Desplegable de oficiales filtrado por facción y excluyendo oficiales ya usados
  en la flota (excepto el oficial actual del barco).
- Recalculo automático y guardado in-place del mismo objeto barco.
- No se modifica la apariencia ni la API externa (callback_actualizar(barco)).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional, Tuple
import math

import tkinter as tk
from tkinter import ttk, messagebox

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Optional libs (no obligatorias para la lógica)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    pd = None  # type: ignore
    PANDAS_AVAILABLE = False

# ---------------------------
# Visual constants (no tocar)
# ---------------------------
NAVAL_BG = "#F0E9DC"
_NAVAL_TEXT = "#4b2e2a"
_BEIGE = "#F5E6C8"
_SELECT_BG = "#D9C19A"
FONT_TITLE = ("Garamond", 18, "bold")
FONT_NORMAL = ("Garamond", 10)

# Layout constants (fijos)
LEFT_COLUMN_WIDTH = 420
RIGHT_COLUMN_WIDTH = 380
COLUMN_GAP = 80
CONTENT_WIDTH = LEFT_COLUMN_WIDTH + COLUMN_GAP + RIGHT_COLUMN_WIDTH

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_CANDIDATES = [
    PROJECT_ROOT / "Black_Seas.xlsx",
    PROJECT_ROOT / "data" / "Black_Seas.xlsx",
    PROJECT_ROOT / "assets" / "Black_Seas.xlsx",
]
BG_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fondos" / "bg_astillero.png",
    PROJECT_ROOT / "assets" / "fondos" / "bg_astillero.jpg",
    PROJECT_ROOT / "assets" / "fondos" / "bg_astillero.jpeg",
]

_MAX_BG_DIM = 3000


def _ensure_int(v, default=0):
    try:
        return int(float(v or 0))
    except Exception:
        return default


def _round_up_to_10(n: float) -> int:
    try:
        return int(math.ceil(float(n) / 10.0) * 10)
    except Exception:
        return int(n)


# ---------------------------
# Helpers para leer/escribir barco (respetando su tipo)
# ---------------------------
def _get_field(barco_obj, key_candidates: List[str], default=None):
    """
    Leer un campo del objeto barco probando varias claves.
    Funciona si barco_obj es dict, tiene .get o es un objeto con atributos.
    """
    if barco_obj is None:
        return default
    try:
        if isinstance(barco_obj, dict):
            for k in key_candidates:
                if k in barco_obj and barco_obj[k] is not None:
                    return barco_obj[k]
    except Exception:
        pass
    try:
        if hasattr(barco_obj, "get"):
            for k in key_candidates:
                try:
                    v = barco_obj.get(k)
                    if v is not None:
                        return v
                except Exception:
                    continue
    except Exception:
        pass
    try:
        for k in key_candidates:
            if hasattr(barco_obj, k):
                v = getattr(barco_obj, k)
                if v is not None:
                    return v
        # case-insensitive attribute fallback
        d = getattr(barco_obj, "__dict__", None)
        if isinstance(d, dict):
            for attr in d:
                for k in key_candidates:
                    if str(attr).lower() == str(k).lower():
                        v = getattr(barco_obj, attr)
                        if v is not None:
                            return v
    except Exception:
        pass
    return default


def _set_field(barco_obj, key: str, value):
    """
    Escribir un campo en el objeto barco sin cambiar su tipo.
    Prioriza dict assignment, luego setattr.
    """
    if barco_obj is None:
        return
    try:
        if isinstance(barco_obj, dict):
            barco_obj[key] = value
            return
    except Exception:
        pass
    try:
        setattr(barco_obj, key, value)
        return
    except Exception:
        pass
    try:
        d = getattr(barco_obj, "__dict__", None)
        if isinstance(d, dict):
            d[key] = value
    except Exception:
        pass


class VentanaMejoras(tk.Toplevel):
    """
    Ventana Astillero: trabaja sobre el objeto `barco` recibido y llama callback_actualizar(barco).
    """

    SIZE_TO_MAX_MEJ = {
        "XL": 4,
        "L": 3,
        "M": 2,
        "S": 1,
        "T": 0,
    }

    CREW_MULTIPLIERS = {
        "REGULAR": 1.0,
        "VETERANA": 1.2,
        "VETERANO": 1.2,
        "INEXPERTA": 0.8,
        "INEXPERIENCED": 0.8,
    }

    INCOMPATIBILIDADES = {
        "Sobreartillado": {"Carronadas Extra"},
        "Carronadas Extra": {"Sobreartillado"},
    }

    def __init__(self, parent, datos, barco, callback_actualizar: Callable[[Any], None]):
        super().__init__(parent)
        self.parent = parent
        self.datos = datos
        self.barco = barco  # Debe actualizarse in-place
        self.callback_actualizar = callback_actualizar

        # Título con nombre del barco al lado de "Astillero —"
        nombre = _get_field(self.barco, ["NOMBRE", "Nombre", "name", "referencia_id"], "")
        self.title(f"Astillero — {nombre}")

        # Visual (no tocar)
        self._default_w, self._default_h = 980, 680
        self.geometry(f"{self._default_w}x{self._default_h}")
        self.minsize(760, 480)
        self.configure(bg=NAVAL_BG)

        # Canvas background (estética)
        self._canvas = tk.Canvas(self, highlightthickness=0, bg=NAVAL_BG)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Background image state
        self._bg_photo = None
        self._bg_orig = None
        self._bg_item_id = None

        # Widgets and state
        self._widgets_created = False
        self._widget_items: Dict[str, int] = {}

        self._mejoras_cache: List[Dict[str, Any]] = []
        self._oficiales_cache: List[Dict[str, Any]] = []
        self.combos_mejoras: List[ttk.Combobox] = []
        self.combo_oficial: Optional[ttk.Combobox] = None
        self.combo_trip: Optional[ttk.Combobox] = None
        self.combo_estado: Optional[ttk.Combobox] = None
        self.entry_id_custom: Optional[tk.Entry] = None
        self.text_mejoras: Optional[tk.Text] = None
        self.text_oficial: Optional[tk.Text] = None
        self.scroll_text_mejoras: Optional[tk.Scrollbar] = None

        # Styles (visual only)
        self._setup_styles()

        # locate excel and background
        self._excel_path = self._find_excel()
        self._bg_path = self._find_bg()

        # Defer loading background and widgets
        self.after(10, self._load_background_image)
        self.after(20, self._crear_widgets)

        self.bind("<Configure>", self._on_resize)

        try:
            self.transient(parent)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            try:
                self.grab_set_global()
            except Exception:
                pass

        logger.info("VentanaMejoras inicializada para %s", nombre)

    # ---------------------------
    # Styles (visual only)
    # ---------------------------
    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("VM.TCombobox", fieldbackground=_BEIGE, background=_BEIGE, foreground=_NAVAL_TEXT)
        style.configure("VM.TEntry", fieldbackground=_BEIGE, background=_BEIGE, foreground=_NAVAL_TEXT)
        style.configure("VM.TLabel", background=NAVAL_BG, foreground=_NAVAL_TEXT, font=FONT_NORMAL)

    # ---------------------------
    # Excel / datos helpers
    # ---------------------------
    def _find_excel(self) -> Optional[Path]:
        for p in EXCEL_CANDIDATES:
            if p.exists():
                return p
        return None

    def _find_bg(self) -> Optional[Path]:
        for p in BG_CANDIDATES:
            if p.exists():
                return p
        return None

    def _load_mejoras_global(self) -> List[Dict[str, Any]]:
        """
        Cargar mejoras desde la API de datos (preferible) o desde la hoja MEJORAS del Excel.
        Devuelve lista de dicts con claves normalizadas: NOMBRE, COSTE, DESCRIPCION, TAMANO.
        """
        mejoras: List[Dict[str, Any]] = []
        try:
            # Preferir API pública si existe
            if self.datos and hasattr(self.datos, "_cache"):
                raw = self.datos._cache.get("MEJORAS")
                if raw is not None:
                    # pandas DataFrame
                    if PANDAS_AVAILABLE and hasattr(raw, "iterrows"):
                        cols = raw.columns
                        col_nom = next((c for c in cols if "nom" in str(c).lower() or "name" in str(c).lower()), None)
                        col_p = next((c for c in cols if "punt" in str(c).lower() or "cost" in str(c).lower()), None)
                        col_desc = next((c for c in cols if "desc" in str(c).lower() or "descr" in str(c).lower()), None)
                        col_tam = next((c for c in cols if "tam" in str(c).lower() or "size" in str(c).lower()), None)
                        for _, r in raw.iterrows():
                            mejoras.append({
                                "NOMBRE": r.get(col_nom, "") if col_nom else r.get("NOMBRE", ""),
                                "COSTE": r.get(col_p, 0) if col_p else r.get("COSTE", 0),
                                "DESCRIPCION": r.get(col_desc, "") if col_desc else r.get("DESCRIPCION", ""),
                                "TAMANO": r.get(col_tam, "") if col_tam else r.get("TAMANO", "")
                            })
                        return mejoras
                    # openpyxl fallback: list of dicts
                    if isinstance(raw, list):
                        for r in raw:
                            mejoras.append({
                                "NOMBRE": r.get("Nombre") or r.get("NOMBRE") or r.get("name") or "",
                                "COSTE": r.get("Coste") or r.get("COSTE") or r.get("Puntos") or 0,
                                "DESCRIPCION": r.get("Descripción") or r.get("DESCRIPCION") or r.get("Desc") or "",
                                "TAMANO": r.get("Tamaño") or r.get("TAMANO") or r.get("Tamano") or ""
                            })
                        return mejoras
        except Exception:
            logger.exception("Error cargando mejoras desde datos._cache")

        # Pandas direct read as fallback
        if PANDAS_AVAILABLE and self._excel_path:
            try:
                df = pd.read_excel(self._excel_path, sheet_name="MEJORAS", engine="openpyxl")
                df.columns = [str(c).strip() for c in df.columns]
                cols = df.columns
                col_nom = next((c for c in cols if "nom" in str(c).lower() or "name" in str(c).lower()), None)
                col_p = next((c for c in cols if "punt" in str(c).lower() or "cost" in str(c).lower()), None)
                col_desc = next((c for c in cols if "desc" in str(c).lower() or "descr" in str(c).lower()), None)
                col_tam = next((c for c in cols if "tam" in str(c).lower() or "size" in str(c).lower()), None)
                for _, r in df.iterrows():
                    mejoras.append({
                        "NOMBRE": r.get(col_nom, "") if col_nom else r.get("NOMBRE", ""),
                        "COSTE": r.get(col_p, 0) if col_p else r.get("COSTE", 0),
                        "DESCRIPCION": r.get(col_desc, "") if col_desc else r.get("DESCRIPCION", ""),
                        "TAMANO": r.get(col_tam, "") if col_tam else r.get("TAMANO", "")
                    })
                return mejoras
            except Exception:
                logger.exception("Error leyendo hoja MEJORAS con pandas")

        return mejoras

    def _load_oficiales_global(self) -> List[Dict[str, Any]]:
        """
        Cargar oficiales desde la hoja OFICIALES (Oficiales de Renombre).
        Normaliza claves: Nombre, Puntos, Descripción, Facción.
        """
        oficiales: List[Dict[str, Any]] = []
        try:
            if self.datos and hasattr(self.datos, "_cache"):
                raw = self.datos._cache.get("OFICIALES")
                if raw is not None:
                    if PANDAS_AVAILABLE and hasattr(raw, "iterrows"):
                        cols = raw.columns
                        col_nom = next((c for c in cols if "nom" in str(c).lower() or "name" in str(c).lower()), None)
                        col_p = next((c for c in cols if "punt" in str(c).lower() or "cost" in str(c).lower()), None)
                        col_desc = next((c for c in cols if "desc" in str(c).lower() or "descr" in str(c).lower()), None)
                        col_fac = next((c for c in cols if "facc" in str(c).lower() or "faction" in str(c).lower()), None)
                        for _, r in raw.iterrows():
                            oficiales.append({
                                "Nombre": r.get(col_nom, "") if col_nom else r.get("Nombre", ""),
                                "Puntos": r.get(col_p, 0) if col_p else r.get("Puntos", 0),
                                "Descripción": r.get(col_desc, "") if col_desc else r.get("Descripción", ""),
                                "Facción": r.get(col_fac, "") if col_fac else r.get("Facción", "")
                            })
                        return oficiales
                    if isinstance(raw, list):
                        for r in raw:
                            oficiales.append({
                                "Nombre": r.get("Nombre") or r.get("name") or "",
                                "Puntos": r.get("Puntos") or r.get("Coste") or 0,
                                "Descripción": r.get("Descripción") or r.get("Desc") or "",
                                "Facción": r.get("Facción") or r.get("Faction") or ""
                            })
                        return oficiales
        except Exception:
            logger.exception("Error cargando oficiales desde datos._cache")

        # Pandas fallback
        if PANDAS_AVAILABLE and self._excel_path:
            try:
                df = pd.read_excel(self._excel_path, sheet_name="OFICIALES", engine="openpyxl")
                df.columns = [str(c).strip() for c in df.columns]
                cols = df.columns
                col_nom = next((c for c in cols if "nom" in str(c).lower() or "name" in str(c).lower()), None)
                col_p = next((c for c in cols if "punt" in str(c).lower() or "cost" in str(c).lower()), None)
                col_desc = next((c for c in cols if "desc" in str(c).lower() or "descr" in str(c).lower()), None)
                col_fac = next((c for c in cols if "facc" in str(c).lower() or "faction" in str(c).lower()), None)
                for _, r in df.iterrows():
                    oficiales.append({
                        "Nombre": r.get(col_nom, "") if col_nom else r.get("Nombre", ""),
                        "Puntos": r.get(col_p, 0) if col_p else r.get("Puntos", 0),
                        "Descripción": r.get(col_desc, "") if col_desc else r.get("Descripción", ""),
                        "Facción": r.get(col_fac, "") if col_fac else r.get("Facción", "")
                    })
                return oficiales
            except Exception:
                logger.exception("Error leyendo hoja OFICIALES con pandas")

        return oficiales

    # ---------------------------
    # Background handling (estética)
    # ---------------------------
    def _load_background_image(self):
        if not self._bg_path:
            return
        try:
            if PIL_AVAILABLE:
                img = Image.open(self._bg_path).convert("RGBA")
                max_dim = max(img.width, img.height)
                if max_dim > _MAX_BG_DIM:
                    scale = _MAX_BG_DIM / float(max_dim)
                    img.thumbnail((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                self._bg_orig = img
                w = max(1, self.winfo_width() or self._default_w)
                h = max(1, self.winfo_height() or self._default_h)
                scale = max(w / img.width, h / img.height)
                target = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                resized = img.resize(target, Image.LANCZOS)
                self._bg_photo = ImageTk.PhotoImage(resized, master=self._canvas)
            else:
                self._bg_photo = tk.PhotoImage(master=self._canvas, file=str(self._bg_path))
        except Exception:
            logger.exception("Error cargando imagen de fondo astillero")
            self._bg_photo = None

        if self._bg_photo:
            cw = self._canvas.winfo_width() or self._default_w
            ch = self._canvas.winfo_height() or self._default_h
            iw = self._bg_photo.width()
            ih = self._bg_photo.height()
            x = (cw - iw) // 2
            y = (ch - ih) // 2
            if self._bg_item_id and self._canvas.type(self._bg_item_id) == "image":
                self._canvas.itemconfig(self._bg_item_id, image=self._bg_photo)
                self._canvas.coords(self._bg_item_id, x, y)
            else:
                self._bg_item_id = self._canvas.create_image(x, y, anchor="nw", image=self._bg_photo, tags="bg_astillero")
            try:
                self._canvas.tag_lower(self._bg_item_id)
            except Exception:
                pass
            self._update_positions_and_place_widgets()

    def _resize_background(self):
        if not PIL_AVAILABLE or self._bg_orig is None:
            return
        try:
            w = max(1, self.winfo_width())
            h = max(1, self.winfo_height())
            img = self._bg_orig
            scale = max(w / img.width, h / img.height)
            new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            resized = img.resize(new_size, Image.LANCZOS)
            self._bg_photo = ImageTk.PhotoImage(resized, master=self._canvas)
            if self._bg_item_id and self._canvas.type(self._bg_item_id) == "image":
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
                self._bg_item_id = self._canvas.create_image(x, y, anchor="nw", image=self._bg_photo, tags="bg_astillero")
            try:
                self._canvas.tag_lower(self._bg_item_id)
            except Exception:
                pass
        except Exception:
            logger.exception("Error redimensionando imagen de fondo astillero")

    # ---------------------------
    # UI creation (no cambiar estética)
    # ---------------------------
    def _crear_widgets(self):
        if self._widgets_created:
            return
        try:
            # Entry ID custom
            self.entry_id_custom = tk.Entry(self._canvas, width=28, fg=_NAVAL_TEXT, bg=_BEIGE,
                                           relief="flat", bd=1, insertbackground=_NAVAL_TEXT,
                                           selectbackground=_SELECT_BG, selectforeground=_NAVAL_TEXT)

            # Estado / Trip
            self.combo_estado = ttk.Combobox(self._canvas, values=["ACTIVO", "CAPTURADO"], state="readonly",
                                             width=18, style="VM.TCombobox")
            self.combo_estado.bind("<<ComboboxSelected>>", lambda e: self._on_estado_change())

            # Tripulación combobox (puede ocultarse para renombre)
            self.combo_trip = ttk.Combobox(self._canvas, values=["REGULAR", "VETERANA", "INEXPERTA"], state="readonly",
                                           width=18, style="VM.TCombobox")
            self.combo_trip.bind("<<ComboboxSelected>>", lambda e: self._on_trip_change())

            # Cargar caches desde Excel / datos
            self._mejoras_cache = self._load_mejoras_global()
            self._oficiales_cache = self._load_oficiales_global()

            # Determinar renombre y tamaño para crear ranuras de mejora
            # --- OBTENER REGISTRO BASE DESDE datos.build_barco_base(ref) ---
            ref = _get_field(self.barco, ["referencia_id", "referencia", "REF", "NOMBRE", "Nombre"], None)
            base = {}
            if ref and self.datos and hasattr(self.datos, "build_barco_base"):
                try:
                    base = self.datos.build_barco_base(ref) or {}
                except Exception:
                    base = {}

            nombre_val = str((base.get("NOMBRE") or base.get("Nombre") or _get_field(self.barco, ["NOMBRE", "Nombre", "name", "referencia_id"], ""))).strip()
            tipo_val = str((base.get("TIPO") or base.get("Tipo") or _get_field(self.barco, ["TIPO", "Tipo"], ""))).strip()
            tam = str((base.get("TAMAÑO") or base.get("TAMANO") or base.get("Tamaño") or _get_field(self.barco, ["TAMAÑO", "TAMANO", "Tamaño", "size"], ""))).strip().upper()
            faccion_base = str((base.get("Facción") or base.get("FACCION") or base.get("Faccion") or "")).strip()

            # CORRECCIÓN: Un barco es de Renombre si RENOMBRE == True o TIPO != NOMBRE
            es_renombre = bool(_get_field(self.barco, ["RENOMBRE"], False) or (nombre_val and tipo_val and nombre_val != tipo_val))
            _set_field(self.barco, "ES_RENOMBRE", es_renombre)

            # Filtrar mejoras por tamaño (exact match en TAMANO si existe)
            mejoras_disponibles = []
            for m in self._mejoras_cache:
                tam_m = str(m.get("TAMANO") or m.get("TAMANO", "") or m.get("Tamaño") or "").strip().upper()
                if not tam_m:
                    mejoras_disponibles.append(m)
                else:
                    if tam and tam_m == tam:
                        mejoras_disponibles.append(m)
            nombres_mejoras = sorted({(m.get("NOMBRE") or m.get("Nombre") or "").strip() for m in mejoras_disponibles if (m.get("NOMBRE") or m.get("Nombre"))})

            # Crear ranuras de mejoras solo si NO es renombre y el barco es genérico (TIPO == NOMBRE)
            self.combos_mejoras = []
            es_generico = (nombre_val == tipo_val)
            show_mejoras = (not es_renombre) and es_generico
            if show_mejoras:
                max_mej = self.SIZE_TO_MAX_MEJ.get(tam, None)
                if max_mej is None:
                    if "XL" in tam:
                        max_mej = 4
                    elif "L" in tam:
                        max_mej = 3
                    elif "M" in tam:
                        max_mej = 2
                    elif "S" in tam:
                        max_mej = 1
                    elif "T" in tam:
                        max_mej = 0
                    else:
                        max_mej = 0
                for i in range(max_mej):
                    cb = ttk.Combobox(self._canvas, values=[""] + nombres_mejoras, state="readonly", width=40, style="VM.TCombobox")
                    cb._slot_index = i
                    cb.bind("<<ComboboxSelected>>", lambda e, _cb=cb: self._on_mejora_change(_cb))
                    self.combos_mejoras.append(cb)
            else:
                self.combos_mejoras = []

            # Oficial combobox (se mostrará solo oficiales de la facción)
            self.combo_oficial = ttk.Combobox(self, values=[""], state="readonly", width=40, style="VM.TCombobox")
            self.combo_oficial.bind("<<ComboboxSelected>>", lambda e: self._on_oficial_change())

            # Botones
            self._btn_guardar = tk.Button(self._canvas, text="Guardar", bg=_BEIGE, fg=_NAVAL_TEXT, relief=tk.FLAT, command=self._on_guardar)
            self._btn_cancel = tk.Button(self._canvas, text="Cancelar", bg=_BEIGE, fg=_NAVAL_TEXT, relief=tk.FLAT, command=self._on_cancelar)

            # Panel derecho (efectos aplicados)
            self.text_mejoras = tk.Text(self._canvas, width=40, height=24, wrap="word",
                                       bg=_BEIGE, fg=_NAVAL_TEXT, relief="flat", highlightthickness=0,
                                       selectbackground=_SELECT_BG, selectforeground=_NAVAL_TEXT, insertbackground=_NAVAL_TEXT)
            self.text_mejoras.configure(state="disabled")
            self.scroll_text_mejoras = tk.Scrollbar(self._canvas, orient="vertical", troughcolor=_BEIGE, bg=_BEIGE)
            try:
                self.text_mejoras.configure(yscrollcommand=self.scroll_text_mejoras.set)
                self.scroll_text_mejoras.configure(command=self.text_mejoras.yview)
            except Exception:
                pass

            self.text_oficial = tk.Text(self._canvas, width=40, height=6, wrap="word",
                                        bg=_BEIGE, fg=_NAVAL_TEXT, relief="flat", highlightthickness=0,
                                        selectbackground=_SELECT_BG, selectforeground=_NAVAL_TEXT, insertbackground=_NAVAL_TEXT)
            self.text_oficial.configure(state="disabled")

            self._widgets_created = True

            # Cargar valores iniciales y colocar widgets
            self._cargar_valores_iniciales()
            self._update_positions_and_place_widgets()
        except Exception:
            logger.exception("Error creando widgets en VentanaMejoras")

    # ---------------------------
    # Posicionamiento (sin cambios estéticos)
    # ---------------------------
    def _compute_vertical_area(self) -> Tuple[int, int]:
        ch = self._canvas.winfo_height() or self._default_h
        area_h = max(300, int(ch * 0.62))
        area_y = int(ch * 0.18)
        return area_y, area_h

    def _update_positions_and_place_widgets(self):
        cw = self._canvas.winfo_width() or self._default_w
        content_x = max(0, (cw - CONTENT_WIDTH) // 2)
        area_y, area_h = self._compute_vertical_area()
        self._place_widgets(content_x, area_y, area_h)

    def _place_widgets(self, content_x: int, area_y: int, area_h: int):
        if not self._widgets_created:
            return
        try:
            def place_widget(widget, key, x, y, anchor="nw", width=None, height=None):
                if key in self._widget_items and self._widget_items[key] is not None:
                    try:
                        self._canvas.coords(self._widget_items[key], x, y)
                    except Exception:
                        try:
                            self._canvas.delete(self._widget_items[key])
                        except Exception:
                            pass
                        self._widget_items[key] = self._canvas.create_window(x, y, window=widget, anchor=anchor, width=width, height=height)
                else:
                    self._widget_items[key] = self._canvas.create_window(x, y, window=widget, anchor=anchor, width=width, height=height)

            # Title
            title_x = content_x + 6
            title_y = area_y - 36
            if "title_text" in self._widget_items and self._widget_items["title_text"]:
                try:
                    self._canvas.coords(self._widget_items["title_text"], title_x, title_y)
                except Exception:
                    pass
            else:
                self._widget_items["title_text"] = self._canvas.create_text(
                    title_x, title_y,
                    text=f"Astillero — {_get_field(self.barco, ['NOMBRE','Nombre','name','referencia_id'], '')}",
                    anchor="nw",
                    font=FONT_TITLE,
                    fill=_NAVAL_TEXT
                )

            # Left column origin
            left_x = content_x
            left_y = area_y + 12
            row_h = 30

            # ID label and entry
            key = "label_id"
            if key in self._widget_items and self._widget_items[key]:
                self._canvas.coords(self._widget_items[key], left_x, left_y)
            else:
                self._widget_items[key] = self._canvas.create_text(
                    left_x, left_y,
                    text="ID (opcional):",
                    anchor="nw",
                    font=FONT_NORMAL,
                    fill=_NAVAL_TEXT
                )
            entry_x = left_x + 140
            place_widget(self.entry_id_custom, "entry_id_custom", entry_x, left_y - 4, anchor="nw", width=220)

            # Estado label and combobox (label "Estado" next to combobox)
            left_y += row_h
            if "label_estado" in self._widget_items and self._widget_items["label_estado"]:
                try:
                    self._canvas.coords(self._widget_items["label_estado"], left_x, left_y)
                except Exception:
                    pass
            else:
                self._widget_items["label_estado"] = self._canvas.create_text(
                    left_x, left_y,
                    text="Estado:",
                    anchor="nw",
                    font=FONT_NORMAL,
                    fill=_NAVAL_TEXT
                )
            place_widget(self.combo_estado, "combo_estado", left_x + 120, left_y - 4, width=160)

            # Tripulación: show only if not renombre (renombre hides the trip slot entirely)
            left_y += row_h
            es_renombre = bool(_get_field(self.barco, ["ES_RENOMBRE"], False))
            if not es_renombre:
                if "label_trip" in self._widget_items and self._widget_items["label_trip"]:
                    try:
                        self._canvas.coords(self._widget_items["label_trip"], left_x, left_y)
                    except Exception:
                        pass
                else:
                    self._widget_items["label_trip"] = self._canvas.create_text(
                        left_x, left_y,
                        text="Tripulación:",
                        anchor="nw",
                        font=FONT_NORMAL,
                        fill=_NAVAL_TEXT
                    )
                place_widget(self.combo_trip, "combo_trip", left_x + 120, left_y - 4, width=160)
            else:
                if "label_trip" in self._widget_items and self._widget_items["label_trip"]:
                    try:
                        self._canvas.delete(self._widget_items["label_trip"])
                    except Exception:
                        pass
                    self._widget_items["label_trip"] = None
                if "combo_trip" in self._widget_items and self._widget_items["combo_trip"]:
                    try:
                        self._canvas.delete(self._widget_items["combo_trip"])
                    except Exception:
                        pass
                    self._widget_items["combo_trip"] = None

            # Adjust left_y for mejoras start (keep spacing consistent)
            left_y += row_h

            # Mejoras: numbered labels "Mejora X" — only the exact number of slots created earlier
            if self.combos_mejoras:
                for i, cb in enumerate(self.combos_mejoras):
                    label_key = f"label_mej_{i}"
                    label_text = f"Mejora {i+1}:"
                    if label_key in self._widget_items and self._widget_items[label_key]:
                        try:
                            self._canvas.coords(self._widget_items[label_key], left_x + 6, left_y)
                        except Exception:
                            pass
                    else:
                        self._widget_items[label_key] = self._canvas.create_text(
                            left_x + 6, left_y,
                            text=label_text,
                            anchor="nw",
                            font=FONT_NORMAL,
                            fill=_NAVAL_TEXT
                        )
                    place_widget(cb, f"mej_cb_{i}", left_x + 120, left_y - 4, width=LEFT_COLUMN_WIDTH - 140)
                    left_y += row_h
            else:
                # ensure any previous labels/windows removed
                for i in range(4):
                    label_key = f"label_mej_{i}"
                    cb_key = f"mej_cb_{i}"
                    if label_key in self._widget_items and self._widget_items[label_key]:
                        try:
                            self._canvas.delete(self._widget_items[label_key])
                        except Exception:
                            pass
                        self._widget_items[label_key] = None
                    if cb_key in self._widget_items and self._widget_items[cb_key]:
                        try:
                            self._canvas.delete(self._widget_items[cb_key])
                        except Exception:
                            pass
                        self._widget_items[cb_key] = None

            # Oficial label and combobox (label "Oficial" next to combobox)
            left_y += 6
            if "label_oficial" in self._widget_items and self._widget_items["label_oficial"]:
                try:
                    self._canvas.coords(self._widget_items["label_oficial"], left_x + 6, left_y)
                except Exception:
                    pass
            else:
                self._widget_items["label_oficial"] = self._canvas.create_text(
                    left_x + 6, left_y,
                    text="Oficial:",
                    anchor="nw",
                    font=FONT_NORMAL,
                    fill=_NAVAL_TEXT
                )
            place_widget(self.combo_oficial, "combo_oficial", left_x + 120, left_y - 4, width=LEFT_COLUMN_WIDTH - 140)

            # Buttons
            place_widget(self._btn_guardar, "btn_guardar", left_x + 12, left_y + 48, width=100)
            place_widget(self._btn_cancel, "btn_cancel", left_x + 132, left_y + 48, width=100)

            # Right column
            right_x = content_x + LEFT_COLUMN_WIDTH + COLUMN_GAP
            right_y = area_y + 12
            place_widget(self.text_mejoras, "text_mejoras", right_x, right_y, width=RIGHT_COLUMN_WIDTH, height=area_h - 80)
            sb_x = right_x + RIGHT_COLUMN_WIDTH + 6
            place_widget(self.scroll_text_mejoras, "scroll_text_mejoras", sb_x, right_y, width=12, height=area_h - 80)
            place_widget(self.text_oficial, "text_oficial", right_x, right_y + (area_h - 70), width=RIGHT_COLUMN_WIDTH, height=80)

            # ensure background behind
            try:
                if getattr(self, "_bg_item_id", None):
                    self._canvas.tag_lower(self._bg_item_id)
            except Exception:
                pass

        except Exception:
            logger.exception("Error colocando widgets en VentanaMejoras")

    # ---------------------------
    # Inicialización de valores y actualización
    # ---------------------------
    def _get_barco_faction(self) -> str:
        val = _get_field(self.barco, ["FACCION", "Facción", "FACTION", "Faction", "faccion", "facción"], "")
        return str(val).strip().lower() if val else ""

    def _cargar_valores_iniciales(self):
        try:
            # Cargar caches si están vacíos
            if not self._mejoras_cache:
                self._mejoras_cache = self._load_mejoras_global()
            if not self._oficiales_cache:
                self._oficiales_cache = self._load_oficiales_global()

            # Recalcular renombre y obtener registro base
            ref = _get_field(self.barco, ["referencia_id", "referencia", "REF", "NOMBRE", "Nombre"], None)
            base = {}
            if ref and self.datos and hasattr(self.datos, "build_barco_base"):
                try:
                    base = self.datos.build_barco_base(ref) or {}
                except Exception:
                    base = {}

            nombre_val = str((base.get("NOMBRE") or base.get("Nombre") or _get_field(self.barco, ["NOMBRE", "Nombre", "name", "referencia_id"], ""))).strip()
            tipo_val = str((base.get("TIPO") or base.get("Tipo") or _get_field(self.barco, ["TIPO", "Tipo"], ""))).strip()
            tam = str((base.get("TAMAÑO") or base.get("TAMANO") or base.get("Tamaño") or _get_field(self.barco, ["TAMAÑO", "TAMANO", "Tamaño", "size"], ""))).strip().upper()
            faccion_base = str((base.get("Facción") or base.get("FACCION") or base.get("Faccion") or "")).strip().lower()

            es_renombre = bool(_get_field(self.barco, ["RENOMBRE"], False) or (nombre_val and tipo_val and nombre_val != tipo_val))
            _set_field(self.barco, "ES_RENOMBRE", es_renombre)

            # Estado
            estado = "CAPTURADO" if _get_field(self.barco, ["CAPTURADO"], False) else "ACTIVO"
            try:
                self.combo_estado.set(estado)
            except Exception:
                pass

            # Tripulación: si renombre -> VETERANA forzada y ocultada
            trip = _get_field(self.barco, ["TRIPULACIÓN", "TRIPULACION", "tripulacion_actual", "TRIP"], None)
            if es_renombre:
                trip = "VETERANA"
                try:
                    self.combo_trip.set("VETERANA")
                except Exception:
                    pass
            else:
                # Si hay hoja de tripulaciones, poblar opciones (no obligatorio)
                if PANDAS_AVAILABLE and self._excel_path:
                    try:
                        df = pd.read_excel(self._excel_path, sheet_name="TRIPULACIONES", engine="openpyxl")
                        if df is not None and len(df.columns) > 0:
                            col_nom = df.columns[0]
                            options = list(pd.Series(df[col_nom].dropna().astype(str)).unique())
                            try:
                                self.combo_trip["values"] = options
                            except Exception:
                                pass
                    except Exception:
                        pass
                if trip:
                    try:
                        self.combo_trip.set(trip)
                    except Exception:
                        pass

            # ID custom
            idc = _get_field(self.barco, ["ID_CUSTOM", "id_custom", "ID", "id_interno"], "")
            if self.entry_id_custom is not None:
                try:
                    self.entry_id_custom.delete(0, tk.END)
                    self.entry_id_custom.insert(0, str(idc))
                except Exception:
                    pass

            # Mejoras actuales: set values into the exact number of slots created
            actuales = _get_field(self.barco, ["MEJORAS_LIST", "mejoras_instaladas"], []) or []
            nombres_actuales = []
            for m in actuales:
                if isinstance(m, dict):
                    nombres_actuales.append(m.get("NOMBRE") or m.get("Nombre") or m.get("name") or "")
                else:
                    nombres_actuales.append(str(m))
            for idx, cb in enumerate(self.combos_mejoras):
                nombre = nombres_actuales[idx] if idx < len(nombres_actuales) else ""
                try:
                    cb.set(nombre or "")
                except Exception:
                    pass

            # POBLAR DESPLEGABLE DE OFICIALES: filtrar por facción y excluir oficiales ya usados en la flota
            fac = faccion_base  # lowercased faction from base
            assigned = set()
            try:
                flota = getattr(self.parent, "flota_actual", None)
                if flota:
                    for b in flota:
                        try:
                            if b is self.barco:
                                continue
                            # obtener referencia al oficial asignado en cada barco
                            ofdata = _get_field(b, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
                            if isinstance(ofdata, dict):
                                nombre_ass = (ofdata.get("Nombre") or ofdata.get("NOMBRE") or "").strip()
                                if nombre_ass:
                                    assigned.add(nombre_ass)
                            elif isinstance(ofdata, str) and ofdata.strip():
                                assigned.add(ofdata.strip())
                        except Exception:
                            continue
            except Exception:
                assigned = set()

            # Nombre del oficial actual del barco (para permitir mantenerlo)
            current_of = _get_field(self.barco, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
            current_name = ""
            if isinstance(current_of, dict):
                current_name = (current_of.get("Nombre") or current_of.get("NOMBRE") or "").strip()
            elif isinstance(current_of, str):
                current_name = current_of.strip()

            # Filtrar oficiales por facción exacta (case-insensitive) y excluir asignados (excepto current)
            filtered = []
            for o in self._oficiales_cache:
                nombre_o = (o.get("Nombre") or "").strip()
                fac_o = str((o.get("Facción") or o.get("Faccion") or o.get("Faction") or "")).strip().lower()
                if not nombre_o:
                    continue
                if fac:
                    if fac_o != fac:
                        continue
                else:
                    # Si el barco no tiene facción, no mostrar oficiales (estricto)
                    continue
                if nombre_o in assigned and nombre_o != current_name:
                    continue
                filtered.append(nombre_o)

            vals = [""] + sorted(filtered)
            if self.combo_oficial:
                try:
                    self.combo_oficial["values"] = vals
                except Exception:
                    pass

            # Si hay oficial actual, setearlo
            if current_name:
                try:
                    self.combo_oficial.set(current_name)
                except Exception:
                    pass

            # Si renombre: vaciar mejoras y asegurar MEJORAS_LIST vacío
            if es_renombre:
                for cb in self.combos_mejoras:
                    try:
                        cb.set("")
                    except Exception:
                        pass
                _set_field(self.barco, "MEJORAS_LIST", [])

            # Actualizar panel derecho y totales
            self._actualizar_mejoras_en_barco()
        except Exception:
            logger.exception("Error cargando valores iniciales en Astillero")

    def _actualizar_panel_info(self):
        try:
            self.text_mejoras.configure(state="normal")
            self.text_mejoras.delete("1.0", tk.END)
            # Tripulación block
            trip = _get_field(self.barco, ["TRIPULACIÓN", "tripulacion_actual", "TRIP"], "")
            if trip:
                self.text_mejoras.insert(tk.END, f"Tripulación: {trip}\n\n")
            # Mejoras
            for m in _get_field(self.barco, ["MEJORAS_LIST", "mejoras_instaladas"], []) or []:
                nombre = m.get("NOMBRE") or m.get("Nombre") or m.get("name") or str(m)
                coste = m.get("COSTE") or m.get("Puntos") or ""
                desc = m.get("DESCRIPCION") or m.get("Descripción") or ""
                self.text_mejoras.insert(tk.END, f"- {nombre} (+{coste} pts)\n{desc}\n\n")
            # Oficial summary
            of = _get_field(self.barco, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
            if isinstance(of, dict):
                self.text_mejoras.insert(tk.END, "Oficial asignado:\n")
                nombre = of.get("Nombre") or ""
                coste = of.get("Puntos") or 0
                desc = of.get("Descripción") or ""
                self.text_mejoras.insert(tk.END, f"{nombre} (+{coste} pts)\n{desc}\n\n")
            elif isinstance(of, str) and of.strip():
                self.text_mejoras.insert(tk.END, f"Oficial asignado: {of}\n\n")
            # Total
            total = _get_field(self.barco, ["TOTAL"], None)
            if total is not None:
                self.text_mejoras.insert(tk.END, f"Total puntos del barco: {total}\n")
            self.text_mejoras.configure(state="disabled")

            # Oficial detailed box
            self.text_oficial.configure(state="normal")
            self.text_oficial.delete("1.0", tk.END)
            of = _get_field(self.barco, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
            if isinstance(of, dict):
                nombre = of.get("Nombre") or ""
                coste = of.get("Puntos") or 0
                desc = of.get("Descripción") or ""
                fac = of.get("Facción") or of.get("Faccion") or ""
                self.text_oficial.insert(tk.END, f"Nombre: {nombre}\nCoste: {coste} pts\nFacción: {fac}\n\n{desc}")
            else:
                self.text_oficial.insert(tk.END, "Sin oficial asignado.")
            self.text_oficial.configure(state="disabled")
        except Exception:
            logger.exception("Error actualizando panel info en Astillero")

    # ---------------------------
    # Handlers (lógica)
    # ---------------------------
    def _on_mejora_change(self, cb: ttk.Combobox):
        try:
            seleccionadas = [c.get().strip() for c in self.combos_mejoras if c.get().strip()]
            # Evitar duplicados
            ocurrencias = {}
            for val in seleccionadas:
                ocurrencias[val] = ocurrencias.get(val, 0) + 1
            duplicates = [k for k, v in ocurrencias.items() if v > 1]
            if duplicates:
                messagebox.showwarning("Mejora duplicada", f"La mejora '{duplicates[0]}' ya está seleccionada. No se permiten duplicados.")
                try:
                    cb.set("")
                except Exception:
                    pass
                self._refresh_mejoras_comboboxes()
                self._actualizar_mejoras_en_barco()
                return

            # Incompatibilidades
            for s in seleccionadas:
                inc = self.INCOMPATIBILIDADES.get(s, set())
                for other in seleccionadas:
                    if other != s and other in inc:
                        messagebox.showwarning("Mejoras incompatibles", f"'{s}' es incompatible con '{other}'. No puedes combinarlas.")
                        try:
                            cb.set("")
                        except Exception:
                            pass
                        self._refresh_mejoras_comboboxes()
                        self._actualizar_mejoras_en_barco()
                        return

            # Refrescar opciones y actualizar barco
            self._refresh_mejoras_comboboxes()
            self._actualizar_mejoras_en_barco()
        except Exception:
            logger.exception("Error manejando cambio de mejora")

    def _refresh_mejoras_comboboxes(self):
        try:
            seleccionadas = [c.get().strip() for c in self.combos_mejoras if c.get().strip()]
            bloqueadas_por_incompat = set()
            for s in seleccionadas:
                bloqueadas_por_incompat.update(self.INCOMPATIBILIDADES.get(s, set()))

            nombres = [m.get("NOMBRE") or m.get("Nombre") or "" for m in self._mejoras_cache]
            nombres = [n for n in nombres if n]
            # ensure known special names exist if present in cache; do not hardcode new ones
            for cb in self.combos_mejoras:
                current = cb.get().strip()
                valores = [""] + sorted(nombres)
                # eliminar ya seleccionadas en otros slots
                for sel in seleccionadas:
                    if sel and sel != current and sel in valores:
                        valores.remove(sel)
                # eliminar incompatibles
                for b in list(bloqueadas_por_incompat):
                    if b in valores and b != current:
                        valores.remove(b)
                try:
                    cb["values"] = valores
                except Exception:
                    pass
        except Exception:
            logger.exception("Error refrescando comboboxes de mejoras")

    def _actualizar_mejoras_en_barco(self):
        try:
            seleccionadas = [c.get().strip() for c in self.combos_mejoras if c.get().strip()]
            nuevas = []
            for nombre in seleccionadas:
                m = self._buscar_mejora_por_nombre(nombre)
                if m:
                    nuevas.append(m)
            # Si renombre: no asignar mejoras
            if _get_field(self.barco, ["ES_RENOMBRE"], False):
                nuevas = []
            _set_field(self.barco, "MEJORAS_LIST", nuevas)

            # recalcular totales y actualizar UI
            self._recalcular_total_barco()
            self._actualizar_panel_info()

            # notificar inmediatamente
            try:
                if callable(self.callback_actualizar):
                    self.callback_actualizar(self.barco)
            except Exception:
                pass
        except Exception:
            logger.exception("Error actualizando mejoras en barco")

    def _buscar_mejora_por_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        if not nombre:
            return None
        # Buscar en cache (coincidencia case-insensitive)
        for m in self._mejoras_cache:
            n = (m.get("NOMBRE") or m.get("Nombre") or "").strip()
            if n.lower() == nombre.strip().lower():
                return m
        # fallback: intentar API datos.get_mejora_by_name si existe
        try:
            if self.datos and hasattr(self.datos, "get_mejora_by_name"):
                m = self.datos.get_mejora_by_name(nombre)
                if m:
                    return m
        except Exception:
            pass
        return {"NOMBRE": nombre, "COSTE": 0, "DESCRIPCION": ""}

    def _on_oficial_change(self):
        try:
            nombre = self.combo_oficial.get().strip() if self.combo_oficial else ""
            of = self._buscar_oficial_por_nombre(nombre) if nombre else None

            # Verificar unicidad en la flota
            assigned = set()
            try:
                flota = getattr(self.parent, "flota_actual", None)
                if flota:
                    for b in flota:
                        try:
                            if b is self.barco:
                                continue
                            ofdata = _get_field(b, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
                            if isinstance(ofdata, dict):
                                nombre_ass = (ofdata.get("Nombre") or ofdata.get("NOMBRE") or "").strip()
                                if nombre_ass:
                                    assigned.add(nombre_ass)
                            elif isinstance(ofdata, str) and ofdata.strip():
                                assigned.add(ofdata.strip())
                        except Exception:
                            continue
            except Exception:
                assigned = set()

            current_of = _get_field(self.barco, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
            current_name = ""
            if isinstance(current_of, dict):
                current_name = (current_of.get("Nombre") or current_of.get("NOMBRE") or "").strip()
            elif isinstance(current_of, str):
                current_name = current_of.strip()

            if nombre and nombre in assigned and nombre != current_name:
                messagebox.showwarning("Oficial no disponible", f"El oficial '{nombre}' ya está asignado en la flota. Elige otro.")
                try:
                    if current_name:
                        self.combo_oficial.set(current_name)
                    else:
                        self.combo_oficial.set("")
                except Exception:
                    pass
                return

            # Guardar oficial en barco (dict si existe definición)
            if of:
                _set_field(self.barco, "OFICIAL_DATA", of)
            else:
                _set_field(self.barco, "OFICIAL_DATA", None)

            # recalcular y actualizar UI
            self._recalcular_total_barco()
            self._actualizar_panel_info()

            # notificar
            try:
                if callable(self.callback_actualizar):
                    self.callback_actualizar(self.barco)
            except Exception:
                pass
        except Exception:
            logger.exception("Error manejando cambio de oficial")

    def _buscar_oficial_por_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        if not nombre:
            return None
        for o in self._oficiales_cache:
            n = (o.get("Nombre") or "").strip()
            if n.lower() == nombre.strip().lower():
                return o
        # fallback: usar API datos.get_oficial_by_name_or_id si existe
        try:
            if self.datos and hasattr(self.datos, "get_oficial_by_name_or_id"):
                o = self.datos.get_oficial_by_name_or_id(nombre)
                if o:
                    return o
        except Exception:
            pass
        return None

    def _on_trip_change(self):
        try:
            if _get_field(self.barco, ["ES_RENOMBRE"], False):
                try:
                    self.combo_trip.set("VETERANA")
                except Exception:
                    pass
                _set_field(self.barco, "TRIPULACIÓN", "VETERANA")
            else:
                _set_field(self.barco, "TRIPULACIÓN", self.combo_trip.get() if self.combo_trip else _get_field(self.barco, ["TRIPULACIÓN"], None))

            # recalcular y notificar
            self._recalcular_total_barco()
            self._actualizar_panel_info()
            try:
                if callable(self.callback_actualizar):
                    self.callback_actualizar(self.barco)
            except Exception:
                pass
        except Exception:
            logger.exception("Error manejando cambio de tripulación")

    def _on_estado_change(self):
        try:
            val = self.combo_estado.get() if self.combo_estado else ""
            if val and val.upper() == "CAPTURADO":
                _set_field(self.barco, "CAPTURADO", True)
                _set_field(self.barco, "ESTADO", "CAPTURADO")
            else:
                _set_field(self.barco, "CAPTURADO", False)
                _set_field(self.barco, "ESTADO", "ACTIVO")
            # recalcular y notificar
            self._recalcular_total_barco()
            self._actualizar_panel_info()
            try:
                if callable(self.callback_actualizar):
                    self.callback_actualizar(self.barco)
            except Exception:
                pass
        except Exception:
            logger.exception("Error manejando cambio de estado")

    # ---------------------------
    # Cálculos
    # ---------------------------
    def _obtener_puntos_base(self) -> int:
        # Primero intentar leer desde el objeto BarcoEstado
        for k in ["PUNTOS DE BARCO", "PUNTOS", "PUNTOS_DE_BARCO", "PUNTOS_DE_BARCO"]:
            v = _get_field(self.barco, [k], None)
            if v is not None and str(v).strip() != "":
                return _ensure_int(v, 0)
        # fallback: intentar obtener desde datos.build_barco_base usando referencia_id
        try:
            ref = _get_field(self.barco, ["referencia_id", "referencia", "REF"], None)
            if ref and self.datos and hasattr(self.datos, "build_barco_base"):
                base = self.datos.build_barco_base(ref)
                if base:
                    for k, vv in base.items():
                        if "punt" in str(k).lower() or "cost" in str(k).lower():
                            return _ensure_int(vv, 0)
        except Exception:
            pass
        return 0

    def _calcular_coste_mejoras(self, mejoras: List[Dict[str, Any]]) -> int:
        total = 0
        for m in mejoras:
            try:
                total += _ensure_int(m.get("COSTE") or m.get("PUNTOS") or m.get("Puntos") or 0)
            except Exception:
                continue
        return total

    def _recalcular_total_barco(self):
        try:
            if _get_field(self.barco, ["CAPTURADO"], False):
                total = 0
                _set_field(self.barco, "TOTAL", total)
                return total

            puntos_base = self._obtener_puntos_base()
            mejoras = _get_field(self.barco, ["MEJORAS_LIST", "mejoras_instaladas"], []) or []
            coste_mejoras = self._calcular_coste_mejoras(mejoras)
            oficial = _get_field(self.barco, ["OFICIAL_DATA", "oficial_ref", "OFICIAL"], None)
            puntos_oficial = 0
            if oficial and isinstance(oficial, dict):
                puntos_oficial = _ensure_int(oficial.get("Puntos") or oficial.get("PUNTOS") or 0)

            if _get_field(self.barco, ["ES_RENOMBRE"], False):
                # Renombre: total = puntos barco + puntos oficial (no multiplicador, no mejoras)
                total = puntos_base + puntos_oficial
                _set_field(self.barco, "TOTAL", int(total))
                return int(total)

            trip = str(_get_field(self.barco, ["TRIPULACIÓN", "TRIP", "tripulacion_actual"], "")).strip().upper()
            mult = self.CREW_MULTIPLIERS.get(trip, 1.0)

            base_after = float(puntos_base) * float(mult)
            total_before = base_after + float(coste_mejoras) + float(puntos_oficial)
            total = _round_up_to_10(total_before)

            _set_field(self.barco, "TOTAL", int(total))
            return int(total)
        except Exception:
            logger.exception("Error recalculando total del barco")
            try:
                _set_field(self.barco, "TOTAL", 0)
            except Exception:
                pass
            return 0

    # ---------------------------
    # Bonificaciones locales (aplicadas al guardar)
    # ---------------------------
    def _apply_mejoras_bonificaciones_local(self, barco_obj):
        try:
            mejoras = _get_field(barco_obj, ["MEJORAS_LIST", "mejoras_instaladas"], []) or []
            nombres = []
            for m in mejoras:
                if isinstance(m, dict):
                    nombres.append((m.get("NOMBRE") or m.get("Nombre") or "").strip().lower())
                else:
                    nombres.append(str(m).strip().lower())

            if any(n == "robusto" for n in nombres):
                _set_field(barco_obj, "VIDA_TOTAL", _ensure_int(_get_field(barco_obj, ["VIDA_TOTAL"], 0)) + 20)

            if any(n == "carronadas extra" for n in nombres):
                _set_field(barco_obj, "CARRONADAS_BABOR", _ensure_int(_get_field(barco_obj, ["CARRONADAS_BABOR"], 0)) + 1)
                _set_field(barco_obj, "CARRONADAS_ESTRIBOR", _ensure_int(_get_field(barco_obj, ["CARRONADAS_ESTRIBOR"], 0)) + 1)

            if any(n == "sobreartillado" for n in nombres):
                _set_field(barco_obj, "CANON_PESADO_BABOR", _ensure_int(_get_field(barco_obj, ["CANON_PESADO_BABOR"], 0)) + 1)
                _set_field(barco_obj, "CANON_LIGERO_BABOR", _ensure_int(_get_field(barco_obj, ["CANON_LIGERO_BABOR"], 0)) + 1)
                _set_field(barco_obj, "CANON_PESADO_ESTRIBOR", _ensure_int(_get_field(barco_obj, ["CANON_PESADO_ESTRIBOR"], 0)) + 1)
                _set_field(barco_obj, "CANON_LIGERO_ESTRIBOR", _ensure_int(_get_field(barco_obj, ["CANON_LIGERO_ESTRIBOR"], 0)) + 1)
        except Exception:
            logger.exception("Error aplicando bonificaciones locales")

    # ---------------------------
    # Guardar / Cancelar
    # ---------------------------
    def _on_guardar(self):
        try:
            mejoras_sel = [cb.get().strip() for cb in self.combos_mejoras if cb.get().strip()]
            mejoras_defs = []
            for nombre in mejoras_sel:
                m = self._buscar_mejora_por_nombre(nombre) or {"NOMBRE": nombre, "COSTE": 0, "DESCRIPCION": ""}
                mejoras_defs.append(m)

            oficial_sel = self.combo_oficial.get().strip() if self.combo_oficial else ""
            oficial_def = self._buscar_oficial_por_nombre(oficial_sel) if oficial_sel else None

            id_custom = ""
            try:
                id_custom = self.entry_id_custom.get().strip() if self.entry_id_custom else ""
            except Exception:
                id_custom = ""

            estado_sel = self.combo_estado.get() if self.combo_estado else ""
            trip_sel = self.combo_trip.get() if self.combo_trip else ""

            if _get_field(self.barco, ["ES_RENOMBRE"], False):
                mejoras_defs = []
                trip_sel = "VETERANA"

            # Actualizar el mismo objeto in-place
            _set_field(self.barco, "MEJORAS_LIST", mejoras_defs)
            _set_field(self.barco, "OFICIAL_DATA", oficial_def)
            _set_field(self.barco, "ID_CUSTOM", id_custom)
            _set_field(self.barco, "ESTADO", estado_sel)
            _set_field(self.barco, "TRIPULACIÓN", trip_sel)

            try:
                self._apply_mejoras_bonificaciones_local(self.barco)
            except Exception:
                pass

            try:
                self._recalcular_total_barco()
            except Exception:
                pass

            # Callback con el mismo objeto
            try:
                if callable(self.callback_actualizar):
                    self.callback_actualizar(self.barco)
            except Exception:
                logger.exception("Error llamando callback_actualizar")

            try:
                self.destroy()
            except Exception:
                pass
        except Exception:
            logger.exception("Error en _on_guardar")
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def _on_cancelar(self):
        try:
            self.destroy()
        except Exception:
            pass

    # ---------------------------
    # Resize handler (estética)
    # ---------------------------
    def _on_resize(self, event):
        try:
            self._resize_background()
            self._update_positions_and_place_widgets()
        except Exception:
            pass
