"""Set a file's created/modified/accessed times. "Created" exists only on Windows."""

import os
import sys


def set_file_times(path, when):
    """Set all file times to `when`, a naive datetime in this machine's local time zone."""
    ts = when.timestamp()
    os.utime(path, (ts, ts))
    if sys.platform == "win32":
        _set_creation_time(path, ts)


def _set_creation_time(path, ts):
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    filetime_p = ctypes.POINTER(wintypes.FILETIME)
    kernel32.SetFileTime.argtypes = [wintypes.HANDLE, filetime_p, filetime_p, filetime_p]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    FILE_WRITE_ATTRIBUTES = 0x100
    SHARE_ALL = 0x1 | 0x2 | 0x4
    OPEN_EXISTING = 3
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    # FILETIME counts 100 ns ticks since 1601-01-01 UTC.
    ticks = round(ts * 10_000_000) + 116_444_736_000_000_000
    created = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)

    handle = kernel32.CreateFileW(str(path), FILE_WRITE_ATTRIBUTES, SHARE_ALL, None, OPEN_EXISTING, 0, None)
    if handle in (None, INVALID_HANDLE_VALUE):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel32.SetFileTime(handle, ctypes.byref(created), None, None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)
