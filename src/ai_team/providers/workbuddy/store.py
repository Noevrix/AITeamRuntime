"""Application-owned DPAPI store. Never discovers or reads WorkBuddy client files."""
import ctypes
import json
import os
import tempfile
from pathlib import Path
from .client import WorkBuddyError


def dpapi(data, decrypt=False):
    if os.name != "nt":
        raise WorkBuddyError("STORAGE_ERROR")

    class Blob(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.c_void_p)]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.c_void_p))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    function.restype = ctypes.c_int
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise WorkBuddyError("STORAGE_ERROR")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        if decrypt:
            ctypes.memset(target.data, 0, target.size)
        kernel.LocalFree(target.data)
        ctypes.memset(buffer, 0, len(data))


class SecureStore:
    def __init__(self, root=None):
        if root is None:
            local = os.environ.get("LOCALAPPDATA")
            if not local:
                raise WorkBuddyError("STORAGE_ERROR")
            root = Path(local) / "AITeamRuntime" / "workbuddy-oauth"
        self.root = Path(root)

    def _path(self, name):
        if name not in {"token", "pending"}:
            raise WorkBuddyError("STORAGE_ERROR")
        return self.root / (name + ".dpapi")

    def exists(self, name):
        return self._path(name).is_file()

    def save(self, name, value):
        # Encrypt before any filesystem write; temporary files also contain ciphertext.
        encrypted = dpapi(json.dumps(value).encode())
        self.root.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix=".write-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(name))
        except OSError:
            raise WorkBuddyError("STORAGE_ERROR") from None
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load(self, name):
        try:
            path = self._path(name)
            if path.stat().st_size > 64_000:
                raise WorkBuddyError("STORAGE_ERROR")
            value = json.loads(dpapi(path.read_bytes(), decrypt=True))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (OSError, ValueError, UnicodeError):
            raise WorkBuddyError("STORAGE_ERROR") from None

    def delete(self, name):
        self._path(name).unlink(missing_ok=True)
