"""Entry point only. All logic lives in the picedit/ package."""
import ctypes

from picedit.app import App

if __name__ == "__main__":
    try:                                  # crisp text on high-DPI Windows screens
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
