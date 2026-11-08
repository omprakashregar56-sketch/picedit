"""Reusable custom widgets: title bar, menu bar, scrollable panel."""
import tkinter as tk
from tkinter import ttk


class TitleBar(tk.Frame):
    """Custom title bar: bold centered title, minimize/maximize/close at top right."""

    def __init__(self, parent, win, title, on_min, on_max, on_close):
        super().__init__(parent, height=44)
        self.win = win
        self.pack_propagate(False)
        self.btns = []
        self.close_btn = self._btn("\u2715", on_close, danger=True)
        self.max_btn = self._btn("\u25a1", on_max)
        self.min_btn = self._btn("\u2014", on_min)
        self.title_lbl = tk.Label(self, text=title, font=("Segoe UI", 16, "bold"))
        self.title_lbl.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self, self.title_lbl):
            w.bind("<ButtonPress-1>", self._start)
            w.bind("<B1-Motion>", self._drag)
            w.bind("<Double-Button-1>", lambda e: on_max())

    def _btn(self, text, cmd, danger=False):
        b = tk.Label(self, text=text, width=5, font=("Segoe UI", 12), cursor="hand2")
        b.pack(side="right", fill="y")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg="#e81123" if danger else self.hover,
                                                fg="#ffffff" if danger else self.fg))
        b.bind("<Leave>", lambda e: b.configure(bg=self.bg, fg=self.fg))
        self.btns.append(b)
        return b

    def set_maximized(self, state):
        self.max_btn.configure(text="\u2750" if state else "\u25a1")

    def _start(self, e):
        self._dx = e.x_root - self.win.winfo_x()
        self._dy = e.y_root - self.win.winfo_y()

    def _drag(self, e):
        if getattr(self.win, "maximized", False):
            return
        self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def restyle(self, p):
        self.bg, self.fg, self.hover = p["title"], p["titlefg"], p["trough"]
        self.configure(bg=self.bg)
        self.title_lbl.configure(bg=self.bg, fg=self.fg)
        for b in self.btns:
            b.configure(bg=self.bg, fg=self.fg)


class MenuBar(tk.Frame):
    """Tab-style menu bar: File, Edit, Theme, Tools, Help, About."""

    def __init__(self, parent):
        super().__init__(parent, height=34)
        self.items = []
        self.menus = []

    def add(self, label, menu=None, command=None):
        lbl = tk.Label(self, text=label, font=("Segoe UI", 11, "bold"), padx=14, cursor="hand2")
        lbl.pack(side="left", fill="y")
        if menu is not None:
            self.menus.append(menu)
            lbl.bind("<Button-1>", lambda e: self._popup(lbl, menu))
        else:
            lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=self.hover))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=self.bg))
        self.items.append(lbl)

    def _popup(self, lbl, menu):
        try:
            menu.tk_popup(lbl.winfo_rootx(), lbl.winfo_rooty() + lbl.winfo_height())
        finally:
            menu.grab_release()

    def restyle(self, p):
        self.bg, self.hover = p["title"], p["trough"]
        self.configure(bg=self.bg)
        for lbl in self.items:
            lbl.configure(bg=self.bg, fg=p["titlefg"])
        for m in self.menus:
            m.configure(bg=p["panel"], fg=p["fg"], activebackground=p["accent"],
                        activeforeground="#ffffff", bd=0, font=("Segoe UI", 10))


class ScrollFrame(ttk.Frame):
    """Vertically scrollable container (mouse wheel works). Put widgets in .inner"""

    def __init__(self, parent, width=290):
        super().__init__(parent, width=width)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, width=width)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        if w is not None and str(w).startswith(str(self)):
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def restyle(self, p):
        self.canvas.configure(bg=p["bg"])
