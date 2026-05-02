#!/usr/bin/env python3
"""
Batch Image Converter — Aplicación independiente con GUI (tkinter + Pillow)
Dependencias: pip install pillow
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageCms

__version__ = "1.0.0"

Image.MAX_IMAGE_PIXELS = None  # se ajusta en runtime

FILETYPES = (
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
    # RAW formats
    ".nef", ".cr2", ".cr3", ".arw", ".orf", ".rw2", ".dng",
    ".raf", ".pef", ".srw", ".raw", ".nrw",
)

FILTERS = {
    "Nearest (0)":  Image.Resampling.NEAREST,
    "Lanczos (1)":  Image.Resampling.LANCZOS,
    "Bilinear (2)": Image.Resampling.BILINEAR,
    "Bicubic (3)":  Image.Resampling.BICUBIC,
    "Box (4)":      Image.Resampling.BOX,
    "Hamming (5)":  Image.Resampling.HAMMING,
}

CMYK_PROFILE = "USWebCoatedSWOP.icc"
SRGB_PROFILE = "sRGB.icc"


# ═══════════════════════════════════════════════════ conversión ══════════════

RAW_EXTENSIONS = (".nef", ".cr2", ".cr3", ".arw", ".orf", ".rw2",
                  ".dng", ".raf", ".pef", ".srw", ".raw", ".nrw")

def open_raw(path):
    """Abre un archivo RAW con rawpy y devuelve una imagen PIL."""
    import rawpy
    import numpy as np
    with rawpy.imread(path) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=False,
            no_auto_bright=False,
            output_bps=8,
        )
    return Image.fromarray(rgb)


def convert_image(path, cfg, log):
    """Procesa un único archivo de imagen. Devuelve True si tuvo éxito."""
    max_size  = (cfg["size"], cfg["size"])
    dpi       = (cfg["dpi"],  cfg["dpi"])
    resampler = cfg["filter"]
    ext       = os.path.splitext(path)[1].lower()

    try:
        if ext in RAW_EXTENSIONS:
            img = open_raw(path)
        else:
            img = Image.open(path)
    except Exception as e:
        log(f"  ✗ No se pudo abrir: {os.path.basename(path)} — {e}\n")
        return False

    # ── Colorspace ──────────────────────────────────────────────────────────
    if cfg["colorspace"] and img.mode == "CMYK":
        if os.path.exists(CMYK_PROFILE) and os.path.exists(SRGB_PROFILE):
            try:
                img = ImageCms.profileToProfile(img, CMYK_PROFILE, SRGB_PROFILE, outputMode="RGB")
            except Exception as e:
                log(f"  ⚠ CMYK→RGB falló en {os.path.basename(path)}: {e}\n")
                img = img.convert("RGB")
        else:
            img = img.convert("RGB")
    elif cfg["colorspace"] and img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    # ── Redimensionar ────────────────────────────────────────────────────────
    img.thumbnail(max_size, resampler)

    # ── Guardar ──────────────────────────────────────────────────────────────
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        new_path = os.path.splitext(path)[0] + ".jpg"
        save_path = new_path
    else:
        save_path = path

    # Formato de salida elegido por el usuario
    out_fmt   = cfg["format"]  # "PNG" o "JPG"
    ext_out   = ".png" if out_fmt == "PNG" else ".jpg"
    new_path  = os.path.splitext(path)[0] + ext_out
    save_path = new_path

    try:
        if out_fmt == "JPG":
            if img.mode in ("RGBA", "P", "CMYK"):
                img = img.convert("RGB")
            img.save(save_path, format="JPEG", dpi=dpi,
                     quality=cfg["quality"], optimize=cfg["optimize"])
        else:
            img.save(save_path, format="PNG", dpi=dpi, optimize=cfg["optimize"])

        if save_path != path:
            os.remove(path)
    except Exception as e:
        log(f"  ✗ Error al guardar {os.path.basename(path)}: {e}\n")
        return False

    return True


def collect_images(root_path):
    images = []
    for root, _, files in os.walk(root_path):
        for f in files:
            if f.lower().endswith(FILETYPES):
                images.append(os.path.join(root, f))
    return images


# ═══════════════════════════════════════════════════════════════ GUI ══════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Batch Image Converter  v{__version__}")
        self.resizable(False, False)
        self.configure(padx=18, pady=18, bg="#f0f0f0")
        self._build_ui()

    # ─────────────────────────────────────────────────────── construcción UI ──

    def _build_ui(self):
        S = {"padx": 6, "pady": 4}

        # ── Carpeta ──────────────────────────────────────────────────────────
        frm_path = ttk.LabelFrame(self, text=" 📁  Carpeta de imágenes ", padding=10)
        frm_path.grid(row=0, column=0, columnspan=3, sticky="ew", **S)

        # Usar la carpeta donde está el .exe (o el .py si se ejecuta directo)
        if getattr(sys, 'frozen', False):
            default_path = os.path.dirname(sys.executable)
        else:
            default_path = os.path.dirname(os.path.abspath(__file__))
        self.path_var = tk.StringVar(value=default_path)
        ttk.Entry(frm_path, textvariable=self.path_var, width=54).grid(row=0, column=0, padx=(0,6))
        ttk.Button(frm_path, text="Examinar…", command=self._browse).grid(row=0, column=1)

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_path, text="Incluir subcarpetas",
                        variable=self.recursive_var).grid(row=1, column=0, sticky="w", pady=(6,0))

        # ── Parámetros ───────────────────────────────────────────────────────
        frm_p = ttk.LabelFrame(self, text=" ⚙  Parámetros ", padding=10)
        frm_p.grid(row=1, column=0, columnspan=3, sticky="ew", **S)

        def row(label, widget_factory, r, hint=""):
            ttk.Label(frm_p, text=label).grid(row=r, column=0, sticky="w", pady=3)
            w = widget_factory(frm_p)
            w.grid(row=r, column=1, sticky="w", padx=8)
            if hint:
                ttk.Label(frm_p, text=hint, foreground="#888").grid(row=r, column=2, sticky="w")
            return w

        self.dpi_var     = tk.IntVar(value=72)
        self.size_var    = tk.IntVar(value=1000)
        self.quality_var = tk.IntVar(value=80)
        self.mpx_var     = tk.IntVar(value=0)
        self.filter_var  = tk.StringVar(value="Lanczos (1)")

        row("DPI (1–1000):",
            lambda p: ttk.Spinbox(p, from_=1, to=1000, textvariable=self.dpi_var, width=8), 0)

        row("Lado largo máx. (px):",
            lambda p: ttk.Spinbox(p, from_=1, to=100000, textvariable=self.size_var, width=8), 1)

        q_spin = row("Calidad JPEG (1–100):",
                     lambda p: ttk.Spinbox(p, from_=1, to=100, textvariable=self.quality_var,
                                           width=8, command=self._warn_quality), 2,
                     hint="")
        self.quality_var.trace_add("write", lambda *_: self._warn_quality())
        self.quality_warn = ttk.Label(frm_p, text="⚠ >95: poco beneficio", foreground="orange")
        self.quality_warn.grid(row=2, column=2, sticky="w")
        self.quality_warn.grid_remove()

        row("Filtro de reducción:",
            lambda p: ttk.Combobox(p, textvariable=self.filter_var,
                                   values=list(FILTERS.keys()), state="readonly", width=14), 3)

        row("Megapíxeles máx. (0=sin límite):",
            lambda p: ttk.Spinbox(p, from_=0, to=10000, textvariable=self.mpx_var, width=8), 4)

        # Checkboxes en dos columnas
        frm_chk = ttk.Frame(frm_p)
        frm_chk.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8,0))

        self.colorspace_var = tk.BooleanVar(value=False)
        self.optimize_var   = tk.BooleanVar(value=True)
        self.format_var     = tk.StringVar(value="PNG")

        ttk.Checkbutton(frm_chk, text="Convertir a RGB (colorspace)",
                        variable=self.colorspace_var).grid(row=0, column=0, sticky="w", padx=(0,20))
        ttk.Checkbutton(frm_chk, text="Optimizar paleta",
                        variable=self.optimize_var).grid(row=0, column=1, sticky="w")

        # Formato de salida
        frm_fmt = ttk.Frame(frm_chk)
        frm_fmt.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8,0))
        ttk.Label(frm_fmt, text="Formato de salida:").grid(row=0, column=0, sticky="w", padx=(0,12))
        ttk.Radiobutton(frm_fmt, text="PNG  (sin pérdida)",
                        variable=self.format_var, value="PNG").grid(row=0, column=1, sticky="w", padx=(0,12))
        ttk.Radiobutton(frm_fmt, text="JPG  (menor tamaño)",
                        variable=self.format_var, value="JPG").grid(row=0, column=2, sticky="w")

        # ── Botón convertir ──────────────────────────────────────────────────
        self.run_btn = ttk.Button(self, text="▶  Iniciar conversión",
                                  command=self._start, style="Accent.TButton")
        self.run_btn.grid(row=2, column=0, columnspan=3, pady=(6, 4))

        # ── Barra de progreso ────────────────────────────────────────────────
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_lbl = ttk.Label(self, text="", foreground="#555")
        self.progress_lbl.grid(row=3, column=0, columnspan=3)
        self.progressbar = ttk.Progressbar(self, variable=self.progress_var,
                                           maximum=100, length=460)
        self.progressbar.grid(row=4, column=0, columnspan=3, padx=6, pady=(2,6))

        # ── Log ──────────────────────────────────────────────────────────────
        frm_log = ttk.LabelFrame(self, text=" 📋  Log ", padding=6)
        frm_log.grid(row=5, column=0, columnspan=3, sticky="nsew", **S)

        self.log_box = scrolledtext.ScrolledText(frm_log, width=70, height=12,
                                                 state="disabled", font=("Courier", 9),
                                                 bg="#1e1e1e", fg="#d4d4d4",
                                                 insertbackground="white")
        self.log_box.pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────── helpers UI ──

    def _browse(self):
        p = filedialog.askdirectory(initialdir=self.path_var.get())
        if p:
            self.path_var.set(p)

    def _warn_quality(self):
        try:
            q = int(self.quality_var.get())
            if q > 95:
                self.quality_warn.grid()
            else:
                self.quality_warn.grid_remove()
        except Exception:
            pass

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_progress(self, done, total):
        pct = done / total * 100 if total else 0
        self.progress_var.set(pct)
        self.progress_lbl.configure(text=f"{done} / {total} imágenes  ({pct:.0f}%)")

    # ──────────────────────────────────────────────────────────── ejecución ──

    def _start(self):
        path = self.path_var.get()
        if not os.path.isdir(path):
            self._log("⚠ Carpeta no válida.\n")
            return

        self.run_btn.configure(state="disabled", text="⏳ Procesando…")
        self.progress_var.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        cfg = {
            "size":       self.size_var.get(),
            "dpi":        self.dpi_var.get(),
            "quality":    self.quality_var.get(),
            "filter":     FILTERS[self.filter_var.get()],
            "colorspace": self.colorspace_var.get(),
            "optimize":   self.optimize_var.get(),
            "format":     self.format_var.get(),
            "mpx":        self.mpx_var.get(),
        }

        if cfg["mpx"] > 0:
            Image.MAX_IMAGE_PIXELS = cfg["mpx"] * 1_000_000
        else:
            Image.MAX_IMAGE_PIXELS = None

        threading.Thread(target=self._worker, args=(path, cfg), daemon=True).start()

    def _worker(self, path, cfg):
        log = lambda t: self.after(0, self._log, t)

        log(f"Carpeta: {path}\n")
        log(f"DPI={cfg['dpi']}  Tamaño={cfg['size']}px  Calidad={cfg['quality']}  "
            f"Colorspace={cfg['colorspace']}  Optimizar={cfg['optimize']}\n")
        log("─" * 60 + "\n")

        # Recopilar imágenes
        if self.recursive_var.get():
            images = collect_images(path)
        else:
            images = [
                os.path.join(path, f) for f in os.listdir(path)
                if f.lower().endswith(FILETYPES)
            ]

        total = len(images)
        if total == 0:
            log("No se encontraron imágenes.\n")
            self.after(0, lambda: self.run_btn.configure(state="normal", text="▶  Iniciar conversión"))
            return

        # Diagnóstico: mostrar todos los archivos encontrados
        all_files = []
        for r, _, fs in os.walk(path):
            for f in fs:
                all_files.append(f)
        log(f"Archivos totales en carpeta: {len(all_files)}\n")
        for f in all_files[:10]:  # mostrar los primeros 10
            log(f"  · {f}\n")
        log(f"Imágenes encontradas: {total}\n\n")
        self.after(0, self._set_progress, 0, total)

        start = datetime.now()
        ok = 0
        fail = 0
        lock = threading.Lock()

        def task(img_path):
            nonlocal ok, fail
            result = convert_image(img_path, cfg, log)
            with lock:
                if result:
                    ok += 1
                    log(f"  ✓ {os.path.relpath(img_path, path)}\n")
                else:
                    fail += 1
                done = ok + fail
            self.after(0, self._set_progress, done, total)

        with ThreadPoolExecutor() as ex:
            futures = {ex.submit(task, p): p for p in images}
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    log(f"  ✗ Error inesperado: {e}\n")

        elapsed = datetime.now() - start
        s = re.sub(r"\.\d+$", "", str(elapsed))
        log("\n" + "─" * 60 + "\n")
        log(f"✅ Completadas: {ok}   ✗ Errores: {fail}   ⏱ Tiempo: {s}\n")

        self.after(0, lambda: self.run_btn.configure(state="normal", text="▶  Iniciar conversión"))
        if ok > 0:
            self.after(0, lambda: self.bell())


if __name__ == "__main__":
    app = App()
    app.mainloop()