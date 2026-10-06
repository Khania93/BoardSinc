# ui/ventana_ficha.py
"""
Ventana Ficha del Barco — versión corregida y completa.

Ajustes principales:
- Uso seguro de PIL (Image, ImageTk) a través de ui.widgets exportados.
- Renderizado de fondo optimizado y robusto.
- Panel inferior dinámico (Combate / Mejoras / Daños) correctamente mostrado.
- Mantiene estética y callbacks.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, DefaultDict, List
from collections import defaultdict
from pathlib import Path

import tkinter as tk
from tkinter import scrolledtext, messagebox

# Import widgets module (no circular imports)
import ui.widgets as widgets

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Aliases and constants
NavalStyle = widgets.NavalStyle
ImageCache = widgets.ImageCache
StyledPanel = widgets.StyledPanel
StyledButton = widgets.StyledButton
StyledLabel = widgets.StyledLabel
crop_and_scale_bg_for_size = widgets.crop_and_scale_bg_for_size
BG_FICHA = widgets.BG_FICHA
PIL_AVAILABLE = widgets.PIL_AVAILABLE
_default_cache = widgets.get_default_cache()

# Logic constants
ZONES = ["POPA", "PROA", "BABOR", "ESTRIBOR"]
TYPES = ["CAÑON PESADO", "CAÑON LIGERO", "CARRONADAS", "MORTEROS"]


def _extract_int(v) -> int:
    try:
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        s = str(v).strip()
        if not s:
            return 0
        import re
        m = re.search(r"-?\d+", s)
        if m:
            return int(m.group(0))
        return int(float(s))
    except Exception:
        return 0


def _accumulate_from_record(record: Dict[str, Any], counts: DefaultDict[str, Dict[str, int]]):
    if not isinstance(record, dict):
        return
    for k, v in record.items():
        if not k:
            continue
        kn = str(k).upper()
        if " - " in kn:
            left, right = [p.strip() for p in kn.split(" - ", 1)]
            zona = left
            tipo = right
            for z in ZONES:
                if z in zona:
                    matched = False
                    for t in TYPES:
                        if t in tipo:
                            counts[z][t] += _extract_int(v)
                            matched = True
                            break
                    if not matched:
                        counts[z]["OTROS"] += _extract_int(v)
                    break
        else:
            parts = kn.split()
            if not parts:
                continue
            first = parts[0]
            for z in ZONES:
                if z in first:
                    rest = " ".join(parts[1:])
                    matched = False
                    for t in TYPES:
                        if t in rest:
                            counts[z][t] += _extract_int(v)
                            matched = True
                            break
                    if not matched:
                        counts[z]["OTROS"] += _extract_int(v)
                    break


def _compute_armamento_total(datos_obj, barco_estado) -> Dict[str, Dict[str, int]]:
    counts: DefaultDict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    try:
        base = datos_obj.build_barco_base(barco_estado.referencia_id) or {}
        armas = base.get("_ARMAS") or []
        if isinstance(armas, list):
            for rec in armas:
                if isinstance(rec, dict):
                    _accumulate_from_record(rec, counts)
        # revisar claves sueltas en base
        for k, v in base.items():
            ks = str(k).upper()
            for z in ZONES:
                if ks.startswith(z):
                    rest = ks[len(z):].strip().lstrip("-_ ").strip()
                    if not rest:
                        rest = "OTROS"
                    counts[z][rest] += _extract_int(v)
        # aplicar mejoras instaladas
        for mname in (barco_estado.mejoras_instaladas or []):
            try:
                mdef = datos_obj.get_mejora_by_name(mname)
            except Exception:
                mdef = None
            if mdef and isinstance(mdef, dict):
                _accumulate_from_record(mdef, counts)
    except Exception:
        logger.exception("Error reconstruyendo armamento")
    result = {}
    for z in ZONES:
        result[z] = {}
        for t in TYPES:
            result[z][t] = int(counts[z].get(t, 0) or 0)
        if counts[z].get("OTROS"):
            result[z]["OTROS"] = int(counts[z].get("OTROS", 0))
    return result


def mostrar_ficha_barco(master, barco_estado, datos_obj):
    """
    Muestra la ficha del barco. No se modifica la lógica ni los callbacks.
    Visual: usa widgets StyledPanel y cache de imágenes para evitar parpadeos.
    """
    if barco_estado is None:
        messagebox.showerror("Error", "No se proporcionó un barco.")
        return

    # Recolectar datos (preferir valores del objeto barco_estado, fallback a base)
    try:
        base = datos_obj.build_barco_base(barco_estado.referencia_id) or {}
    except Exception:
        logger.exception("Error obteniendo base del barco")
        base = {}

    # Nombre y armamento
    nombre_barco = base.get("NOMBRE") or base.get("Nombre") or str(barco_estado.referencia_id)
    mejoras_defs = []
    for n in (barco_estado.mejoras_instaladas or []):
        try:
            mejoras_defs.append(datos_obj.get_mejora_by_name(n))
        except Exception:
            logger.exception("Error cargando mejora %s", n)
            mejoras_defs.append(None)
    oficial_def = None
    try:
        if getattr(barco_estado, "oficial_ref", None):
            oficial_def = datos_obj.get_oficial_by_name_or_id(barco_estado.oficial_ref)
    except Exception:
        logger.exception("Error cargando oficial")
        oficial_def = None
    try:
        danos_catalogo = datos_obj.get_danos() or []
    except Exception:
        logger.exception("Error cargando daños")
        danos_catalogo = []

    armamento = _compute_armamento_total(datos_obj, barco_estado)

    # Ventana
    win = tk.Toplevel(master)
    win.title(f"Ficha — {nombre_barco}")
    win.geometry("1100x750")
    try:
        win.transient(master)
    except Exception:
        pass

    # Mostrar datos de pantalla_principal en la parte fija superior si están disponibles
    jugador_text = getattr(master, "nombre_jugador", "") or ""
    puntos_restantes_text = ""
    try:
        # intentar leer desde entry_puntos_objetivo o canvas text
        if hasattr(master, "entry_puntos_objetivo"):
            try:
                objetivo = int(master.entry_puntos_objetivo.get())
            except Exception:
                objetivo = None
            if objetivo is not None:
                usados = sum(master._calcular_total_para_estado(b) for b in getattr(master, "flota_actual", []))
                restantes = max(0, (objetivo or 0) - usados)
                puntos_restantes_text = f"Puntos restantes: {restantes}"
        else:
            # intentar leer canvas text si existe
            try:
                puntos_restantes_text = master._canvas.itemcget(master._restantes_text, "text")
            except Exception:
                puntos_restantes_text = ""
    except Exception:
        puntos_restantes_text = ""

    # caches and images
    win._cache = _default_cache
    win._pil = {}
    win._images = {}
    win._bg_last_size = None
    win._barco_last_size = None
    win._render_debounce = None

    # load background and barco images via cache
    win._pil["main_bg"] = win._cache.load_pil(BG_FICHA)
    velero_path = Path(__file__).resolve().parent.parent / "assets" / "barcos" / "velero.png"
    win._pil["barco"] = win._cache.load_pil(velero_path)

    # Canvas background
    canvas_bg_color = NavalStyle.NAVAL_BG_FALLBACK
    root_canvas = tk.Canvas(win, highlightthickness=0, bg=canvas_bg_color)
    root_canvas.pack(fill=tk.BOTH, expand=True)

    # Optimized background renderer (no unnecessary PhotoImage recreation)
    def _render_background():
        try:
            pil = win._pil.get("main_bg")
            if not pil or not PIL_AVAILABLE:
                root_canvas.configure(bg=canvas_bg_color)
                return
            w = max(1, root_canvas.winfo_width())
            h = max(1, root_canvas.winfo_height())
            pw, ph = pil.size
            scale = max(w / pw, h / ph)
            target = (max(1, int(pw * scale)), max(1, int(ph * scale)))
            if win._bg_last_size == target and win._images.get("main_bg"):
                # only reposition
                if getattr(win, "_bg_main_id", None):
                    cw = root_canvas.winfo_width()
                    ch = root_canvas.winfo_height()
                    iw = win._images["main_bg"].width()
                    ih = win._images["main_bg"].height()
                    x = (cw - iw) // 2
                    y = (ch - ih) // 2
                    try:
                        root_canvas.coords(win._bg_main_id, x, y)
                    except Exception:
                        pass
                return
            # Resize using PIL LANCZOS
            img = pil.resize(target, widgets.Image.LANCZOS) if PIL_AVAILABLE else None
            photo = widgets.ImageTk.PhotoImage(img, master=win) if (PIL_AVAILABLE and img is not None) else None
            win._images["main_bg"] = photo
            win._bg_last_size = target
            if getattr(win, "_bg_main_id", None):
                try:
                    root_canvas.itemconfig(win._bg_main_id, image=photo)
                except Exception:
                    win._bg_main_id = root_canvas.create_image(0, 0, anchor="nw", image=photo)
                    root_canvas.tag_lower(win._bg_main_id)
            else:
                win._bg_main_id = root_canvas.create_image(0, 0, anchor="nw", image=photo)
                root_canvas.tag_lower(win._bg_main_id)
            cw = root_canvas.winfo_width()
            ch = root_canvas.winfo_height()
            iw = photo.width() if photo is not None else 0
            ih = photo.height() if photo is not None else 0
            x = (cw - iw) // 2
            y = (ch - ih) // 2
            try:
                root_canvas.coords(win._bg_main_id, x, y)
                root_canvas.tag_lower(win._bg_main_id)
            except Exception:
                pass
        except Exception:
            logger.exception("Error renderizando fondo principal")

    # call render once and bind resize
    _render_background()
    def _on_root_resize(event=None):
        _render_background()
    root_canvas.bind("<Configure>", lambda e: _on_root_resize())

    # Container frame
    container = tk.Frame(root_canvas, bd=0, bg=canvas_bg_color, highlightthickness=0)
    container_id = root_canvas.create_window(0, 0, anchor="nw", window=container)

    def _make_label(parent, text="", title=False, textvariable=None):
        lbl = StyledLabel(parent, text=text, title=title, textvariable=textvariable)
        if not PIL_AVAILABLE or win._pil.get("main_bg") is None:
            try:
                lbl.configure(bg=canvas_bg_color)
            except Exception:
                pass
        return lbl

    # Layout configuration
    container.columnconfigure(0, weight=0)
    container.columnconfigure(1, weight=1)
    container.rowconfigure(0, weight=1)

    # Left menu panel
    left_panel = StyledPanel(container, win._cache, pil_bg=win._pil.get("main_bg"), key="left_panel")
    left_panel.grid(row=0, column=0, sticky="ns")
    left_panel.columnconfigure(0, weight=1)

    menu_frame = StyledPanel(left_panel, win._cache, pil_bg=win._pil.get("main_bg"), key="menu_frame")
    menu_frame.pack(fill=tk.BOTH, expand=True, padx=NavalStyle.PAD_MED, pady=NavalStyle.PAD_MED)

    btn_combate = StyledButton(menu_frame, "COMBATE")
    btn_mejoras = StyledButton(menu_frame, "MEJORAS")
    btn_danos = StyledButton(menu_frame, "DAÑOS")
    btn_close = StyledButton(menu_frame, "CERRAR")

    btn_combate.pack(fill=tk.X, pady=(8, 8))
    btn_mejoras.pack(fill=tk.X, pady=(8, 8))
    btn_danos.pack(fill=tk.X, pady=(8, 8))
    spacer = tk.Frame(menu_frame, height=8, bd=0)
    spacer.pack(expand=True, fill=tk.BOTH)
    btn_close.pack(fill=tk.X, pady=(8, 8))

    # Header
    header = StyledPanel(container, win._cache, pil_bg=win._pil.get("main_bg"), key="header")
    header.grid(row=0, column=1, sticky="ew", pady=(6, 6), padx=12)
    header.columnconfigure(0, weight=1)
    header.columnconfigure(1, weight=1)
    header.columnconfigure(2, weight=1)

    display_id = getattr(barco_estado, "id_custom", "") or ""
    if not display_id:
        display_id = base.get("NOMBRE") or base.get("Nombre") or ""

    # Top fixed info: mostrar Jugador y Puntos restantes (si master los proporciona)
    top_info_frame = tk.Frame(header, bd=0)
    top_info_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
    lbl_jugador = _make_label(top_info_frame, text=f"Jugador: {jugador_text}", title=False)
    lbl_jugador.pack(side=tk.LEFT, padx=(4, 8))
    lbl_puntos = _make_label(top_info_frame, text=puntos_restantes_text, title=False)
    lbl_puntos.pack(side=tk.RIGHT, padx=(8, 4))

    def _label_pair(parent, row, col, title, value):
        lbl_t = _make_label(parent, text=title + ":", title=True)
        lbl_v = _make_label(parent, text=str(value or ""), title=False)
        lbl_t.grid(row=row * 2, column=col, sticky="w", padx=4, pady=(2, 0))
        lbl_v.grid(row=row * 2 + 1, column=col, sticky="w", padx=4, pady=(0, 4))

    # Cambiado: "Tasa de nudos" en lugar de "Velocidad"
    tasa_nudos_val = ""
    try:
        tasa_nudos_val = getattr(barco_estado, "tasa_nudos", "") or base.get("TASA DE NUDOS") or base.get("TASA_NUDOS") or base.get("VELOCIDAD") or ""
    except Exception:
        tasa_nudos_val = base.get("TASA DE NUDOS") or base.get("VELOCIDAD") or ""

    _label_pair(header, 0, 0, "Nombre", nombre_barco)
    _label_pair(header, 0, 1, "Tipo", base.get("TIPO") or base.get("Tipo") or "")
    _label_pair(header, 0, 2, "Facción", base.get("Facción") or base.get("FACCION") or "")
    _label_pair(header, 1, 0, "ID", display_id)
    _label_pair(header, 1, 1, "Tamaño", base.get("TAMAÑO") or base.get("TAMANO") or "")
    _label_pair(header, 1, 2, "Tasa de nudos", tasa_nudos_val)

    # Central area
    central = StyledPanel(container, win._cache, pil_bg=win._pil.get("main_bg"), key="central")
    central.grid(row=1, column=1, sticky="nsew", pady=(0, 6), padx=12)
    central.columnconfigure(0, weight=2)
    central.columnconfigure(1, weight=3)
    central.columnconfigure(2, weight=1)
    central.rowconfigure(0, weight=1)

    # Info left (zona fija central): eliminar Classe, Desplazamiento y Tripulación base
    info_panel = StyledPanel(central, win._cache, pil_bg=win._pil.get("main_bg"), key="info_panel")
    info_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

    info_items = [
        ("Tripulación actual", getattr(barco_estado, "tripulacion_actual", "") or ""),
        ("Ruptura", base.get("RUPTURA") or ""),
        ("Ángulo", base.get("ANGULO") or base.get("ANGÚLO") or ""),
        ("Habilidad especial", base.get("HABILIDAD") or base.get("Habilidad") or ""),
    ]
    for r, (k, v) in enumerate(info_items):
        lbl_k = _make_label(info_panel, text=k + ":", title=True)
        lbl_v = _make_label(info_panel, text=str(v or ""), title=False)
        lbl_k.grid(row=r, column=0, sticky="w", pady=2)
        lbl_v.grid(row=r, column=1, sticky="w", pady=2, padx=(8, 0))

    # Image center
    image_panel = StyledPanel(central, win._cache, pil_bg=win._pil.get("main_bg"), key="image_panel")
    image_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
    image_panel.columnconfigure(0, weight=1)
    image_panel.rowconfigure(0, weight=1)
    barco_holder = StyledPanel(image_panel, win._cache, pil_bg=win._pil.get("main_bg"), key="barco_holder")
    barco_holder.grid(row=0, column=0, sticky="nsew")
    barco_label = tk.Label(barco_holder, bd=0)
    barco_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # Vida panel (derecha)
    vida_panel = StyledPanel(central, win._cache, pil_bg=win._pil.get("main_bg"), key="vida_panel")
    vida_panel.grid(row=0, column=2, sticky="nse", padx=(8, 0))
    vida_title = _make_label(vida_panel, text="VIDA", title=True)
    vida_title.pack(anchor="w")

    # Compute vida total: base + mejoras
    vida_total_val = 0
    for k, v in base.items():
        if "vida" in str(k).lower():
            try:
                vida_total_val = int(float(v or 0))
            except Exception:
                vida_total_val = 0
            break
    try:
        for mdef in mejoras_defs:
            if isinstance(mdef, dict):
                for mk, mv in mdef.items():
                    if "vida" in str(mk).lower():
                        try:
                            vida_total_val += int(float(mv or 0))
                        except Exception:
                            pass
    except Exception:
        pass

    vida_total_var = tk.IntVar(value=vida_total_val)
    vida_actual_var = tk.IntVar(value=int(getattr(barco_estado, "vida_actual", vida_total_val) or vida_total_val))

    lbl_total = _make_label(vida_panel, text="Total:", title=True)
    lbl_total.pack(anchor="w", pady=(6, 0))
    val_total = _make_label(vida_panel, textvariable=vida_total_var, title=False)
    val_total.pack(anchor="w")
    lbl_actual = _make_label(vida_panel, text="Actual:", title=True)
    lbl_actual.pack(anchor="w", pady=(6, 0))
    val_actual = _make_label(vida_panel, textvariable=vida_actual_var, title=False)
    val_actual.pack(anchor="w")

    # Daño a aplicar entry
    lbl_daño = _make_label(vida_panel, text="Daño a aplicar:", title=True)
    lbl_daño.pack(anchor="w", pady=(8, 0))
    entry_daño = tk.Entry(vida_panel, width=10, font=NavalStyle.NORMAL, fg=NavalStyle.TEXT, relief="flat")
    if not PIL_AVAILABLE or win._pil.get("main_bg") is None:
        try:
            entry_daño.configure(bg=NavalStyle.NAVAL_BG_FALLBACK, insertbackground=NavalStyle.TEXT)
        except Exception:
            pass
    else:
        try:
            entry_daño.configure(insertbackground=NavalStyle.TEXT)
        except Exception:
            pass
    entry_daño.pack(anchor="w", pady=(4, 8))

    impacto_btn = StyledButton(vida_panel, "IMPACTO")
    reparar_btn = StyledButton(vida_panel, "REPARAR")
    impacto_btn.pack(fill=tk.X, pady=(2, 4))
    reparar_btn.pack(fill=tk.X, pady=(0, 2))

    # Ensure barco_estado.danos_activos exists
    try:
        if not isinstance(barco_estado.danos_activos, list):
            barco_estado.danos_activos = getattr(barco_estado, "danos_activos", []) or []
    except Exception:
        barco_estado.danos_activos = getattr(barco_estado, "danos_activos", []) or []

    # Sync function
    def _sync_with_master():
        try:
            barco_estado.vida_actual = int(vida_actual_var.get())
        except Exception:
            pass
        try:
            cb = getattr(master, "_callback_actualizar_barco", None)
            if callable(cb):
                cb(barco_estado)
        except Exception:
            logger.exception("Error llamando callback de master")
        try:
            master.event_generate("<<BARCO_ACTUALIZADO>>", when="tail")
        except Exception:
            pass

    # Impacto / Reparar logic
    def impacto_action():
        try:
            d = int(float(entry_daño.get() or 0))
        except Exception:
            d = 0
        current = int(vida_actual_var.get() or 0)
        nueva = max(0, current - d)
        vida_actual_var.set(nueva)
        try:
            if not isinstance(barco_estado.danos_activos, list):
                barco_estado.danos_activos = []
            barco_estado.danos_activos.append({"nombre": "Impacto", "estado": {"valor": d}})
        except Exception:
            logger.exception("Error registrando impacto en historial")
        _sync_with_master()
        try:
            ruptura_val = int(float(base.get("RUPTURA") or 0))
            if ruptura_val > 0 and nueva <= ruptura_val:
                messagebox.showwarning("Alerta de ruptura", f"Vida actual ({nueva}) es igual o inferior a Ruptura ({ruptura_val}).")
        except Exception:
            pass

    def reparar_action():
        try:
            d = int(float(entry_daño.get() or 0))
        except Exception:
            d = 0
        current = int(vida_actual_var.get() or 0)
        nueva = min(int(vida_total_var.get() or 0), current + d)
        vida_actual_var.set(nueva)
        try:
            if not isinstance(barco_estado.danos_activos, list):
                barco_estado.danos_activos = []
            barco_estado.danos_activos.append({"nombre": "Reparacion", "estado": {"valor": d}})
        except Exception:
            logger.exception("Error registrando reparacion en historial")
        _sync_with_master()

    impacto_btn.configure(command=impacto_action)
    reparar_btn.configure(command=reparar_action)

    # Bottom dynamic panel
    bottom = StyledPanel(container, win._cache, pil_bg=win._pil.get("main_bg"), key="bottom")
    bottom.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=(8, 12))
    bottom.rowconfigure(0, weight=1)
    bottom.columnconfigure(0, weight=1)

    contenido = StyledPanel(bottom, win._cache, pil_bg=win._pil.get("main_bg"), key="contenido")
    combate = StyledPanel(bottom, win._cache, pil_bg=win._pil.get("main_bg"), key="combate")
    mejoras = StyledPanel(bottom, win._cache, pil_bg=win._pil.get("main_bg"), key="mejoras")
    danos = StyledPanel(bottom, win._cache, pil_bg=win._pil.get("main_bg"), key="danos")

    for f in (contenido, combate, mejoras, danos):
        f.grid(row=0, column=0, sticky="nsew")

    # Damage UI state
    damage_buttons: Dict[str, tk.Button] = {}
    damage_vars: Dict[str, bool] = {}

    def _update_damage_description_area(selected_list: List[str], text_widget: scrolledtext.ScrolledText):
        try:
            text_widget.configure(state="normal")
            text_widget.delete("1.0", tk.END)
            if not selected_list:
                text_widget.insert(tk.END, "Seleccione un daño para ver su descripción.")
            else:
                for s in selected_list:
                    desc = ""
                    effects = ""
                    for rec in danos_catalogo:
                        if isinstance(rec, dict) and str(rec.get("Nombre") or "").strip() == s:
                            desc = rec.get("Descripción") or rec.get("Descripcion") or ""
                            effects = rec.get("Efectos") or rec.get("Efecto") or ""
                            break
                    text_widget.insert(tk.END, f"{s}\n\n{desc}\n\nEfectos:\n{effects}\n\n")
            text_widget.configure(state="disabled")
        except Exception:
            logger.exception("Error actualizando descripción de daños")

    def _toggle_damage(name: str, text_widget: scrolledtext.ScrolledText):
        try:
            current = damage_vars.get(name, False)
            new_state = not current
            damage_vars[name] = new_state
            btn = damage_buttons.get(name)
            if btn:
                if new_state:
                    btn.config(relief="sunken", bg=NavalStyle.BTN_ACTIVE, fg=NavalStyle.TEXT)
                else:
                    btn.config(relief="raised", bg=NavalStyle.NAVAL_BG_FALLBACK, fg=NavalStyle.TEXT)
            selected = [n for n, v in damage_vars.items() if v]
            try:
                barco_estado.danos_activos = [{"nombre": s, "estado": {}} for s in selected]
            except Exception:
                logger.exception("Error sincronizando daños activos en barco_estado")
            _update_damage_description_area(selected, text_widget)
            _sync_with_master()
        except Exception:
            logger.exception("Error toggling damage")

    # Populate panels
    def populate_contenido():
        for w in contenido.winfo_children():
            w.destroy()
        lbl = _make_label(contenido, text="Seleccione una opción del menú para visualizar la información.", title=False)
        lbl.pack(expand=True)

    def populate_combate():
        for w in combate.winfo_children():
            w.destroy()
        title = _make_label(combate, text="COMBATE", title=True)
        title.pack(anchor="w")
        grid = tk.Frame(combate, bd=0)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        hdr = _make_label(grid, text="Tipo", title=True)
        hdr.grid(row=0, column=0, padx=6, pady=(0, 6))
        for ci, z in enumerate(ZONES, start=1):
            tk.Label(grid, text=z, font=NavalStyle.LABEL, fg=NavalStyle.TEXT).grid(row=0, column=ci, padx=6, pady=(0, 6))
        for ri, t in enumerate(TYPES, start=1):
            tk.Label(grid, text=t + ":", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).grid(row=ri, column=0, sticky="w", padx=(6, 2))
            for ci, z in enumerate(ZONES, start=1):
                val = armamento.get(z, {}).get(t, 0)
                tk.Label(grid, text=str(val), font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).grid(row=ri, column=ci, padx=6, pady=4)
        any_otros = any("OTROS" in armamento.get(z, {}) for z in ZONES)
        if any_otros:
            r = len(TYPES) + 2
            tk.Label(grid, text="OTROS:", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).grid(row=r, column=0, sticky="w", padx=(6, 2))
            for ci, z in enumerate(ZONES, start=1):
                val = armamento.get(z, {}).get("OTROS", 0)
                tk.Label(grid, text=str(val), font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).grid(row=r, column=ci, padx=6, pady=4)

    def populate_mejoras():
        for w in mejoras.winfo_children():
            w.destroy()
        title = _make_label(mejoras, text="MEJORAS", title=True)
        title.pack(anchor="w")
        cols = tk.Frame(mejoras, bd=0)
        cols.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(cols, bd=0)
        mid = tk.Frame(cols, bd=0)
        rightc = tk.Frame(cols, bd=0)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        rightc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        tk.Label(left, text="Mejoras instaladas", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).pack(anchor="w")
        mejoras_list = getattr(barco_estado, "mejoras_instaladas", []) or []
        if not mejoras_list:
            tk.Label(left, text="Sin mejoras", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w", pady=4)
        else:
            for m in mejoras_list:
                try:
                    mdef = datos_obj.get_mejora_by_name(m) or {}
                except Exception:
                    mdef = {}
                desc = mdef.get("Descripción") or mdef.get("Descripcion") or ""
                tk.Label(left, text=f"{m} - {desc}", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w", pady=2)

        tk.Label(mid, text="Oficial", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).pack(anchor="w")
        if oficial_def and isinstance(oficial_def, dict):
            tk.Label(mid, text=f"{oficial_def.get('Nombre')} - {oficial_def.get('Descripción') or oficial_def.get('Descripcion','')}", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w")
        else:
            tk.Label(mid, text="Sin oficial", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w")

        tk.Label(rightc, text="Regla nacional", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).pack(anchor="w")
        norma = base.get("_NORMA") or {}
        if isinstance(norma, dict) and norma:
            for k, v in norma.items():
                tk.Label(rightc, text=f"{k}: {v}", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w")
        else:
            tk.Label(rightc, text="Sin regla", font=NavalStyle.NORMAL, fg=NavalStyle.TEXT).pack(anchor="w")

    def populate_danos():
        for w in danos.winfo_children():
            w.destroy()
        title = _make_label(danos, text="DAÑOS", title=True)
        title.pack(anchor="w")
        mainf = tk.Frame(danos, bd=0)
        mainf.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(mainf, bd=0)
        rightf = tk.Frame(mainf, bd=0)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        rightf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="Diario de daños", font=NavalStyle.LABEL, fg=NavalStyle.ACCENT).pack(anchor="w")

        known = [d.get("Nombre") if isinstance(d, dict) else str(d) for d in danos_catalogo] or []
        if not known:
            known = ["Aparejo dañado", "Timón dañado", "Filtración", "Incendio"]

        active_names = [dd.get("nombre") for dd in (barco_estado.danos_activos or []) if isinstance(dd, dict)]
        for d in known:
            is_active = d in active_names
            damage_vars[d] = bool(is_active)
            btn = tk.Button(left, text=d, anchor="w", justify="left",
                            relief="sunken" if is_active else "raised",
                            bg=NavalStyle.BTN_ACTIVE if is_active else NavalStyle.NAVAL_BG_FALLBACK,
                            fg=NavalStyle.TEXT, command=lambda _d=d: _toggle_damage(_d, right_text))
            btn.pack(fill=tk.X, pady=2)
            damage_buttons[d] = btn

        right_text = scrolledtext.ScrolledText(rightf, width=40, height=12, wrap="word")
        right_text.pack(fill=tk.BOTH, expand=True)
        _update_damage_description_area(active_names, right_text)

    # Wire menu buttons to populate functions and ensure panels apply background
    def _show_panel(panel_name: str):
        for p in (contenido, combate, mejoras, danos):
            p.grid_remove()
        target = {
            "contenido": contenido,
            "combate": combate,
            "mejoras": mejoras,
            "danos": danos
        }.get(panel_name, contenido)
        target.grid(row=0, column=0, sticky="nsew")
        # call populate for the shown panel
        if panel_name == "contenido":
            populate_contenido()
        elif panel_name == "combate":
            populate_combate()
        elif panel_name == "mejoras":
            populate_mejoras()
        elif panel_name == "danos":
            populate_danos()
        # ensure backgrounds applied
        for p in (contenido, combate, mejoras, danos, left_panel, header, central, vida_panel, image_panel):
            try:
                p.apply_background()
            except Exception:
                pass

    btn_combate.configure(command=lambda: _show_panel("combate"))
    btn_mejoras.configure(command=lambda: _show_panel("mejoras"))
    btn_danos.configure(command=lambda: _show_panel("danos"))
    btn_close.configure(command=win.destroy)

    # Show default panel
    _show_panel("contenido")

    # Ensure StyledPanel backgrounds are applied after layout
    def _deferred_apply_bg():
        for p in (left_panel, menu_frame, header, central, contenido, combate, mejoras, danos, bottom):
            try:
                p.apply_background()
            except Exception:
                pass
    win.after(50, _deferred_apply_bg)

    return win
