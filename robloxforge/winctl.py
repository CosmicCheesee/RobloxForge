"""Windows control of the Roblox Studio window: find it, bring it to the front, and send real relative
mouse motion (for mouse-look in a locked-mouse first-person game). Every input refuses to fire unless
Studio is the foreground window, so nothing ever lands in another application."""
from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes as wt

if os.name != "nt":  # pragma: no cover
    raise ImportError("winctl is Windows-only")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
# physical pixels everywhere, so cursor positions agree with Roblox's viewport pixels on scaled displays
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:  # pragma: no cover
    pass

STUDIO_EXE = "robloxstudiobeta.exe"
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetForegroundWindow.restype = wt.HWND
kernel32.OpenProcess.restype = wt.HANDLE


def _exe_of(hwnd) -> str:
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value).lower()
        return ""
    finally:
        kernel32.CloseHandle(h)


def _title(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def studio_windows():
    found = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0 and _exe_of(hwnd) == STUDIO_EXE:
            l, t, r, b = _rect(hwnd)
            found.append((hwnd, _title(hwnd), (r - l) * (b - t), (l, t, r, b)))
        return True
    user32.EnumWindows(EnumProc(cb), 0)
    found.sort(key=lambda f: -f[2])
    return found


def main_window():
    ws = studio_windows()
    return ws[0] if ws else None


def is_foreground() -> bool:
    fg = user32.GetForegroundWindow()
    return bool(fg) and _exe_of(fg) == STUDIO_EXE


def status():
    w = main_window()
    if not w:
        return {"studio": "not running"}
    hwnd, title, _, rect = w
    return {"title": title, "foreground": is_foreground(), "minimized": bool(user32.IsIconic(hwnd)), "rect": rect}


def focus() -> dict:
    w = main_window()
    if not w:
        return {"ok": False, "error": "Roblox Studio is not running"}
    hwnd = w[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    fg = user32.GetForegroundWindow()
    me = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    tgt_tid = user32.GetWindowThreadProcessId(hwnd, None)
    # Windows only lets the process that received the last input steal focus; an Alt tap makes that us.
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    attached = []
    for tid in {fg_tid, tgt_tid} - {0, me}:
        if user32.AttachThreadInput(me, tid, True):
            attached.append(tid)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        for tid in attached:
            user32.AttachThreadInput(me, tid, False)
    for _ in range(20):
        if is_foreground():
            break
        time.sleep(0.05)
    return {"ok": is_foreground(), **status()}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("mi", MOUSEINPUT)]  # MOUSEINPUT is the largest union member: 40 bytes on x64


MOUSEEVENTF_MOVE, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0001, 0x0008, 0x0010


def _send(dx=0, dy=0, flags=MOUSEEVENTF_MOVE):
    inp = INPUT(type=0, mi=MOUSEINPUT(dx=int(dx), dy=int(dy), mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0))
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def mouse_move(dx: float, dy: float, step=30, delay=0.008):
    """Relative mouse motion in small steps (one big jump can be clamped or dropped by the game)."""
    if not is_foreground():
        raise RuntimeError("Studio is not the foreground window -- refusing to move the real mouse (call play_focus)")
    n = max(1, int(max(abs(dx), abs(dy)) // step) + 1)
    sx, sy = dx / n, dy / n
    ax = ay = 0.0
    for _ in range(n):
        ax += sx
        ay += sy
        ix, iy = int(round(ax)), int(round(ay))
        if ix or iy:
            _send(ix, iy)
            ax -= ix
            ay -= iy
        time.sleep(delay)


def right_button(down: bool):
    if not is_foreground():
        raise RuntimeError("Studio is not the foreground window")
    _send(0, 0, MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP)


MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP = 0x0020, 0x0040


def cursor():
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor(x, y):
    if not is_foreground():
        raise RuntimeError("Studio is not the foreground window")
    user32.SetCursorPos(int(x), int(y))


def middle_click(x, y):
    """A real middle click, which the Backroom game binds to nothing: it only gives the game viewport OS
    focus, which is what engages first-person mouse lock in a Studio playtest."""
    set_cursor(x, y)
    time.sleep(0.05)
    _send(0, 0, MOUSEEVENTF_MIDDLEDOWN)
    time.sleep(0.05)
    _send(0, 0, MOUSEEVENTF_MIDDLEUP)
