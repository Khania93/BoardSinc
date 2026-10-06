# ui/home.py
import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from core.utils import NAVAL_BG, FONT_TITLE, center_window

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
BG_IMAGE = ASSETS_DIR / "fondos" / "bg_map.jpg"
LOGOS_DIR = ASSETS_DIR / "logos"

ASSETS_LOGOS = [
    "black_seas_logo_650.png",
    "logo.png",
    "logo.gif",
    "velero.png",
]

_BEIGE = "#f5e6d3"
_DARK_BROWN = "#4b2e2a"

class HomeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Black Seas")
        self.configure(bg=NAVAL_BG)
        self._default_w, self._default_h = 900, 600
        self.geometry(f"{self._default_w}x{self._default_h}")
        try:
            center_window(self, self._default_w, self._default_h)
        except Exception:
            pass

        self._bg_img_tk = None
        self._orig_img = None
        self._resize_after_id = None

        self._logo_image = None
        self._logo_item = None
        self._logo_text_item = None

        self.entry_nombre = None
        self._entry_item = None
        self._label_item = None
        self._btn_abrir = None
        self._btn_cargar = None
        self._btn_salir = None
        self._btn_items = [None, None, None]
        self._footer_item = None

        self._canvas = tk.Canvas(self, highlightthickness=0, bg=NAVAL_BG)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self.bind("<Configure>", self._on_resize)
        self.after(20, self._init_ui_once)

    def _init_ui_once(self):
        try:
            self._load_background()
        except Exception:
            logger.exception("Fallo en _load_background")
        try:
            self._draw_background()
            self._create_persistent_widgets()
            self._place_widgets()
        except Exception:
            logger.exception("Fallo dibujando UI inicial")

    def _load_background(self):
        try:
            self._canvas.delete("bg_image")
        except Exception:
            pass
        self._bg_img_tk = None
        self._orig_img = None
        if not BG_IMAGE.exists():
            logger.warning("Imagen de fondo no encontrada: %s", BG_IMAGE)
            self._canvas.configure(bg=NAVAL_BG)
            return
        try:
            if PIL_AVAILABLE:
                img = Image.open(BG_IMAGE).convert("RGBA")
                max_dim = max(img.width, img.height)
                if max_dim > 2000:
                    scale = 2000 / float(max_dim)
                    img.thumbnail((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                self._orig_img = img
                cw = max(1, self._canvas.winfo_width() or self._default_w)
                ch = max(1, self._canvas.winfo_height() or self._default_h)
                scale = max(cw / img.width, ch / img.height)
                target_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                resized = img.resize(target_size, Image.LANCZOS)
                self._bg_img_tk = ImageTk.PhotoImage(resized, master=self._canvas)
            else:
                self._bg_img_tk = tk.PhotoImage(file=str(BG_IMAGE))
                self._orig_img = None
        except Exception as e:
            logger.exception("Error cargando imagen de fondo: %s", e)
            self._bg_img_tk = None
            self._canvas.configure(bg=NAVAL_BG)

    def _draw_background(self):
        try:
            self._canvas.delete("bg_image")
        except Exception:
            pass
        if self._bg_img_tk:
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            iw = self._bg_img_tk.width()
            ih = self._bg_img_tk.height()
            x = (cw - iw) // 2
            y = (ch - ih) // 2
            self._canvas.create_image(x, y, anchor="nw", image=self._bg_img_tk, tags="bg_image")
            try:
                self._canvas.tag_lower("bg_image")
            except Exception:
                pass
        else:
            self._canvas.configure(bg=NAVAL_BG)

    def _create_persistent_widgets(self):
        if self._logo_item is None:
            # create_image with no image initially; will be configured in _place_widgets
            self._logo_item = self._canvas.create_image(0, 0, image=None, anchor="n", tags="logo_img")
        if self._label_item is None:
            self._label_item = self._canvas.create_text(
                0, 0,
                text="Nombre de jugador:",
                anchor="w",
                font=("Garamond", 11, "bold"),
                fill=_DARK_BROWN,
                tags="overlay_text"
            )
        if self.entry_nombre is None:
            # Entry con fondo beige y cursor visible
            entry = tk.Entry(
                self._canvas,
                width=36,
                fg=_DARK_BROWN,
                bg=_BEIGE,                 # color de fondo beige
                relief="flat",
                bd=1,
                highlightthickness=0,
                insertbackground=_DARK_BROWN  # color del cursor
            )
            entry.insert(0, "Tripulante")
            # Opcional: borrar placeholder al enfocar
            def _clear_placeholder(e, ent=entry):
                if ent.get() == "Tripulante":
                    ent.delete(0, tk.END)
            def _restore_placeholder(e, ent=entry):
                if not ent.get().strip():
                    ent.insert(0, "Tripulante")
            entry.bind("<FocusIn>", _clear_placeholder)
            entry.bind("<FocusOut>", _restore_placeholder)

            self.entry_nombre = entry
            self._entry_item = self._canvas.create_window(0, 0, window=self.entry_nombre, anchor="w", tags="controls_window")
        if self._btn_items[0] is None:
            btn_open = tk.Button(self._canvas, text="Abrir Generador de Flota", bg="#f5e6d3", fg=_DARK_BROWN,
                                 activebackground="#f5e6d3", activeforeground=_DARK_BROWN, relief="raised", padx=12, pady=6,
                                 command=self._abrir_principal)
            btn_load = tk.Button(self._canvas, text="Cargar flota", bg="#f5e6d3", fg=_DARK_BROWN,
                                 activebackground="#f5e6d3", activeforeground=_DARK_BROWN, relief="raised", padx=12, pady=6,
                                 command=self._cargar_partida)
            btn_exit = tk.Button(self._canvas, text="Salir", bg="#f5e6d3", fg=_DARK_BROWN,
                                 activebackground="#f5e6d3", activeforeground=_DARK_BROWN, relief="raised", padx=12, pady=6,
                                 command=self.destroy)
            id1 = self._canvas.create_window(0, 0, window=btn_open, anchor="center", tags="controls_window")
            id2 = self._canvas.create_window(0, 0, window=btn_load, anchor="center", tags="controls_window")
            id3 = self._canvas.create_window(0, 0, window=btn_exit, anchor="center", tags="controls_window")
            self._btn_items = [id1, id2, id3]
            self._btn_abrir, self._btn_cargar, self._btn_salir = btn_open, btn_load, btn_exit
        if self._footer_item is None:
            footer_text = "Aplicación creada por y para fans. Con la ayuda y soporte de la Comunidad Black Seas España. Programada por: Anna Lara"
            self._footer_item = self._canvas.create_text(
                0, 0,
                text=footer_text,
                anchor="s",
                font=("Garamond", 10, "bold"),
                fill=_DARK_BROWN,
                tags="overlay_text",
                width=int(self._default_w * 0.9),
                justify="center"
            )

    def _place_widgets(self):
        cw = self._canvas.winfo_width() or self._default_w
        ch = self._canvas.winfo_height() or self._default_h
        self.update_idletasks()
        bw1 = self._btn_abrir.winfo_reqwidth()
        bw2 = self._btn_cargar.winfo_reqwidth()
        bw3 = self._btn_salir.winfo_reqwidth()
        btn_gap = 12
        total_w = bw1 + bw2 + bw3 + btn_gap * 2

        # --- LOGO: aumentar tamaño objetivo ---
        target_logo_w = min(int(cw * 0.90), max(400, total_w, int(cw * 0.5)))
        logo_loaded = False

        for fn in ASSETS_LOGOS:
            p = LOGOS_DIR / fn
            if p.exists():
                try:
                    if PIL_AVAILABLE:
                        img = Image.open(p).convert("RGBA")
                        w_img, h_img = img.size
                        scale = min(1.0, target_logo_w / w_img)
                        if scale < 1.0:
                            new_w = max(1, int(w_img * scale))
                            new_h = max(1, int(h_img * scale))
                            img = img.resize((new_w, new_h), Image.LANCZOS)
                        self._logo_image = ImageTk.PhotoImage(img, master=self._canvas)
                        self._canvas.itemconfig(self._logo_item, image=self._logo_image)
                        logo_loaded = True
                        break
                    else:
                        self._logo_image = tk.PhotoImage(file=str(p))
                        self._canvas.itemconfig(self._logo_item, image=self._logo_image)
                        logo_loaded = True
                        break
                except Exception:
                    continue

        if not logo_loaded:
            try:
                self._canvas.itemconfig(self._logo_item, image="")
            except Exception:
                pass
            if self._logo_text_item is None:
                self._logo_text_item = self._canvas.create_text(
                    cw // 2, int(ch * 0.14),
                    text="BLACK SEAS",
                    anchor="n",
                    font=FONT_TITLE if FONT_TITLE else ("Garamond", 36, "bold"),
                    fill=_DARK_BROWN,
                    tags="logo_text"
                )
            else:
                self._canvas.coords(self._logo_text_item, cw // 2, int(ch * 0.14))
                self._canvas.itemconfig(self._logo_text_item, fill=_DARK_BROWN)
        else:
            if self._logo_text_item is not None:
                try:
                    self._canvas.delete(self._logo_text_item)
                except Exception:
                    pass
                self._logo_text_item = None
            logo_img_w = self._logo_image.width() if self._logo_image is not None else 0
            logo_img_h = self._logo_image.height() if self._logo_image is not None else 0
            logo_y = max(12, int(ch * 0.12))
            self._canvas.coords(self._logo_item, cw // 2, logo_y)

        # Colocar label, entry y botones debajo del logo
        lbl_x = cw // 2 - total_w // 2
        controls_y = int(ch * 0.45)
        if self._logo_image is not None:
            logo_h = self._logo_image.height()
            controls_y = min(int(ch * 0.55), int((logo_y + logo_h) + 24))

        self._canvas.coords(self._label_item, lbl_x, controls_y)
        entry_x = lbl_x + 150
        entry_y = controls_y
        self._canvas.coords(self._entry_item, entry_x, entry_y)
        btn_y = controls_y + 48
        start_x = cw // 2 - total_w // 2
        x1 = start_x + bw1 // 2
        x2 = x1 + bw1 // 2 + btn_gap + bw2 // 2
        x3 = x2 + bw2 // 2 + btn_gap + bw3 // 2
        try:
            self._canvas.coords(self._btn_items[0], x1, btn_y)
            self._canvas.coords(self._btn_items[1], x2, btn_y)
            self._canvas.coords(self._btn_items[2], x3, btn_y)
        except Exception:
            for i, wid in enumerate((self._btn_abrir, self._btn_cargar, self._btn_salir)):
                try:
                    if i < len(self._btn_items) and self._btn_items[i] is not None:
                        self._canvas.delete(self._btn_items[i])
                except Exception:
                    pass
            self._btn_items = [
                self._canvas.create_window(x1, btn_y, window=self._btn_abrir, anchor="center", tags="controls_window"),
                self._canvas.create_window(x2, btn_y, window=self._btn_cargar, anchor="center", tags="controls_window"),
                self._canvas.create_window(x3, btn_y, window=self._btn_salir, anchor="center", tags="controls_window"),
            ]
        footer_y = ch - 24
        self._canvas.coords(self._footer_item, cw // 2, footer_y)
        try:
            self._canvas.itemconfig(self._footer_item, width=int(cw * 0.9))
        except Exception:
            pass

    def _on_resize(self, event):
        try:
            if self._resize_after_id:
                self.after_cancel(self._resize_after_id)
        except Exception:
            pass
        def _do_resize():
            if getattr(self, "_orig_img", None) is not None and PIL_AVAILABLE:
                try:
                    w = max(1, self._canvas.winfo_width() or event.width)
                    h = max(1, self._canvas.winfo_height() or event.height)
                    img = self._orig_img
                    scale = max(w / img.width, h / img.height)
                    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                    resized = img.resize(new_size, Image.LANCZOS)
                    self._bg_img_tk = ImageTk.PhotoImage(resized, master=self._canvas)
                except Exception:
                    logger.exception("Error redimensionando imagen de fondo")
            try:
                self._draw_background()
                self._place_widgets()
            except Exception:
                logger.exception("Error redibujando UI tras resize")
        self._resize_after_id = self.after(150, _do_resize)

    def _abrir_principal(self):
        nombre = (self.entry_nombre.get().strip() or "Tripulante")
        try:
            from ui.pantalla_principal import GeneradorFlotaApp
        except Exception as e:
            logger.exception("No se pudo importar pantalla_principal: %s", e)
            messagebox.showerror("Error", f"No se pudo abrir la aplicación principal:\n{e}")
            return
        self.withdraw()
        try:
            app = GeneradorFlotaApp(player_name=nombre)
            app.mainloop()
        except Exception as e:
            logger.exception("Error iniciando GeneradorFlotaApp: %s", e)
            messagebox.showerror("Error", f"No se pudo iniciar la aplicación:\n{e}")
        finally:
            try:
                self.deiconify()
            except Exception:
                pass

    def _cargar_partida(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de partida (JSON)",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        nombre = (self.entry_nombre.get().strip() or "Tripulante")
        try:
            from ui.pantalla_principal import GeneradorFlotaApp
        except Exception as e:
            logger.exception("No se pudo importar pantalla_principal: %s", e)
            messagebox.showerror("Error", f"No se pudo abrir la aplicación principal:\n{e}")
            return
        self.withdraw()
        try:
            app = GeneradorFlotaApp(player_name=nombre, loaded_fleet_path=path)
            app.mainloop()
        except Exception as e:
            logger.exception("Error iniciando GeneradorFlotaApp con partida cargada: %s", e)
            messagebox.showerror("Error", f"No se pudo iniciar la aplicación:\n{e}")
        finally:
            try:
                self.deiconify()
            except Exception:
                pass

if __name__ == "__main__":
    HomeApp().mainloop()
