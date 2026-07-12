import os
import sys


def app_root():
    """Directory for writable data (database, generated PDFs).

    When frozen into a PyInstaller onefile exe, this is the folder the
    exe itself lives in — not the throwaway _MEIPASS temp dir the exe
    unpacks bundled resources into, which is wiped after the process exits.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    """Path to a bundled read-only resource (images, etc.)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
