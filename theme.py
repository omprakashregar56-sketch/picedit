"""Colors and widget styling. Add a new palette to THEMES to create a new theme."""
from tkinter import ttk

THEMES = {
    "sunset": {
        "bg": "#f3b67f", "panel": "#fdebd5", "fg": "#2e1405", "canvas": "#f7f0da",
        "accent": "#1c1c70", "select": "#c1121f", "button": "#fff3e3",
        "trough": "#b9a58f", "entry": "#fffaf2", "title": "#e9873f", "titlefg": "#2a1005",
    },
    "dark": {
        "bg": "#252526", "panel": "#2d2d30", "fg": "#e6e6e6", "canvas": "#1b1b1c",
        "accent": "#0a84d6", "select": "#00e5ff", "button": "#3c3c3f",
        "trough": "#4a4a4e", "entry": "#3a3a3d", "title": "#171718", "titlefg": "#ffffff",
    },
    "light": {
        "bg": "#f3f3f3", "panel": "#ffffff", "fg": "#1e1e1e", "canvas": "#d9d9d9",
        "accent": "#0078d4", "select": "#e81123", "button": "#e6e6e6",
        "trough": "#c8c8c8", "entry": "#ffffff", "title": "#dfe6ee", "titlefg": "#102030",
    },
}
THEME_NAMES = list(THEMES)


def get(name):
    return THEMES.get(name, THEMES["sunset"])


def apply(root, name):
    """Style ttk widgets and the root window. Returns the palette."""
    p = get(name)
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=p["bg"])
    style.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["entry"])
    style.configure("TFrame", background=p["bg"])
    style.configure("TLabel", background=p["bg"], foreground=p["fg"])
    style.configure("TLabelframe", background=p["bg"], bordercolor=p["trough"])
    style.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"],
                    font=("Segoe UI", 10, "bold"))
    style.configure("TButton", background=p["button"], foreground=p["fg"], padding=5,
                    bordercolor=p["trough"], font=("Segoe UI", 9, "bold"))
    style.map("TButton", background=[("active", p["trough"])])
    style.configure("Primary.TButton", background=p["accent"], foreground="#ffffff",
                    padding=8, font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", p["select"])])
    style.configure("TCheckbutton", background=p["bg"], foreground=p["fg"])
    style.configure("TEntry", fieldbackground=p["entry"], foreground=p["fg"])
    style.configure("TSpinbox", fieldbackground=p["entry"], foreground=p["fg"])
    style.configure("TCombobox", fieldbackground=p["entry"], foreground=p["fg"])
    style.configure("Vertical.TScrollbar", background=p["button"], troughcolor=p["bg"])
    return p


def scale_options(p):
    """Options for classic tk.Scale widgets."""
    return dict(bg=p["bg"], fg=p["fg"], troughcolor=p["trough"],
                highlightthickness=0, activebackground=p["accent"], bd=0)
