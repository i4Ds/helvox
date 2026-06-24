import ctypes
import ctypes.util
import os
import platform
import sys
import tempfile
from pathlib import Path

from platformdirs import user_data_path


def app_font(size: int, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    system = platform.system()

    if system == "Windows":
        family = "Segoe UI"
    elif system == "Darwin":
        family = "Helvetica"
    else:
        family = "Arial"

    if bold:
        return (family, size, "bold")

    return (family, size)


def _in_temp_dir(path: Path) -> bool:
    """Return True if *path* is inside the system temporary directory."""
    try:
        tmp = Path(tempfile.gettempdir()).resolve()
        path.resolve().relative_to(tmp)
        return True
    except (ValueError, OSError):
        return False


def _best_exe_path() -> Path:
    """
    Return the path of the *original* executable, not a PyInstaller temp extract.

    PyInstaller --onefile (especially with console=False on Windows) may run the
    app's Python code from a child process whose sys.executable points inside the
    temp _MEIxxxxxx directory rather than the user-placed .exe/.app.
    sys.argv[0] reliably points to the original binary in all known configurations.
    """
    candidates: list[Path] = []

    # argv[0] is the most reliable source; resolve relative paths against cwd.
    if sys.argv and sys.argv[0]:
        a = Path(sys.argv[0])
        if not a.is_absolute():
            a = Path(os.getcwd()) / a
        candidates.append(a)

    candidates.append(Path(sys.executable))

    # Prefer the first candidate that is NOT in the system temp directory.
    for c in candidates:
        try:
            resolved = c.resolve()
            if not _in_temp_dir(resolved):
                return resolved
        except OSError:
            continue

    # Last resort: just use sys.executable even if it is in temp.
    return Path(sys.executable).resolve()


def _macos_detranslocate(app_bundle: Path) -> Path | None:
    """
    Ask the macOS Security framework for the pre-translocation path of *app_bundle*.

    macOS App Translocation runs a quarantined .app from a random read-only path
    under /private/var/folders/.  The process itself cannot escape this via
    filesystem calls alone — we must ask the Security framework for the original
    location.  Returns None if the bundle is not translocated or the call fails.
    """
    try:
        lib_cf = ctypes.cdll.LoadLibrary(
            ctypes.util.find_library("CoreFoundation") or "CoreFoundation"
        )
        lib_sec = ctypes.cdll.LoadLibrary(
            ctypes.util.find_library("Security") or "Security"
        )

        # ── CoreFoundation helpers ──────────────────────────────────────────
        lib_cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        lib_cf.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32
        ]
        lib_cf.CFURLCreateWithFileSystemPath.restype = ctypes.c_void_p
        lib_cf.CFURLCreateWithFileSystemPath.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_bool
        ]
        lib_cf.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
        lib_cf.CFURLGetFileSystemRepresentation.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.c_char_p, ctypes.c_long
        ]
        lib_cf.CFRelease.restype = None
        lib_cf.CFRelease.argtypes = [ctypes.c_void_p]

        # ── Security helpers ────────────────────────────────────────────────
        lib_sec.SecTranslocateIsTranslocatedURL.restype = ctypes.c_bool
        lib_sec.SecTranslocateIsTranslocatedURL.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_bool),
            ctypes.c_void_p,
        ]
        lib_sec.SecTranslocateCreateOriginalPathForURL.restype = ctypes.c_void_p
        lib_sec.SecTranslocateCreateOriginalPathForURL.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p
        ]

        kCFStringEncodingUTF8 = 0x08000100
        kCFURLPOSIXPathStyle = 0

        cf_str = lib_cf.CFStringCreateWithCString(
            None, str(app_bundle).encode("utf-8"), kCFStringEncodingUTF8
        )
        if not cf_str:
            return None

        url = lib_cf.CFURLCreateWithFileSystemPath(
            None, cf_str, kCFURLPOSIXPathStyle, True
        )
        lib_cf.CFRelease(cf_str)
        if not url:
            return None

        is_translocated = ctypes.c_bool(False)
        lib_sec.SecTranslocateIsTranslocatedURL(
            url, ctypes.byref(is_translocated), None
        )

        if not is_translocated.value:
            lib_cf.CFRelease(url)
            return None  # not translocated — caller uses normal path

        orig_url = lib_sec.SecTranslocateCreateOriginalPathForURL(url, None)
        lib_cf.CFRelease(url)
        if not orig_url:
            return None

        buf = ctypes.create_string_buffer(4096)
        ok = lib_cf.CFURLGetFileSystemRepresentation(orig_url, True, buf, len(buf))
        lib_cf.CFRelease(orig_url)

        if ok:
            return Path(buf.value.decode("utf-8"))
        return None
    except Exception:
        return None


def portable_base_dir() -> Path:
    """Directory next to the packaged executable / app bundle. In development: repo root."""
    if getattr(sys, "frozen", False):
        exe = _best_exe_path()

        if sys.platform == "darwin":
            # Walk up from the binary to find the .app bundle.
            p = exe
            while p != p.parent:
                if p.suffix == ".app":
                    parent = p.parent
                    if str(parent).startswith("/private/var/folders/"):
                        # macOS App Translocation is active — the OS is running
                        # the app from a random read-only mirror.  Ask the
                        # Security framework for the real pre-translocation path
                        # so portable files land next to the actual .app.
                        real = _macos_detranslocate(p)
                        if real is not None:
                            return real.parent
                        # De-translocation failed: return whatever path we have.
                        # The caller's error handling will surface the write failure.
                    return parent
                p = p.parent

        return exe.parent

    # Running from source: repository root (parent of src/)
    return Path(__file__).resolve().parents[3]


def recordings_dir() -> Path:
    """Fixed folder for recordings: `<portable_base>/helvox/`."""
    return portable_base_dir() / "helvox"


def default_recordings_dir() -> Path:
    """Deprecated name; use recordings_dir(). Kept for compatibility."""
    return recordings_dir()
