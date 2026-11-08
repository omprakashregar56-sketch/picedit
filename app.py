"""Main window (UI only). All image work is done by picedit.core."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from . import config, core, theme
from .widgets import MenuBar, ScrollFrame, TitleBar

PASSPORT_RATIO = 35 / 45


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def work_area(root):
    """Usable screen area (excludes the Windows taskbar)."""
    try:
        import ctypes
        from ctypes import wintypes
        r = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(r), 0)
        return r.left, r.top, r.right, r.bottom
    except Exception:
        return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.app_name = self.cfg["app_name"]
        self.title(self.app_name)
        self.overrideredirect(True)          # custom title bar
        self.maximized = False
        self._minimized = False
        self._normal_geom = None
        try:
            self.iconbitmap(config.resource_path(os.path.join("assets", "icon.ico")))
        except Exception:
            pass
        self.pal = theme.apply(self, self.cfg["theme"])
        self.ratios = {k: (v[0] / v[1] if v else None) for k, v in self.cfg["ratios"].items()}

        self.base = None
        self._proxy = None
        self.history = []
        self.path = None
        self.files = []
        self.idx = -1
        self.sel = None
        self.start = None
        self.scale = 1.0
        self.ox = self.oy = 0
        self.tkimg = None
        self.scales = []

        self.bright = tk.DoubleVar(value=0)
        self.contrast = tk.DoubleVar(value=0)
        self.angle = tk.DoubleVar(value=0)
        self.tol = tk.IntVar(value=self.cfg["autocrop_tolerance"])
        self.ratio = tk.StringVar(value=self.cfg["default_ratio"])
        self.w = tk.StringVar()
        self.h = tk.StringVar()
        self.keep = tk.BooleanVar(value=True)
        self.kb = tk.StringVar(value=str(self.cfg["target_kb"]))
        self.theme_var = tk.StringVar(value=self.cfg["theme"])
        self.status = tk.StringVar(value="File > Open to load an image (Ctrl+O)")

        self.place_window()
        self.build_ui()
        self.set_theme(self.cfg["theme"])

        self.bind("<Map>", self.on_map)
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_as())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Left>", lambda e: self.step(-1))
        self.bind("<Right>", lambda e: self.step(1))
        self.bind("<Return>", lambda e: self.crop_selection())
        self.after(60, self.init_taskbar)

    # ------------------------------------------------- window handling
    def place_window(self):
        l, t, r, b = work_area(self)
        try:
            ww, hh = (int(v) for v in self.cfg["window_size"].lower().split("x"))
        except Exception:
            ww, hh = 1150, 720
        ww, hh = min(ww, r - l), min(hh, b - t)
        self.geometry(f"{ww}x{hh}+{l + (r - l - ww) // 2}+{t + (b - t - hh) // 2}")
        self.minsize(820, 520)

    def set_appwindow(self):
        """Make the borderless window show in the Windows taskbar."""
        try:
            import ctypes
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.winfo_id())
            style = u.GetWindowLongW(hwnd, -20)
            u.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)
        except Exception:
            pass

    def init_taskbar(self):
        self.set_appwindow()
        self.withdraw()
        self.after(40, self.deiconify)

    def minimize(self):
        self._minimized = True
        self.overrideredirect(False)
        self.update_idletasks()
        self.iconify()

    def on_map(self, e):
        if e.widget is self and self._minimized:
            self._minimized = False
            self.overrideredirect(True)
            self.after(30, self.set_appwindow)

    def toggle_max(self):
        if not self.maximized:
            self._normal_geom = self.geometry()
            l, t, r, b = work_area(self)
            self.geometry(f"{r - l}x{b - t}+{l}+{t}")
        else:
            self.geometry(self._normal_geom)
        self.maximized = not self.maximized
        self.titlebar.set_maximized(self.maximized)

    def grip_start(self, e):
        self._gx, self._gy = e.x_root, e.y_root
        self._gw, self._gh = self.winfo_width(), self.winfo_height()

    def grip_drag(self, e):
        if self.maximized:
            return
        w = max(820, self._gw + e.x_root - self._gx)
        h = max(520, self._gh + e.y_root - self._gy)
        self.geometry(f"{w}x{h}")

    def on_close(self):
        self.cfg["window_size"] = f"{self.winfo_width()}x{self.winfo_height()}" \
            if not self.maximized else self.cfg["window_size"]
        self.cfg["target_kb"] = self.kb.get()
        self.cfg["autocrop_tolerance"] = self.tol.get()
        config.save(self.cfg)
        self.destroy()

    # ------------------------------------------------------------- UI
    def build_ui(self):
        self.shell = tk.Frame(self, highlightthickness=1)
        self.shell.pack(fill="both", expand=True)

        self.titlebar = TitleBar(self.shell, self, self.app_name,
                                 self.minimize, self.toggle_max, self.on_close)
        self.titlebar.pack(side="top", fill="x")

        self.menubar = MenuBar(self.shell)
        self.menubar.pack(side="top", fill="x")
        self.build_menus()

        bottom = ttk.Frame(self.shell)
        bottom.pack(side="bottom", fill="x")
        ttk.Label(bottom, textvariable=self.status, anchor="w").pack(side="left", fill="x", expand=True, padx=6)
        grip = tk.Label(bottom, text="\u25e2", cursor="size_nw_se")
        grip.pack(side="right")
        grip.bind("<ButtonPress-1>", self.grip_start)
        grip.bind("<B1-Motion>", self.grip_drag)
        self.grip = grip

        body = ttk.Frame(self.shell)
        body.pack(fill="both", expand=True, padx=8, pady=6)
        self.side = ScrollFrame(body, width=300)
        self.side.pack(side="right", fill="y")
        self.side.pack_propagate(False)
        self.canvas = tk.Canvas(body, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.canvas.bind("<Configure>", lambda e: self.refresh())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.build_panel(self.side.inner)

    def build_menus(self):
        def menu(items):
            m = tk.Menu(self, tearoff=0)
            for it in items:
                if it is None:
                    m.add_separator()
                else:
                    m.add_command(label=it[0], command=it[1],
                                  accelerator=it[2] if len(it) > 2 else "")
            return m

        file_m = menu([("Open...", self.open_file, "Ctrl+O"),
                       ("Previous Image", lambda: self.step(-1), "Left"),
                       ("Next Image", lambda: self.step(1), "Right"), None,
                       ("Save As...", self.save_as, "Ctrl+S"),
                       ("Save under Target KB...", self.save_kb), None,
                       ("Exit", self.on_close)])
        edit_m = menu([("Undo", self.undo, "Ctrl+Z"), ("Reset to Original", self.reset), None,
                       ("Apply Adjustments", self.commit), None,
                       ("Rotate 90\u00b0 Left", lambda: self.op(lambda im: core.rotate90(im, False))),
                       ("Rotate 90\u00b0 Right", lambda: self.op(lambda im: core.rotate90(im, True))),
                       ("Flip Horizontal", lambda: self.op(lambda im: core.flip(im, True))),
                       ("Flip Vertical", lambda: self.op(lambda im: core.flip(im, False)))])
        tools_m = menu([("Crop Selection", self.crop_selection, "Enter"),
                        ("Passport (3.5\u00d74.5)", self.passport),
                        ("Auto Sign Crop", self.auto_crop), None,
                        ("Resize Pixels", self.apply_resize)])
        theme_m = tk.Menu(self, tearoff=0)
        for n in theme.THEME_NAMES:
            theme_m.add_radiobutton(label=n.capitalize(), value=n, variable=self.theme_var,
                                    command=lambda n=n: self.set_theme(n))
        help_m = menu([("How to use", self.show_help)])

        self.menubar.add("File", file_m)
        self.menubar.add("Edit", edit_m)
        self.menubar.add("Theme", theme_m)
        self.menubar.add("Tools", tools_m)
        self.menubar.add("Help", help_m)
        self.menubar.add("About", command=self.show_about)

    def scale_widget(self, parent, **kw):
        s = tk.Scale(parent, orient="horizontal", showvalue=True, **kw)
        self.scales.append(s)
        return s

    def build_panel(self, p):
        f = ttk.LabelFrame(p, text="Crop Selection", padding=6)
        f.pack(fill="x", pady=4, padx=2)
        ttk.Button(f, text="Crop Selection", style="Primary.TButton",
                   command=self.crop_selection).pack(fill="x", pady=2)
        r = ttk.Frame(f); r.pack(fill="x", pady=2)
        ttk.Button(r, text="Passport (3.5\u00d74.5)", command=self.passport).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(r, text="Auto Sign Crop", command=self.auto_crop).pack(
            side="left", expand=True, fill="x", padx=(2, 0))
        ttk.Combobox(f, textvariable=self.ratio, values=list(self.ratios),
                     state="readonly").pack(fill="x", pady=2)
        self.scale_widget(f, from_=0, to=100, variable=self.tol,
                          label="Auto crop tolerance:").pack(fill="x")

        f = ttk.LabelFrame(p, text="Straighten  Adjustment", padding=6)
        f.pack(fill="x", pady=4, padx=2)
        self.scale_widget(f, from_=-45, to=45, resolution=0.1, variable=self.angle,
                          label="Straighten (-45\u00b0 to 45\u00b0):",
                          command=lambda v: self.refresh()).pack(fill="x")
        self.scale_widget(f, from_=-100, to=100, variable=self.bright, label="Brightness:",
                          command=lambda v: self.refresh()).pack(fill="x")
        self.scale_widget(f, from_=-100, to=100, variable=self.contrast, label="Contrast:",
                          command=lambda v: self.refresh()).pack(fill="x")
        r = ttk.Frame(f); r.pack(fill="x", pady=2)
        ttk.Button(r, text="Apply", command=self.commit).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(r, text="Clear", command=self.clear_sliders).pack(side="left", expand=True, fill="x", padx=(2, 0))

        f = ttk.LabelFrame(p, text="Dimensions (Pixels)", padding=6)
        f.pack(fill="x", pady=4, padx=2)
        f.columnconfigure(1, weight=1)
        ttk.Label(f, text="Width (px):").grid(row=0, column=0, sticky="w", pady=2)
        sw = ttk.Spinbox(f, from_=1, to=30000, textvariable=self.w, width=8,
                         command=lambda: self.sync_size("w"))
        sw.grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(f, text="Height (px):").grid(row=1, column=0, sticky="w", pady=2)
        sh = ttk.Spinbox(f, from_=1, to=30000, textvariable=self.h, width=8,
                         command=lambda: self.sync_size("h"))
        sh.grid(row=1, column=1, sticky="ew", padx=4)
        sw.bind("<KeyRelease>", lambda e: self.sync_size("w"))
        sh.bind("<KeyRelease>", lambda e: self.sync_size("h"))
        ttk.Checkbutton(f, text="Lock Aspect Ratio", variable=self.keep).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Button(f, text="Resize Pixels", command=self.apply_resize).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=2)

        f = ttk.LabelFrame(p, text="Target File Size (KB)", padding=6)
        f.pack(fill="x", pady=4, padx=2)
        r = ttk.Frame(f); r.pack(fill="x")
        ttk.Label(r, text="Max KB:").pack(side="left")
        ttk.Spinbox(r, from_=1, to=100000, textvariable=self.kb, width=8).pack(side="left", padx=4)
        ttk.Button(f, text="Save JPG under KB", command=self.save_kb).pack(fill="x", pady=2)

        f = ttk.LabelFrame(p, text="Rotate / Flip", padding=6)
        f.pack(fill="x", pady=4, padx=2)
        r = ttk.Frame(f); r.pack(fill="x")
        for txt, fn in (("90\u00b0 L", lambda: self.op(lambda im: core.rotate90(im, False))),
                        ("90\u00b0 R", lambda: self.op(lambda im: core.rotate90(im, True))),
                        ("Flip H", lambda: self.op(lambda im: core.flip(im, True))),
                        ("Flip V", lambda: self.op(lambda im: core.flip(im, False)))):
            ttk.Button(r, text=txt, width=5, command=fn).pack(side="left", expand=True, fill="x")

    # ------------------------------------------------------------ theme
    def set_theme(self, name):
        self.cfg["theme"] = name
        self.theme_var.set(name)
        self.pal = p = theme.apply(self, name)
        self.shell.configure(bg=p["bg"], highlightbackground=p["accent"],
                             highlightcolor=p["accent"])
        self.canvas.configure(bg=p["canvas"])
        self.grip.configure(bg=p["bg"], fg=p["fg"])
        for s in self.scales:
            s.configure(**theme.scale_options(p))
        self.titlebar.restyle(p)
        self.menubar.restyle(p)
        self.side.restyle(p)
        self.refresh()

    # ------------------------------------------------------ image state
    def set_base(self, im):
        self.base = im
        self._proxy = None
        self.sel = None
        self.w.set(str(im.width))
        self.h.set(str(im.height))

    def proxy(self):
        if self._proxy is None:
            self._proxy = core.make_preview(self.base, self.cfg["preview_max_side"])
        return self._proxy

    def push(self):
        self.history.append(self.base)
        if len(self.history) > self.cfg["undo_limit"]:
            self.history.pop(0)

    def sliders_active(self):
        return abs(self.angle.get()) > 0.01 or self.bright.get() or self.contrast.get()

    def compute(self, im):
        return core.adjust(im, self.angle.get(), self.bright.get(), self.contrast.get())

    def clear_sliders(self):
        self.angle.set(0); self.bright.set(0); self.contrast.set(0)
        self.refresh()

    def commit(self):
        if self.base is None or not self.sliders_active():
            return
        new = self.compute(self.base)
        self.push()
        self.clear_sliders()
        self.set_base(new)
        self.refresh()

    def op(self, fn):
        if self.base is None:
            return
        self.commit()
        res = fn(self.base)
        if res is None:
            return
        self.push()
        self.set_base(res)
        self.refresh()

    def undo(self):
        if self.base is None:
            return
        if self.sliders_active():
            self.clear_sliders()
        elif self.history:
            self.set_base(self.history.pop())
            self.refresh()

    def reset(self):
        if self.path:
            self.load(self.path)

    # ----------------------------------------------------------- files
    def open_file(self):
        p = filedialog.askopenfilename(
            parent=self, initialdir=self.cfg["last_dir"] or None,
            filetypes=[("Images", " ".join("*" + e for e in core.SUPPORTED)), ("All", "*.*")])
        if p:
            self.load(p)

    def load(self, path):
        try:
            im = core.load_image(path)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}", parent=self)
            return
        self.path = path
        folder = os.path.dirname(path)
        self.cfg["last_dir"] = folder
        self.files = sorted(f for f in os.listdir(folder) if f.lower().endswith(core.SUPPORTED))
        name = os.path.basename(path)
        self.idx = self.files.index(name) if name in self.files else -1
        self.history.clear()
        self.clear_sliders()
        self.set_base(im)
        self.refresh()

    def step(self, d):
        if not self.files or self.idx < 0:
            return
        self.idx = (self.idx + d) % len(self.files)
        self.load(os.path.join(os.path.dirname(self.path), self.files[self.idx]))

    def save_as(self):
        if self.base is None:
            return
        self.commit()
        p = filedialog.asksaveasfilename(
            parent=self, defaultextension=".jpg",
            initialfile=os.path.splitext(os.path.basename(self.path or "image"))[0] + "_edit",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("BMP", "*.bmp"),
                       ("WEBP", "*.webp"), ("TIFF", "*.tif")])
        if not p:
            return
        try:
            core.save_image(self.base, p, self.cfg["jpeg_quality"])
            self.status.set(f"Saved: {p} ({os.path.getsize(p) / 1024:.1f} KB)")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def save_kb(self):
        if self.base is None:
            return
        self.commit()
        try:
            kb = float(self.kb.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid KB number", parent=self)
            return
        p = filedialog.asksaveasfilename(
            parent=self, defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")],
            initialfile=os.path.splitext(os.path.basename(self.path or "image"))[0] + "_small")
        if not p:
            return
        res = core.encode_jpeg_under_kb(self.base, kb)
        if not res:
            messagebox.showerror("Error", "Could not reach that size", parent=self)
            return
        data, size, q = res
        with open(p, "wb") as fh:
            fh.write(data)
        self.status.set(f"Saved {len(data) / 1024:.1f} KB, {size[0]}x{size[1]}px, "
                        f"quality {q} -> {p}")

    # ----------------------------------------------------------- tools
    def crop_selection(self):
        if self.base is None or not self.sel:
            return
        self.op(lambda im: core.crop(im, self.sel))

    def passport(self):
        """Select a centered 3.5 x 4.5 area; adjust by dragging, then Crop Selection."""
        if self.base is None:
            return
        self.commit()
        W, H = self.base.size
        if W / H > PASSPORT_RATIO:
            h = H; w = h * PASSPORT_RATIO
        else:
            w = W; h = w / PASSPORT_RATIO
        x0, y0 = (W - w) / 2, (H - h) / 2
        self.sel = (x0, y0, x0 + w, y0 + h)
        for name, r in self.ratios.items():
            if r and abs(r - PASSPORT_RATIO) < 1e-6:
                self.ratio.set(name)
        self.status.set("Passport area selected. Drag to adjust, then press Crop Selection.")
        self.refresh(keep_status=True)

    def auto_crop(self):
        if self.base is None:
            return
        self.commit()
        res = core.auto_crop(self.base, self.tol.get())
        if res is None:
            self.status.set("Auto crop: no border found (try changing tolerance)")
            return
        self.push()
        self.set_base(res)
        self.refresh()

    def sync_size(self, which):
        if self.base is None or not self.keep.get():
            return
        try:
            if which == "w":
                self.h.set(str(max(1, round(int(self.w.get()) * self.base.height / self.base.width))))
            else:
                self.w.set(str(max(1, round(int(self.h.get()) * self.base.width / self.base.height))))
        except ValueError:
            pass

    def apply_resize(self):
        if self.base is None:
            return
        try:
            w, h = int(self.w.get()), int(self.h.get())
            assert w > 0 and h > 0
        except Exception:
            messagebox.showerror("Error", "Enter valid width and height", parent=self)
            return
        self.op(lambda im: core.resize(im, w, h))

    def show_help(self):
        messagebox.showinfo(
            "How to use",
            "1. File > Open to load an image (Left/Right keys browse the folder).\n"
            "2. Drag on the image to select a crop area, then Crop Selection (Enter).\n"
            "3. Passport (3.5x4.5) selects a passport-ratio area automatically.\n"
            "4. Auto Sign Crop trims the plain border around a signature/scan.\n"
            "5. Use sliders for straighten, brightness, contrast, then Apply.\n"
            "6. Set Max KB and press Save JPG under KB to compress to a size.\n\n"
            "Ctrl+Z = Undo,  Ctrl+S = Save As.", parent=self)

    def show_about(self):
        messagebox.showinfo(
            "About", f"{self.app_name}\nVersion 1.0\n\nImage viewer and editor:\n"
            "crop, resize, straighten, brightness, contrast,\nsave to target KB.",
            parent=self)

    # ---------------------------------------------------------- canvas
    def refresh(self, keep_status=False):
        c = self.canvas
        c.delete("all")
        if self.base is None:
            c.create_text(c.winfo_width() // 2, c.winfo_height() // 2,
                          text="File > Open  (Ctrl+O) to load an image",
                          fill=self.pal["fg"], font=("Segoe UI", 13))
            return
        im = self.compute(self.proxy()) if self.sliders_active() else self.base
        cw, ch = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        s = max(min(cw / im.width, ch / im.height), 0.01)
        self.scale = s
        disp = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        self.tkimg = ImageTk.PhotoImage(disp)
        self.ox = (cw - disp.width) // 2
        self.oy = (ch - disp.height) // 2
        c.create_image(self.ox, self.oy, anchor="nw", image=self.tkimg)
        if self.sel and not self.sliders_active():
            x0, y0, x1, y1 = self.sel
            c.create_rectangle(self.ox + x0 * s, self.oy + y0 * s,
                               self.ox + x1 * s, self.oy + y1 * s,
                               outline=self.pal["select"], width=2, dash=(5, 3))
        if not keep_status:
            kb = os.path.getsize(self.path) / 1024 if self.path and os.path.exists(self.path) else 0
            self.status.set(f"{os.path.basename(self.path or '')}  |  "
                            f"{self.base.width}x{self.base.height}px  |  "
                            f"original file {kb:.1f} KB  |  zoom {s * 100:.0f}%")

    def to_img(self, x, y):
        return ((x - self.ox) / self.scale, (y - self.oy) / self.scale)

    def on_press(self, e):
        if self.base is None:
            return
        self.commit()
        self.refresh()
        x, y = self.to_img(e.x, e.y)
        self.start = (clamp(x, 0, self.base.width), clamp(y, 0, self.base.height))
        self.sel = None

    def on_drag(self, e):
        if not self.start or self.base is None:
            return
        x0, y0 = self.start
        x1, y1 = self.to_img(e.x, e.y)
        x1 = clamp(x1, 0, self.base.width)
        y1 = clamp(y1, 0, self.base.height)
        r = self.ratios.get(self.ratio.get())
        if r:
            sx = 1 if x1 >= x0 else -1
            sy = 1 if y1 >= y0 else -1
            w, h = abs(x1 - x0), abs(y1 - y0)
            if w > h * r:
                w = h * r
            else:
                h = w / r
            x1, y1 = x0 + sx * w, y0 + sy * h
        self.sel = (x0, y0, x1, y1)
        self.refresh()

    def on_release(self, e):
        self.start = None
