import ctypes
from ctypes import wintypes
import asyncio
import http.server
import os
import queue
import socketserver
import sys
import threading
import time
import urllib.parse
import winreg
import json
import traceback
from tray_popup import open_tray_menu

import screen_brightness_control as sbc
from PIL import Image, ImageDraw, ImageGrab
import pystray
import win32api
import win32con
import win32gui
import win32process

WINRT_IMPORT_ERROR = ""
try:
    import winrt.windows.foundation
    import winrt.windows.foundation.collections
    import winrt.windows.storage.streams
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaSessionManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as MediaPlaybackStatus,
    )
except Exception as import_error:
    WINRT_IMPORT_ERROR = "".join(traceback.format_exception_only(type(import_error), import_error)).strip()
    MediaSessionManager = None
    MediaPlaybackStatus = None


APP_NAME = "ControleBrilhoGlobal"
APP_TITLE = "Controle de Brilho"
SILENT = True
DEFAULT_BRIGHTNESS_LEVELS = [100, 0]
BRIGHTNESS_LEVELS = DEFAULT_BRIGHTNESS_LEVELS.copy()
TRAY_BRIGHTNESS_LEVELS = [100, 90, 80, 70, 60, 50, 40, 30, 25, 20, 15, 10, 5, 3, 1, 0]
SELECTED_MONITOR_KEYS = []
extra_dim_levels = {}
extra_dim_windows = {}
extra_dim_suspended = False
DEFAULT_BRIGHTNESS_HOTKEY = ["f1"]
DEFAULT_PIP_HOTKEY = ["f2"]
DEFAULT_GHOST_HOTKEY = ["f3"]
DEFAULT_APP_GHOST_HOTKEY = ["f4"]
DEFAULT_LEFT_CLICK_HOTKEY = []
DEFAULT_RIGHT_CLICK_HOTKEY = []
DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY = ["f5"]
DEFAULT_PIP_OPACITY = 100
DEFAULT_APP_GHOST_OPACITY = 70
PIP_OPACITY_LEVELS = [100, 90, 80, 70, 60, 50, 40, 30, 20, 15, 10, 5, 2, 1]
APP_GHOST_OPACITY_LEVELS = [100, 90, 80, 70, 60, 50, 40, 30, 20, 15, 10, 5, 2, 1]
PIP_VISIBLE_STRIP = 2
PIP_EXTENSION_PORT = 17963
PIP_EXTENSION_SEEN_SECONDS = 10
PIP_EXTENSION_WAIT_SECONDS = 0.7
PIP_EXTENSION_COMMAND_TTL_SECONDS = 3.0
PIP_EXTENSION_LONG_POLL_SECONDS = 20
HOTKEY_COOLDOWN_SECONDS = 0.7
PIP_ACTION_COOLDOWN_SECONDS = 1.6
BRIGHTNESS_READ_CACHE_SECONDS = 0.6
BRIGHTNESS_SAME_TOLERANCE = 2
DISPLAY_CACHE_SECONDS = 3
MODIFIER_KEY_NAMES = {
    "alt_l": "alt",
    "alt_r": "alt",
    "control_l": "ctrl",
    "control_r": "ctrl",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "shift_l": "shift",
    "shift_r": "shift",
    "super_l": "windows",
    "super_r": "windows",
    "win_l": "windows",
    "win_r": "windows",
}
KEY_NAME_ALIASES = {
    "altgr": "alt gr",
    "right alt": "alt gr",
    "rmenu": "alt gr",
    "escape": "esc",
    "return": "enter",
    "prior": "page up",
    "next": "page down",
    "minus": "minus",
    "plus": "plus",
    "period": "period",
    "comma": ",",
    "slash": "/",
    "backslash": "\\",
    "space": "space",
    "pgup": "page up",
    "pgdn": "page down",
    "apps": "menu",
    "context menu": "menu",
}
MODIFIER_ORDER = ["ctrl", "alt", "shift", "windows"]
MODIFIER_FLAGS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "windows": 0x0008,
}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_APPCOMMAND = 0x0319
WM_REFRESH_HOTKEYS = 0x8001
WM_STOP_HOTKEYS = 0x8002
APPCOMMAND_MEDIA_PLAY = 46
APPCOMMAND_MEDIA_PAUSE = 47
APPCOMMAND_MEDIA_PLAY_PAUSE = 14
LWA_ALPHA = 0x00000002
BROWSER_MEDIA_SOURCE_TOKENS = (
    "edge",
    "msedge",
    "chrome",
    "chromium",
    "brave",
    "vivaldi",
    "opera",
    "firefox",
)
HOTKEY_BRIGHTNESS_ID = 1
HOTKEY_PIP_ID = 2
HOTKEY_GHOST_ID = 3
HOTKEY_APP_GHOST_ID = 4
HOTKEY_LEFT_CLICK_ID = 5
HOTKEY_RIGHT_CLICK_ID = 6
HOTKEY_MOUSE_KEYS_TOGGLE_ID = 7
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
MAPVK_VK_TO_VSC = 0
EXTENDED_KEY_VKS = {
    0x21,
    0x22,
    0x23,
    0x24,
    0x25,
    0x26,
    0x27,
    0x28,
    0x2D,
    0x2E,
    0x5B,
    0x5C,
    0x6F,
    0x90,
    0x91,
}
IGNORED_CAPTURE_VKS = {
    0x01,
    0x02,
    0x03,
    0x04,
    0x05,
    0x06,
    0x07,
    0x0A,
    0x0B,
    0x0E,
    0x0F,
    0x10,
    0x11,
    0x12,
    0x15,
    0x16,
    0x1A,
    0x1B,
    0x1C,
    0x1D,
    0x1E,
    0x1F,
    0x3A,
    0x3B,
    0x3C,
    0x3D,
    0x3E,
    0x3F,
    0x40,
    0x88,
    0x89,
    0x8A,
    0x8B,
    0x8C,
    0x8D,
    0x8E,
    0x8F,
    0x92,
    0x93,
    0x94,
    0x95,
    0x96,
    0x97,
    0xE8,
    0xA0,
    0xA1,
    0xA2,
    0xA3,
    0xA4,
    0xA5,
    0x5B,
    0x5C,
    0x5E,
    0xB8,
    0xB9,
    0xC1,
    0xC2,
    0xC3,
    0xC4,
    0xC5,
    0xC6,
    0xC7,
    0xC8,
    0xC9,
    0xCA,
    0xCB,
    0xCC,
    0xCD,
    0xCE,
    0xCF,
    0xD0,
    0xD1,
    0xD2,
    0xD3,
    0xD4,
    0xD5,
    0xD6,
    0xD7,
    0xE0,
    0xE9,
    0xEA,
    0xEB,
    0xEC,
    0xED,
    0xEE,
    0xEF,
    0xF6,
    0xF7,
    0xF8,
    0xF9,
    0xFA,
    0xFB,
    0xFC,
    0xFD,
    0xFE,
    0xFF,
}
MOUSE_CAPTURE_VKS = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06}
VIRTUAL_KEYS = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "space": 0x20,
    "page up": 0x21,
    "page down": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
    "num0": 0x60,
    "num1": 0x61,
    "num2": 0x62,
    "num3": 0x63,
    "num4": 0x64,
    "num5": 0x65,
    "num6": 0x66,
    "num7": 0x67,
    "num8": 0x68,
    "num9": 0x69,
    "num multiply": 0x6A,
    "num plus": 0x6B,
    "num minus": 0x6D,
    "num decimal": 0x6E,
    "num divide": 0x6F,
    "print screen": 0x2C,
    "caps lock": 0x14,
    "scroll lock": 0x91,
    "pause": 0x13,
    "media previous": 0xB1,
    "media next": 0xB0,
    "media play pause": 0xB3,
    "volume mute": 0xAD,
    "volume down": 0xAE,
    "volume up": 0xAF,
    "ctrl": 0x11,
    "left ctrl": 0xA2,
    "right ctrl": 0xA3,
    "alt": 0x12,
    "left alt": 0xA4,
    "alt gr": 0xA5,
    "shift": 0x10,
    "left shift": 0xA0,
    "right shift": 0xA1,
    "windows": 0x5B,
    "left windows": 0x5B,
    "right windows": 0x5C,
    "browser back": 0xA6,
    "browser forward": 0xA7,
    "browser refresh": 0xA8,
    "browser stop": 0xA9,
    "browser search": 0xAA,
    "browser favorites": 0xAB,
    "browser home": 0xAC,
    "launch mail": 0xB4,
    "launch media": 0xB5,
    "launch app1": 0xB6,
    "launch app2": 0xB7,
    "menu": 0x5D,
    "minus": 0xBD,
    "-": 0xBD,
    "plus": 0xBB,
    "+": 0xBB,
    "period": 0xBE,
    ".": 0xBE,
    ",": 0xBC,
    "/": 0xBF,
    "\\": 0xDC,
}
MODIFIER_CAPTURE_KEYS = [
    (0xA5, "alt gr"),
    (0xA3, "right ctrl"),
    (0xA2, "left ctrl"),
    (0xA4, "left alt"),
    (0xA1, "right shift"),
    (0xA0, "left shift"),
    (0x5C, "right windows"),
    (0x5B, "left windows"),
    (0x11, "ctrl"),
    (0x12, "alt"),
    (0x10, "shift"),
]
brightness_hotkey = DEFAULT_BRIGHTNESS_HOTKEY.copy()
pip_hotkey = DEFAULT_PIP_HOTKEY.copy()
ghost_hotkey = DEFAULT_GHOST_HOTKEY.copy()
app_ghost_hotkey = DEFAULT_APP_GHOST_HOTKEY.copy()
left_click_hotkey = DEFAULT_LEFT_CLICK_HOTKEY.copy()
right_click_hotkey = DEFAULT_RIGHT_CLICK_HOTKEY.copy()
mouse_keys_enabled = False
mouse_keys_toggle_hotkey = DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY.copy()
pip_opacity = DEFAULT_PIP_OPACITY
app_ghost_opacity = DEFAULT_APP_GHOST_OPACITY
pip_ghost = False
pip_ghost_windows = {}
pip_ghost_lock = threading.RLock()
app_ghost_enabled = False
app_ghost_target_key = ""
app_ghost_target_label = ""
app_ghost_click_through = False
app_ghost_windows = {}
app_ghost_lock = threading.RLock()


def sync_pip_ghost():
    with pip_ghost_lock:
        pip_windows = set()
        def collect(hwnd, _):
            title = win32gui.GetWindowText(hwnd).strip().lower()
            if title in ("picture-in-picture", "picture in picture") and is_strong_pip_window(hwnd, include_hidden=True):
                pip_windows.add(hwnd)
        win32gui.EnumWindows(collect, None)
        candidates = pip_windows if pip_ghost and not stop_event.is_set() else set()
        for hwnd in list(pip_ghost_windows):
            pid, originally_transparent = pip_ghost_windows[hwnd]
            if not win32gui.IsWindow(hwnd) or window_process_id(hwnd) != pid:
                pip_ghost_windows.pop(hwnd, None)
                continue
            if hwnd not in candidates:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if not originally_transparent:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style & ~win32con.WS_EX_TRANSPARENT)
                pip_ghost_windows.pop(hwnd, None)
        if not pip_ghost:
            for hwnd in pip_windows:
                try:
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    if style & win32con.WS_EX_TRANSPARENT:
                        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style & ~win32con.WS_EX_TRANSPARENT)
                        log_event(f"pip ghost cleared hwnd={hwnd}")
                except Exception:
                    log_event("pip ghost clear failed:\n" + traceback.format_exc())
            return
        for hwnd in candidates:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if hwnd not in pip_ghost_windows:
                pip_ghost_windows[hwnd] = (window_process_id(hwnd), bool(style & win32con.WS_EX_TRANSPARENT))
                apply_pip_opacity(hwnd)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)


def set_pip_ghost(enabled):
    global pip_ghost
    pip_ghost = bool(enabled)
    save_config()
    sync_pip_ghost()
    if tray_icon:
        tray_icon.update_menu()


def toggle_pip_ghost():
    set_pip_ghost(not pip_ghost)
    log_event(f"pip ghost toggled enabled={pip_ghost}")


def run_pip_ghost_watcher():
    while not stop_event.wait(0.4):
        try:
            sync_pip_ghost()
            sync_app_ghost()
        except Exception:
            log_event("pip ghost failed:\n" + traceback.format_exc())


def process_path(process_id):
    if not process_id:
        return ""

    handle = None
    try:
        query_limited_information = 0x1000
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(query_limited_information, False, int(process_id))
        if not handle:
            return ""

        buffer = ctypes.create_unicode_buffer(4096)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value
    except Exception:
        return ""
    finally:
        if handle:
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass


def app_window_candidate(hwnd):
    try:
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            return None

        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return None

        class_name = win32gui.GetClassName(hwnd)
        if class_name in {"Progman", "WorkerW", "Shell_TrayWnd", "DV2ControlHost"}:
            return None

        if is_strong_pip_window(hwnd, include_hidden=True):
            return None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width < 120 or height < 90:
            return None

        process_id = window_process_id(hwnd)
        path = process_path(process_id)
        own_path = app_path().lower()
        if path and os.path.abspath(path).lower() == own_path:
            return None

        key = f"path:{path.lower()}" if path else f"pid:{process_id}"
        name = os.path.splitext(os.path.basename(path))[0] if path else class_name
        label = f"{name} - {title}" if name and title else title or name
        if len(label) > 72:
            label = label[:69] + "..."

        return {
            "hwnd": hwnd,
            "key": key,
            "label": label,
            "title": title,
            "class_name": class_name,
            "process_id": process_id,
            "path": path,
        }
    except Exception:
        return None


def open_app_targets():
    targets = {}

    def collect(hwnd, _extra):
        info = app_window_candidate(hwnd)
        if not info:
            return

        current = targets.get(info["key"])
        if current is None or len(info["title"]) > len(current["title"]):
            targets[info["key"]] = info

    win32gui.EnumWindows(collect, None)
    return sorted(targets.values(), key=lambda item: item["label"].lower())


def selected_app_ghost_windows():
    if not app_ghost_target_key:
        return set()

    windows = set()

    def collect(hwnd, _extra):
        info = app_window_candidate(hwnd)
        if info and info["key"] == app_ghost_target_key:
            windows.add(hwnd)

    win32gui.EnumWindows(collect, None)
    return windows


def sync_app_ghost():
    with app_ghost_lock:
        candidates = selected_app_ghost_windows() if app_ghost_enabled and not stop_event.is_set() else set()

        for hwnd in list(app_ghost_windows):
            (
                process_id,
                originally_transparent,
                originally_topmost,
                originally_layered,
                original_layered_ok,
                original_color_key,
                original_alpha,
                original_layered_flags,
                _last_applied_alpha,
            ) = app_ghost_windows[hwnd]
            if not win32gui.IsWindow(hwnd) or window_process_id(hwnd) != process_id or hwnd not in candidates:
                try:
                    if win32gui.IsWindow(hwnd):
                        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                        restored_style = style
                        if not originally_transparent:
                            restored_style &= ~win32con.WS_EX_TRANSPARENT
                        if not originally_layered:
                            restored_style &= ~win32con.WS_EX_LAYERED
                        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, restored_style)
                        if originally_layered and original_layered_ok:
                            win32gui.SetLayeredWindowAttributes(
                                hwnd,
                                original_color_key,
                                original_alpha,
                                original_layered_flags,
                            )
                        if not originally_topmost:
                            win32gui.SetWindowPos(
                                hwnd,
                                win32con.HWND_NOTOPMOST,
                                0,
                                0,
                                0,
                                0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                            )
                except Exception:
                    log_event("app ghost clear failed:\n" + traceback.format_exc())
                app_ghost_windows.pop(hwnd, None)

        for hwnd in candidates:
            try:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                alpha = max(1, min(255, round(clamp_pip_opacity(app_ghost_opacity) * 255 / 100)))
                desired_transparent = app_ghost_click_through
                if hwnd not in app_ghost_windows:
                    layered_ok, color_key, alpha_value, layered_flags = layered_window_attributes(hwnd)
                    app_ghost_windows[hwnd] = (
                        window_process_id(hwnd),
                        bool(style & win32con.WS_EX_TRANSPARENT),
                        bool(style & win32con.WS_EX_TOPMOST),
                        bool(style & win32con.WS_EX_LAYERED),
                        layered_ok,
                        color_key,
                        alpha_value,
                        layered_flags,
                        None,
                    )
                current_state = app_ghost_windows[hwnd]
                last_alpha = current_state[-1]
                needs_style = not (
                    (style & win32con.WS_EX_LAYERED)
                    and (style & win32con.WS_EX_TOPMOST)
                    and bool(style & win32con.WS_EX_TRANSPARENT) == desired_transparent
                )
                if last_alpha == alpha and not needs_style:
                    continue

                new_style = style | win32con.WS_EX_LAYERED
                if desired_transparent:
                    new_style |= win32con.WS_EX_TRANSPARENT
                else:
                    new_style &= ~win32con.WS_EX_TRANSPARENT
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
                win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW,
                )
                app_ghost_windows[hwnd] = current_state[:-1] + (alpha,)
            except Exception:
                log_event("app ghost apply failed:\n" + traceback.format_exc())


def set_app_ghost_target(key, label):
    global app_ghost_enabled, app_ghost_target_key, app_ghost_target_label

    if app_ghost_enabled:
        sync_app_ghost()
    app_ghost_target_key = str(key or "")
    app_ghost_target_label = str(label or "")
    if not app_ghost_target_key:
        app_ghost_enabled = False
    save_config()
    sync_app_ghost()
    if tray_icon:
        tray_icon.update_menu()


def set_app_ghost_target_and_enable(key, label):
    global app_ghost_enabled, app_ghost_target_key, app_ghost_target_label

    if app_ghost_enabled:
        sync_app_ghost()
    app_ghost_target_key = str(key or "")
    app_ghost_target_label = str(label or "")
    app_ghost_enabled = bool(app_ghost_target_key)
    save_config()
    sync_app_ghost()
    if tray_icon:
        tray_icon.update_menu()
    log_event(f"app ghost target enabled={app_ghost_enabled} target={app_ghost_target_label!r}")


def set_app_ghost_enabled(enabled):
    global app_ghost_enabled

    app_ghost_enabled = bool(enabled) and bool(app_ghost_target_key)
    save_config()
    sync_app_ghost()
    if tray_icon:
        tray_icon.update_menu()
    log_event(f"app ghost enabled={app_ghost_enabled} target={app_ghost_target_label!r}")


def set_app_ghost_opacity(value):
    global app_ghost_opacity

    app_ghost_opacity = clamp_pip_opacity(value)
    save_config()
    sync_app_ghost()
    if tray_icon:
        tray_icon.update_menu()
    log_event(f"app ghost opacity set to {app_ghost_opacity}")


def set_app_ghost_click_through(enabled):
    global app_ghost_click_through

    app_ghost_click_through = bool(enabled)
    save_config()
    sync_app_ghost()
    if tray_icon:
        tray_icon.update_menu()
    log_event(f"app ghost click_through={app_ghost_click_through}")


def toggle_app_ghost_click_mode():
    set_app_ghost_click_through(not app_ghost_click_through)


def next_opacity_value(current, levels):
    ordered = list(levels)
    if current not in ordered:
        return ordered[0]
    index = ordered.index(current)
    return ordered[(index + 1) % len(ordered)]


def cycle_pip_opacity():
    set_pip_opacity(next_opacity_value(pip_opacity, PIP_OPACITY_LEVELS))


def cycle_app_ghost_opacity():
    set_app_ghost_opacity(next_opacity_value(app_ghost_opacity, APP_GHOST_OPACITY_LEVELS))


def toggle_app_ghost():
    if not app_ghost_target_key:
        log_event("app ghost toggle skipped: no target")
        return
    set_app_ghost_enabled(not app_ghost_enabled)

last_brightness = None
last_brightness_read = {
    "value": None,
    "time": 0,
}
cycle_index = -1
brightness_lock = threading.Lock()
cycle_lock = threading.Lock()
brightness_queue = queue.Queue(maxsize=1)
cached_displays = []
cached_displays_time = 0
stop_event = threading.Event()
tray_icon = None
ui_root = None
settings_window = None
hotkey_thread = None
hotkey_thread_id = None
monitor_thread = None
pip_hover_thread = None
hotkeys_suspended = False
single_instance_mutex = None
pip_lock = threading.Lock()
pip_last_action_time = 0
pip_hover_active = False
pip_hover_last_scan = 0
pip_opacity_cache = {}
hotkey_active = {
    HOTKEY_BRIGHTNESS_ID: False,
    HOTKEY_PIP_ID: False,
    HOTKEY_GHOST_ID: False,
    HOTKEY_APP_GHOST_ID: False,
    HOTKEY_LEFT_CLICK_ID: False,
    HOTKEY_RIGHT_CLICK_ID: False,
    HOTKEY_MOUSE_KEYS_TOGGLE_ID: False,
}
hotkey_last_fire = {
    HOTKEY_BRIGHTNESS_ID: 0,
    HOTKEY_PIP_ID: 0,
    HOTKEY_GHOST_ID: 0,
    HOTKEY_APP_GHOST_ID: 0,
    HOTKEY_LEFT_CLICK_ID: 0,
    HOTKEY_RIGHT_CLICK_ID: 0,
    HOTKEY_MOUSE_KEYS_TOGGLE_ID: 0,
}
hotkey_release_since = {
    HOTKEY_BRIGHTNESS_ID: 0,
    HOTKEY_PIP_ID: 0,
    HOTKEY_GHOST_ID: 0,
    HOTKEY_APP_GHOST_ID: 0,
    HOTKEY_LEFT_CLICK_ID: 0,
    HOTKEY_RIGHT_CLICK_ID: 0,
    HOTKEY_MOUSE_KEYS_TOGGLE_ID: 0,
}
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class InputData(ctypes.Union):
    _fields_ = [("mi", MouseInput)]


class WindowsInput(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", InputData)]


send_input = ctypes.WinDLL("user32", use_last_error=True).SendInput
send_input.argtypes = [wintypes.UINT, ctypes.POINTER(WindowsInput), ctypes.c_int]
send_input.restype = wintypes.UINT
KEY_NAME_TO_VK = {}
pip_state = {
    "hidden": False,
    "hwnd": None,
    "rect": None,
    "last_rect": None,
    "hidden_at": 0,
    "paused_by_app": False,
    "pause_method": None,
    "last_action": 0,
}
pip_extension_lock = threading.Lock()
pip_extension_command = {
    "seq": 0,
    "action": "idle",
    "created_at": 0,
}
pip_extension_results = {}
pip_extension_last_seen = 0


def install_exception_logging():
    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args):
            log_event(
                f"thread error name={getattr(args.thread, 'name', '')}:\n"
                + "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            )

        threading.excepthook = _thread_excepthook


def app_data_dir():
    base = os.getenv("APPDATA") or os.path.dirname(app_path())
    folder = os.path.join(base, APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return folder


def log_event(message):
    try:
        with open(os.path.join(app_data_dir(), "controle_brilho.log"), "a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def layered_window_attributes(hwnd):
    color_key = wintypes.DWORD(0)
    alpha = ctypes.c_ubyte(255)
    flags = wintypes.DWORD(0)
    try:
        user32.GetLayeredWindowAttributes.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetLayeredWindowAttributes.restype = wintypes.BOOL
        ok = bool(
            user32.GetLayeredWindowAttributes(
                hwnd,
                ctypes.byref(color_key),
                ctypes.byref(alpha),
                ctypes.byref(flags),
            )
        )
        return ok, int(color_key.value), int(alpha.value), int(flags.value)
    except Exception:
        return False, 0, 255, 0


class PipExtensionHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global pip_extension_last_seen

        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path != "/pip-command":
            self.send_error(404)
            return

        query = urllib.parse.parse_qs(parsed_path.query)
        try:
            last_seq = int((query.get("last") or [""])[0])
        except (TypeError, ValueError):
            last_seq = None

        if last_seq is not None:
            deadline = time.monotonic() + PIP_EXTENSION_LONG_POLL_SECONDS
            while time.monotonic() < deadline:
                with pip_extension_lock:
                    current_seq = int(pip_extension_command.get("seq") or 0)
                if current_seq != last_seq:
                    break
                time.sleep(0.01)

        pip_extension_last_seen = time.monotonic()
        with pip_extension_lock:
            payload = dict(pip_extension_command)

        # Never replay a command left behind by a disconnected/restarted extension.
        # Only a command issued moments ago is allowed to affect media playback.
        created_at = float(payload.get("created_at") or 0)
        if (
            payload.get("action") in ("pause", "play")
            and (time.time() - created_at) > PIP_EXTENSION_COMMAND_TTL_SECONDS
        ):
            payload["action"] = "idle"

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global pip_extension_last_seen

        if not self.path.startswith("/pip-result"):
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))
            seq = int(payload.get("seq") or 0)
            pip_extension_last_seen = time.monotonic()
            if seq:
                with pip_extension_lock:
                    previous = pip_extension_results.get(seq) or {}
                    pip_extension_results[seq] = {
                        "ok": bool(payload.get("ok")) or bool(previous.get("ok")),
                        "action": str(payload.get("action") or ""),
                        "seen": int(previous.get("seen") or 0) + int(payload.get("seen") or 0),
                        "changed": int(previous.get("changed") or 0) + int(payload.get("changed") or 0),
                        "created_at": time.monotonic(),
                    }
                log_event(f"pip extension result seq={seq} payload={payload}")

            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            log_event("pip extension result failed:\n" + traceback.format_exc())
            self.send_error(400)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, _format, *_args):
        return


class ThreadingLocalServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_pip_extension_server():
    def run_server():
        try:
            server = ThreadingLocalServer(("127.0.0.1", PIP_EXTENSION_PORT), PipExtensionHandler)
            log_event(f"pip extension server started port={PIP_EXTENSION_PORT}")
            server.serve_forever()
        except Exception:
            log_event("pip extension server failed:\n" + traceback.format_exc())

    threading.Thread(target=run_server, name="pip-extension-server", daemon=True).start()


def pip_extension_available():
    return time.monotonic() - pip_extension_last_seen <= PIP_EXTENSION_SEEN_SECONDS


def send_pip_extension_command(action):
    issued_at = time.monotonic()
    with pip_extension_lock:
        pip_extension_command["seq"] += 1
        pip_extension_command["action"] = action
        pip_extension_command["created_at"] = time.time()
        seq = pip_extension_command["seq"]
        pip_extension_results.pop(seq, None)

    log_event(f"pip extension command action={action} seq={seq}")
    deadline = time.monotonic() + PIP_EXTENSION_WAIT_SECONDS
    last_result = None
    while time.monotonic() < deadline:
        with pip_extension_lock:
            result = pip_extension_results.get(seq)
        if result:
            last_result = result
            ok = bool(result.get("ok"))
            seen = int(result.get("seen") or 0)
            changed = int(result.get("changed") or 0)
            if ok and changed > 0:
                return True
        time.sleep(0.05)

    if last_result:
        log_event(
            f"pip extension rejected action={action} seq={seq} "
            f"ok={bool(last_result.get('ok'))} "
            f"seen={int(last_result.get('seen') or 0)} "
            f"changed={int(last_result.get('changed') or 0)}"
        )
        return False

    if pip_extension_last_seen >= issued_at:
        log_event(f"pip extension no ack action={action} seq={seq}: connected without result")
    else:
        log_event(f"pip extension skipped action={action} seq={seq}: not connected")
    return False


def config_path():
    return os.path.join(app_data_dir(), "config.json")


def ensure_single_instance():
    global single_instance_mutex

    mutex_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mutex_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    mutex_kernel32.CreateMutexW.restype = wintypes.HANDLE
    single_instance_mutex = mutex_kernel32.CreateMutexW(None, True, f"Local\\{APP_NAME}_SingleInstance")
    if ctypes.get_last_error() == 183:
        log_event("another instance is already running")
        return False
    return True


def clamp_brightness(value):
    return max(0, min(100, int(value)))


def clamp_pip_opacity(value):
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = DEFAULT_PIP_OPACITY
    return max(1, min(100, numeric))


def apply_pip_opacity(hwnd, opacity=None):
    global pip_opacity_cache

    if not hwnd or not win32gui.IsWindow(hwnd):
        return False

    if not is_strong_pip_window(hwnd, include_hidden=True):
        title, class_name, rect = window_info(hwnd)
        log_event(f"pip opacity skipped non-pip hwnd={hwnd} title={title!r} class={class_name!r} rect={rect}")
        return False

    opacity = clamp_pip_opacity(pip_opacity if opacity is None else opacity)
    alpha = max(1, min(255, round(255 * opacity / 100)))
    try:
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if pip_opacity_cache.get(hwnd) == alpha and (ex_style & win32con.WS_EX_LAYERED):
            return True

        if not (ex_style & win32con.WS_EX_LAYERED):
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
        pip_opacity_cache[hwnd] = alpha
        log_event(f"pip opacity applied hwnd={hwnd} opacity={opacity} alpha={alpha}")
        return True
    except Exception:
        log_event("pip opacity failed:\n" + traceback.format_exc())
        return False


def cursor_inside_window(hwnd):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False

    try:
        point = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            return False
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return left <= point.x < right and top <= point.y < bottom
    except Exception:
        log_event("cursor window check failed:\n" + traceback.format_exc())
        return False


def is_known_hidden_pip(hwnd):
    stored_hwnd = pip_state.get("hwnd")
    return bool(hwnd and stored_hwnd == hwnd and pip_state.get("hidden") and is_hidden_on_side(hwnd))


def is_strong_pip_window(hwnd, include_hidden=False):
    if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
        return False

    title, class_name, rect = window_info(hwnd)
    title_lower = title.lower().strip()
    class_lower = class_name.lower().strip()
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return False

    if title_lower in ("picture-in-picture", "picture in picture"):
        return True

    if include_hidden and is_known_hidden_pip(hwnd):
        return True

    if class_lower != "chrome_widgetwin_1":
        return False

    if title_lower:
        return False

    is_visible = bool(win32gui.IsWindowVisible(hwnd))
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    is_topmost = bool(ex_style & win32con.WS_EX_TOPMOST)
    ratio = width / height if height else 0
    virtual_left, virtual_top, virtual_right, virtual_bottom = get_virtual_screen_rect()
    virtual_width = max(1, virtual_right - virtual_left)
    virtual_height = max(1, virtual_bottom - virtual_top)
    max_width = max(900, int(virtual_width * 0.65))
    max_height = max(650, int(virtual_height * 0.65))

    # Chrome/Edge reuse this class for non-PiP UI. Without a PiP title, require
    # a video-like floating window shape so browser menus never receive opacity.
    return bool(
        is_visible
        and is_topmost
        and 160 <= width <= max_width
        and 90 <= height <= max_height
        and 1.1 <= ratio <= 2.8
    )


def normalize_key_name(keysym):
    key = str(keysym or "").strip().lower()
    if not key:
        return ""

    if key in MODIFIER_KEY_NAMES:
        return MODIFIER_KEY_NAMES[key]
    if key in KEY_NAME_ALIASES:
        return KEY_NAME_ALIASES[key]
    if key.startswith("kp_"):
        key = key[3:]
    if len(key) == 1:
        return key

    return key.replace("_", " ")


def key_name_from_vk(vk):
    modifier_names = {
        0x10: "shift",
        0x11: "ctrl",
        0x12: "alt",
        0x5B: "left windows",
        0x5C: "right windows",
        0xA0: "left shift",
        0xA1: "right shift",
        0xA2: "left ctrl",
        0xA3: "right ctrl",
        0xA4: "left alt",
        0xA5: "alt gr",
    }
    if vk in modifier_names:
        return modifier_names[vk]

    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    if 0x70 <= vk <= 0x87:
        return f"f{vk - 0x70 + 1}"

    for name, mapped_vk in VIRTUAL_KEYS.items():
        if mapped_vk == vk and len(name) > 1:
            return normalize_key_name(name)

    scan_code = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    if not scan_code:
        return f"vk{vk}"

    lparam = scan_code << 16
    if vk in EXTENDED_KEY_VKS:
        lparam |= 1 << 24

    buffer = ctypes.create_unicode_buffer(64)
    if user32.GetKeyNameTextW(lparam, buffer, len(buffer)):
        name = normalize_key_name(buffer.value)
        if name:
            return name

    return f"vk{vk}"


def rebuild_key_name_map():
    KEY_NAME_TO_VK.clear()
    for name, vk in VIRTUAL_KEYS.items():
        KEY_NAME_TO_VK[normalize_key_name(name)] = vk
    for vk in range(1, 256):
        if vk in MOUSE_CAPTURE_VKS:
            continue
        KEY_NAME_TO_VK.setdefault(key_name_from_vk(vk), vk)
        KEY_NAME_TO_VK.setdefault(f"vk{vk}", vk)


def build_hotkey(modifiers, key):
    normalized_key = normalize_key_name(key)
    if not normalized_key:
        return ""
    return normalized_key


def normalize_single_hotkey_key(value):
    key = normalize_key_name(value)
    if not key or not key_to_vk(key):
        return ""
    return key


def split_legacy_hotkey(value):
    if isinstance(value, list):
        return value
    return [part for part in str(value or "").split("+") if part.strip()]


def normalize_hotkey_keys(value, default):
    default_keys = normalize_hotkey_keys(default, []) if default else []
    keys = []

    for part in split_legacy_hotkey(value):
        key = normalize_single_hotkey_key(part)
        if key and key not in keys:
            keys.append(key)
        if len(keys) >= 3:
            break

    return keys or default_keys


def hotkey_label(value):
    keys = normalize_hotkey_keys(value, [])
    labels = []
    for key in keys:
        if key.startswith("vk") and key[2:].isdigit():
            name = key_name_from_vk(int(key[2:]))
            labels.append("Tecla especial" if name.startswith("vk") else name)
        else:
            labels.append(key)
    return " + ".join(labels) if labels else "nenhuma"


def normalize_hotkey(value, default):
    hotkey = str(value or "").strip().lower()
    parts = [normalize_key_name(part) for part in hotkey.split("+") if part.strip()]
    key = None

    if len(parts) == 1 and parts[0] in MODIFIER_FLAGS:
        return parts[0]

    for part in parts:
        if part not in MODIFIER_FLAGS:
            key = part

    if not key or not key_to_vk(key):
        return default

    return key


def key_to_vk(key):
    key = normalize_key_name(key)
    if not key:
        return None
    if key.startswith("vk") and key[2:].isdigit():
        value = int(key[2:])
        if 1 <= value <= 255:
            return value
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    if len(key) == 1:
        mapped = user32.VkKeyScanW(ctypes.c_wchar(key))
        if mapped != -1:
            return mapped & 0xFF
    if key.startswith("f") and key[1:].isdigit():
        number = int(key[1:])
        if 1 <= number <= 24:
            return 0x70 + number - 1
    if not KEY_NAME_TO_VK:
        rebuild_key_name_map()
    return KEY_NAME_TO_VK.get(key) or VIRTUAL_KEYS.get(key)


def parse_hotkey(hotkey):
    parts = [part.strip().lower() for part in str(hotkey or "").split("+") if part.strip()]
    key = None

    for part in parts:
        normalized = normalize_key_name(part)
        if normalized not in MODIFIER_FLAGS:
            key = normalized

    if not key and len(parts) == 1 and parts[0] in MODIFIER_FLAGS:
        key = parts[0]

    vk = key_to_vk(key)
    if not vk:
        return None

    return MOD_NOREPEAT, vk


def parse_hotkey_state(hotkey):
    if isinstance(hotkey, list):
        vks = []
        for key in normalize_hotkey_keys(hotkey, []):
            vk = key_to_vk(key)
            if vk and vk not in vks:
                vks.append(vk)
        return vks if vks else None

    parts = [part.strip().lower() for part in str(hotkey or "").split("+") if part.strip()]
    key = None

    if len(parts) == 1 and parts[0] in MODIFIER_FLAGS:
        vk = key_to_vk(parts[0])
        return [vk] if vk else None

    for part in parts:
        normalized = normalize_key_name(part)
        if normalized not in MODIFIER_FLAGS:
            key = normalized

    vk = key_to_vk(key)
    if not vk:
        return None

    return [vk]


def is_vk_pressed(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def pressed_capture_vks():
    return {vk for vk in range(1, 256) if vk not in MOUSE_CAPTURE_VKS and is_vk_pressed(vk)}


def hotkey_from_vk(vk):
    for modifier_vk, key_name in MODIFIER_CAPTURE_KEYS:
        if modifier_vk == vk:
            return build_hotkey(set(), key_name)

    key_name = key_name_from_vk(vk)
    return build_hotkey(set(), key_name if key_to_vk(key_name) == vk else f"vk{vk}")


def first_new_capture_hotkey(baseline_vks):
    current_vks = pressed_capture_vks()
    new_vks = current_vks - set(baseline_vks or [])
    if not new_vks:
        return "", current_vks

    for modifier_vk, key_name in MODIFIER_CAPTURE_KEYS:
        if modifier_vk in new_vks:
            return build_hotkey(set(), key_name), current_vks

    return hotkey_from_vk(min(new_vks)), current_vks


def any_capture_key_pressed():
    return bool(pressed_capture_vks())


def read_pressed_hotkey():
    hotkey, _current_vks = first_new_capture_hotkey(set())
    return hotkey


def hotkey_from_tk_event(event):
    keycode = int(getattr(event, "keycode", 0) or 0)
    keysym = normalize_key_name(getattr(event, "keysym", "") or "")

    if keycode in {vk for vk, _key_name in MODIFIER_CAPTURE_KEYS}:
        return hotkey_from_vk(keycode)

    if keycode and 1 <= keycode <= 255 and keycode not in MOUSE_CAPTURE_VKS:
        return hotkey_from_vk(keycode)

    if keysym and keysym not in {"??"}:
        if keysym in MODIFIER_FLAGS or key_to_vk(keysym):
            return build_hotkey(set(), keysym)

    return ""


def load_config():
    global pip_ghost, app_ghost_enabled, app_ghost_target_key, app_ghost_target_label, app_ghost_click_through
    global extra_dim_levels, extra_dim_suspended
    global BRIGHTNESS_LEVELS, SELECTED_MONITOR_KEYS, brightness_hotkey, pip_hotkey, ghost_hotkey, app_ghost_hotkey, left_click_hotkey, right_click_hotkey, mouse_keys_enabled, mouse_keys_toggle_hotkey, pip_opacity, app_ghost_opacity

    try:
        with open(config_path(), "r", encoding="utf-8-sig") as file:
            data = json.load(file)
        pip_ghost = data.get("pip_ghost", False) is True
        app_ghost_enabled = data.get("app_ghost_enabled", False) is True
        app_ghost_target_key = str(data.get("app_ghost_target_key") or "")
        app_ghost_target_label = str(data.get("app_ghost_target_label") or "")
        app_ghost_click_through = data.get("app_ghost_click_through", False) is True
        if not app_ghost_target_key:
            app_ghost_enabled = False
        extra_dim_levels = {str(key): max(0, min(95, int(value))) for key, value in data.get("extra_dim_levels", {}).items()}
        extra_dim_suspended = data.get("extra_dim_suspended", False) is True

        levels = data.get("brightness_levels", DEFAULT_BRIGHTNESS_LEVELS)
        if isinstance(levels, list) and len(levels) == 2:
            BRIGHTNESS_LEVELS = [clamp_brightness(levels[0]), clamp_brightness(levels[1])]
        selected_monitors = data.get("selected_monitor_keys", [])
        if isinstance(selected_monitors, list):
            SELECTED_MONITOR_KEYS = [str(key) for key in selected_monitors if str(key)]
        brightness_hotkey = normalize_hotkey_keys(
            data.get("brightness_hotkey"),
            DEFAULT_BRIGHTNESS_HOTKEY,
        )
        pip_hotkey = normalize_hotkey_keys(data.get("pip_hotkey"), DEFAULT_PIP_HOTKEY)
        ghost_hotkey = normalize_hotkey_keys(data.get("ghost_hotkey"), DEFAULT_GHOST_HOTKEY)
        app_ghost_hotkey = normalize_hotkey_keys(data.get("app_ghost_hotkey"), DEFAULT_APP_GHOST_HOTKEY)
        left_click_hotkey = normalize_hotkey_keys(data.get("left_click_hotkey"), DEFAULT_LEFT_CLICK_HOTKEY)
        right_click_hotkey = normalize_hotkey_keys(data.get("right_click_hotkey"), DEFAULT_RIGHT_CLICK_HOTKEY)
        mouse_keys_enabled = data.get("mouse_keys_enabled", False) is True
        mouse_keys_toggle_hotkey = normalize_hotkey_keys(data.get("mouse_keys_toggle_hotkey"), DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY)
        pip_opacity = clamp_pip_opacity(data.get("pip_opacity", DEFAULT_PIP_OPACITY))
        app_ghost_opacity = clamp_pip_opacity(data.get("app_ghost_opacity", DEFAULT_APP_GHOST_OPACITY))
        log_event(
            "config loaded raw "
            f"brightness_hotkey={data.get('brightness_hotkey')!r} "
            f"pip_hotkey={data.get('pip_hotkey')!r} "
            f"ghost_hotkey={data.get('ghost_hotkey')!r} "
            f"app_ghost_hotkey={data.get('app_ghost_hotkey')!r} "
            f"pip_opacity={pip_opacity} "
            f"app_ghost_opacity={app_ghost_opacity} "
            f"selected_monitors={SELECTED_MONITOR_KEYS!r} "
            f"normalized={hotkey_label(brightness_hotkey)!r}/{hotkey_label(pip_hotkey)!r}/{hotkey_label(ghost_hotkey)!r}/{hotkey_label(app_ghost_hotkey)!r}"
        )
    except Exception:
        log_event("load_config fallback:\n" + traceback.format_exc())
        BRIGHTNESS_LEVELS = DEFAULT_BRIGHTNESS_LEVELS.copy()
        SELECTED_MONITOR_KEYS = []
        brightness_hotkey = DEFAULT_BRIGHTNESS_HOTKEY.copy()
        pip_hotkey = DEFAULT_PIP_HOTKEY.copy()
        ghost_hotkey = DEFAULT_GHOST_HOTKEY.copy()
        app_ghost_hotkey = DEFAULT_APP_GHOST_HOTKEY.copy()
        left_click_hotkey = DEFAULT_LEFT_CLICK_HOTKEY.copy()
        right_click_hotkey = DEFAULT_RIGHT_CLICK_HOTKEY.copy()
        mouse_keys_enabled = False
        mouse_keys_toggle_hotkey = DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY.copy()
        pip_opacity = DEFAULT_PIP_OPACITY
        app_ghost_opacity = DEFAULT_APP_GHOST_OPACITY


def save_config():
    try:
        with open(config_path(), "w", encoding="utf-8") as file:
            json.dump(
                {
                    "brightness_levels": BRIGHTNESS_LEVELS,
                    "selected_monitor_keys": SELECTED_MONITOR_KEYS,
                    "brightness_hotkey": brightness_hotkey,
                    "pip_hotkey": pip_hotkey,
                    "ghost_hotkey": ghost_hotkey,
                    "app_ghost_hotkey": app_ghost_hotkey,
                    "left_click_hotkey": left_click_hotkey,
                    "right_click_hotkey": right_click_hotkey,
                    "mouse_keys_enabled": mouse_keys_enabled,
                    "mouse_keys_toggle_hotkey": mouse_keys_toggle_hotkey,
                    "pip_opacity": pip_opacity,
                    "app_ghost_opacity": app_ghost_opacity,
                    "pip_ghost": pip_ghost,
                    "app_ghost_enabled": app_ghost_enabled,
                    "app_ghost_target_key": app_ghost_target_key,
                    "app_ghost_target_label": app_ghost_target_label,
                    "app_ghost_click_through": app_ghost_click_through,
                    "extra_dim_levels": extra_dim_levels,
                    "extra_dim_suspended": extra_dim_suspended,
                },
                file,
                indent=2,
            )
        log_event(
            f"config saved brightness={BRIGHTNESS_LEVELS} "
            f"selected_monitors={SELECTED_MONITOR_KEYS} "
            f"brightness_hotkey={hotkey_label(brightness_hotkey)} "
            f"pip_hotkey={hotkey_label(pip_hotkey)} "
            f"ghost_hotkey={hotkey_label(ghost_hotkey)} "
            f"app_ghost_hotkey={hotkey_label(app_ghost_hotkey)} "
            f"pip_opacity={pip_opacity} app_ghost_opacity={app_ghost_opacity}"
        )
    except Exception:
        log_event("save_config failed:\n" + traceback.format_exc())


def app_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def bundled_exe_path():
    source_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(source_dir, "dist", "ControleBrilho.exe")
    return path if os.path.exists(path) else ""


def redirect_source_run_to_exe():
    if getattr(sys, "frozen", False):
        return False
    if os.getenv("CONTROLE_BRILHO_ALLOW_SOURCE") == "1":
        return False

    exe_path = bundled_exe_path()
    if not exe_path:
        return False

    try:
        os.startfile(exe_path)
        log_event(f"source run redirected to exe path={exe_path}")
        return True
    except Exception:
        log_event("source redirect failed:\n" + traceback.format_exc())
        return False


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    exe_path = bundled_exe_path()
    if exe_path:
        return f'"{exe_path}"'

    path = app_path()
    if path.lower().endswith(".pyw"):
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        runner = pythonw if os.path.exists(pythonw) else sys.executable
        return f'"{runner}" "{path}"'
    return f'"{path}"'


def open_run_key(access=winreg.KEY_READ):
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        access,
    )


def is_startup_enabled():
    try:
        with open_run_key() as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_startup_enabled(enabled):
    try:
        with open_run_key(winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
    except OSError as error:
        report_error(f"Nao foi possivel alterar a inicializacao do Windows:\n{error}")


def report_error(message):
    if SILENT:
        return

    try:
        import tkinter as tk
        from tkinter import messagebox

        def _show():
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_TITLE, message)
            root.destroy()

        threading.Thread(target=_show, daemon=True).start()
    except Exception:
        pass


def display_info_value(info, *names):
    for name in names:
        value = info.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def make_display_key(info, index):
    parts = [
        display_info_value(info, "serial", "serial_number", "uid", "edid"),
        display_info_value(info, "name", "model", "manufacturer"),
        display_info_value(info, "method"),
        str(index),
    ]
    return "|".join(part.replace("|", "/") for part in parts if part)


def make_display_label(info, index):
    name = display_info_value(info, "name", "model")
    return f"Monitor {index + 1}: {name}" if name else f"Monitor {index + 1}"


def load_displays(force=False):
    global cached_displays, cached_displays_time, SELECTED_MONITOR_KEYS

    now = time.monotonic()
    if cached_displays and not force and now - cached_displays_time < DISPLAY_CACHE_SECONDS:
        return cached_displays

    try:
        infos = sbc.list_monitors_info(allow_duplicates=True)
        cached_displays = [
            {
                "display": sbc.Display(**info),
                "info": info,
                "key": make_display_key(info, index),
                "label": make_display_label(info, index),
            }
            for index, info in enumerate(infos)
        ]
        cached_displays_time = now
        available_keys = {entry["key"] for entry in cached_displays}
        if SELECTED_MONITOR_KEYS:
            selected = [key for key in SELECTED_MONITOR_KEYS if key in available_keys]
            if selected != SELECTED_MONITOR_KEYS:
                SELECTED_MONITOR_KEYS = selected
                save_config()
    except Exception:
        cached_displays = []
        cached_displays_time = now

    return cached_displays


def selected_display_entries():
    displays = load_displays()
    if not displays:
        return []
    if not SELECTED_MONITOR_KEYS:
        return displays

    selected = [entry for entry in displays if entry["key"] in SELECTED_MONITOR_KEYS]
    return selected or displays


def display_brightness(entry):
    values = entry["display"].get_brightness()
    if isinstance(values, (list, tuple)):
        values = [int(value) for value in values if value is not None]
        if not values:
            return None
        return clamp_brightness(round(sum(values) / len(values)))
    return clamp_brightness(values)


def get_current_brightness():
    now = time.monotonic()
    cached_value = last_brightness_read.get("value")
    if cached_value is not None and now - last_brightness_read.get("time", 0) < BRIGHTNESS_READ_CACHE_SECONDS:
        return cached_value

    try:
        selected_values = []
        for entry in selected_display_entries():
            value = display_brightness(entry)
            if value is not None:
                selected_values.append(value)

        if selected_values:
            value = round(sum(selected_values) / len(selected_values))
        else:
            values = sbc.get_brightness()
            if isinstance(values, (list, tuple)):
                values = [int(value) for value in values if value is not None]
                if not values:
                    return None
                value = round(sum(values) / len(values))
            else:
                value = int(values)

        value = clamp_brightness(value)
        last_brightness_read["value"] = value
        last_brightness_read["time"] = now
        return value
    except Exception:
        log_event("brightness read failed:\n" + traceback.format_exc())
        return None


def brightness_matches(current, target):
    return current is not None and abs(int(current) - int(target)) <= BRIGHTNESS_SAME_TOLERANCE


def set_brightness(value):
    global cycle_index, last_brightness

    value = clamp_brightness(value)

    with brightness_lock:
        current = get_current_brightness()
        if last_brightness == value and brightness_matches(current, value):
            log_event(f"brightness skipped target={value} current={current}")
            return
        if brightness_matches(current, value):
            last_brightness = value
            log_event(f"brightness already target={value} current={current}")
            return

        try:
            displays = load_displays()
            if displays:
                changed = False
                for entry in selected_display_entries():
                    try:
                        entry["display"].set_brightness(value, force=True)
                        changed = True
                    except Exception:
                        log_event(f"monitor brightness failed key={entry['key']!r}:\n" + traceback.format_exc())
                if not changed:
                    raise RuntimeError("Nenhum monitor selecionado aceitou controle de brilho.")
            else:
                sbc.set_brightness(value, force=True, no_return=True)
            last_brightness = value
            last_brightness_read["value"] = value
            last_brightness_read["time"] = time.monotonic()
            if value in BRIGHTNESS_LEVELS:
                with cycle_lock:
                    cycle_index = BRIGHTNESS_LEVELS.index(value)
            log_event(f"brightness set target={value} previous={current}")
        except Exception as error:
            report_error(f"Erro ao alterar o brilho para {value}%:\n{error}")


def set_cycle_level(index, value, apply_now=False):
    global BRIGHTNESS_LEVELS, cycle_index

    value = clamp_brightness(value)
    with cycle_lock:
        BRIGHTNESS_LEVELS[index] = value
        cycle_index = index
        save_config()

    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass

    if apply_now:
        request_brightness(value)


def refresh_monitor_list():
    load_displays(force=True)
    refresh_tray_menu()


def refresh_tray_menu():
    if tray_icon:
        try:
            tray_icon.menu = build_menu()
            tray_icon.update_menu()
        except Exception:
            pass


def set_all_monitors_selected():
    global SELECTED_MONITOR_KEYS

    SELECTED_MONITOR_KEYS = []
    save_config()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def toggle_monitor_selection(key):
    global SELECTED_MONITOR_KEYS

    displays = load_displays()
    all_keys = [entry["key"] for entry in displays]
    selected = set(SELECTED_MONITOR_KEYS or all_keys)
    if key in selected and len(selected) > 1:
        selected.remove(key)
    else:
        selected.add(key)

    if set(all_keys) == selected:
        SELECTED_MONITOR_KEYS = []
    else:
        SELECTED_MONITOR_KEYS = [entry["key"] for entry in displays if entry["key"] in selected]

    save_config()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def is_monitor_selected(key):
    if not SELECTED_MONITOR_KEYS:
        return True
    return key in SELECTED_MONITOR_KEYS


def set_pip_opacity(value, apply_now=True):
    global pip_opacity

    pip_opacity = clamp_pip_opacity(value)
    save_config()

    if apply_now:
        hwnd = find_pip_window(include_hidden=True, reset_others=True)
        if hwnd:
            opacity = pip_opacity
            if not pip_ghost and pip_opacity < 100 and cursor_inside_window(hwnd):
                opacity = 100
            apply_pip_opacity(hwnd, opacity)

    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def set_monitor_brightness(key, value):
    value = clamp_brightness(value)
    for entry in load_displays():
        if entry["key"] != key:
            continue
        try:
            entry["display"].set_brightness(value, force=True)
            log_event(f"monitor brightness set key={key!r} value={value}")
            last_brightness_read["value"] = None
            last_brightness_read["time"] = 0
        except Exception as error:
            report_error(f"Erro ao alterar o brilho deste monitor para {value}%:\n{error}")
        break

    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def open_settings_window():
    def _show():
        global settings_window

        import tkinter as tk
        from tkinter import ttk

        if settings_window is not None:
            try:
                if settings_window.winfo_exists():
                    settings_window.deiconify()
                    settings_window.lift()
                    settings_window.focus_force()
                    return
            except Exception:
                settings_window = None

        unregister_all_hotkeys()

        root = tk.Toplevel(ui_root) if ui_root is not None else tk.Tk()
        settings_window = root
        root.title(APP_TITLE)
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", lambda: close_settings())

        values = BRIGHTNESS_LEVELS.copy()
        level_one = tk.IntVar(value=values[0])
        level_two = tk.IntVar(value=values[1])
        brightness_keys = normalize_hotkey_keys(brightness_hotkey, DEFAULT_BRIGHTNESS_HOTKEY)
        pip_keys = normalize_hotkey_keys(pip_hotkey, DEFAULT_PIP_HOTKEY)
        ghost_keys = normalize_hotkey_keys(ghost_hotkey, DEFAULT_GHOST_HOTKEY)
        app_ghost_keys = normalize_hotkey_keys(app_ghost_hotkey, DEFAULT_APP_GHOST_HOTKEY)
        class CapturedKeyVar(tk.StringVar):
            def __init__(self, value):
                self.key = value
                super().__init__(value=hotkey_label([value]) if value else "")

            def get(self):
                return self.key

            def set(self, value):
                self.key = value
                super().set(hotkey_label([value]) if value else "")

        brightness_hotkey_vars = [
            CapturedKeyVar(value=brightness_keys[index] if index < len(brightness_keys) else "")
            for index in range(3)
        ]
        pip_hotkey_vars = [
            CapturedKeyVar(value=pip_keys[index] if index < len(pip_keys) else "")
            for index in range(3)
        ]
        ghost_hotkey_vars = [
            CapturedKeyVar(value=ghost_keys[index] if index < len(ghost_keys) else "")
            for index in range(3)
        ]
        app_ghost_hotkey_vars = [
            CapturedKeyVar(value=app_ghost_keys[index] if index < len(app_ghost_keys) else "")
            for index in range(3)
        ]
        left_click_keys = normalize_hotkey_keys(left_click_hotkey, [])
        right_click_keys = normalize_hotkey_keys(right_click_hotkey, [])
        mouse_keys_toggle_keys = normalize_hotkey_keys(mouse_keys_toggle_hotkey, DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY)
        left_click_hotkey_vars = [CapturedKeyVar(value=left_click_keys[index] if index < len(left_click_keys) else "") for index in range(3)]
        right_click_hotkey_vars = [CapturedKeyVar(value=right_click_keys[index] if index < len(right_click_keys) else "") for index in range(3)]
        mouse_keys_toggle_hotkey_vars = [CapturedKeyVar(value=mouse_keys_toggle_keys[index] if index < len(mouse_keys_toggle_keys) else "") for index in range(3)]
        mouse_keys_enabled_var = tk.BooleanVar(value=mouse_keys_enabled)
        capture_status = tk.StringVar(value="")
        capturing = {
            "target": None,
            "button": None,
            "after_id": None,
            "deadline": 0,
            "arm_at": 0,
            "armed": False,
            "baseline_vks": set(),
            "last_hotkey": "",
            "stable_count": 0,
        }

        frame = ttk.Frame(root, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Nivel claro").grid(row=0, column=0, sticky="w", padx=(0, 10))
        spin_one = tk.Scale(frame, from_=0, to=100, orient="horizontal", length=200, resolution=1, variable=level_one)
        spin_one.grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="%").grid(row=0, column=2, sticky="w", padx=(4, 0))

        ttk.Label(frame, text="Nivel escuro").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        spin_two = tk.Scale(frame, from_=0, to=100, orient="horizontal", length=200, resolution=1, variable=level_two)
        spin_two.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(frame, text="%").grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(8, 0))

        hotkey_frame = ttk.Frame(frame)
        hotkey_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=(8, 0))
        for column in range(1, 4):
            hotkey_frame.columnconfigure(column, weight=1)

        ttk.Label(hotkey_frame, text="Atalho de brilho").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(hotkey_frame, text="Atalho do PiP").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        ttk.Label(hotkey_frame, text="Modo Fantasma").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        ttk.Label(hotkey_frame, text="App Fantasma").grid(row=6, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        ttk.Label(hotkey_frame, text="Clique esquerdo").grid(row=8, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        ttk.Label(hotkey_frame, text="Clique direito").grid(row=10, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        ttk.Label(hotkey_frame, text="Alternar cliques por tecla").grid(row=12, column=0, sticky="w", padx=(0, 10), pady=(8, 0))

        def make_hotkey_boxes(row, variables):
            buttons = []
            for index, variable in enumerate(variables):
                entry = ttk.Entry(
                    hotkey_frame,
                    width=10,
                    textvariable=variable,
                    state="readonly",
                )
                entry.grid(row=row, column=index + 1, sticky="we", padx=(0 if index == 0 else 6, 0))
                button = ttk.Button(hotkey_frame, text="Capturar")
                button.grid(row=row + 1, column=index + 1, sticky="we", padx=(0 if index == 0 else 6, 0), pady=(2, 0))
                buttons.append(button)
            return buttons

        brightness_capture_buttons = make_hotkey_boxes(0, brightness_hotkey_vars)
        pip_capture_buttons = make_hotkey_boxes(2, pip_hotkey_vars)
        ghost_capture_buttons = make_hotkey_boxes(4, ghost_hotkey_vars)
        app_ghost_capture_buttons = make_hotkey_boxes(6, app_ghost_hotkey_vars)
        left_click_capture_buttons = make_hotkey_boxes(8, left_click_hotkey_vars)
        right_click_capture_buttons = make_hotkey_boxes(10, right_click_hotkey_vars)
        mouse_keys_toggle_capture_buttons = make_hotkey_boxes(12, mouse_keys_toggle_hotkey_vars)

        def clear_hotkey_boxes(variables):
            for variable in variables:
                variable.set("")

        ttk.Button(
            hotkey_frame,
            text="Limpar",
            command=lambda: clear_hotkey_boxes(brightness_hotkey_vars),
        ).grid(row=1, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(
            hotkey_frame,
            text="Limpar",
            command=lambda: clear_hotkey_boxes(pip_hotkey_vars),
        ).grid(row=3, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(
            hotkey_frame,
            text="Limpar",
            command=lambda: clear_hotkey_boxes(ghost_hotkey_vars),
        ).grid(row=5, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(
            hotkey_frame,
            text="Limpar",
            command=lambda: clear_hotkey_boxes(app_ghost_hotkey_vars),
        ).grid(row=7, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(hotkey_frame, text="Limpar", command=lambda: clear_hotkey_boxes(left_click_hotkey_vars)).grid(row=9, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(hotkey_frame, text="Limpar", command=lambda: clear_hotkey_boxes(right_click_hotkey_vars)).grid(row=11, column=0, sticky="we", padx=(0, 10), pady=(2, 0))
        ttk.Button(hotkey_frame, text="Limpar", command=lambda: clear_hotkey_boxes(mouse_keys_toggle_hotkey_vars)).grid(row=13, column=0, sticky="we", padx=(0, 10), pady=(2, 0))

        def start_capture(target, button):
            if capturing["after_id"] is not None:
                try:
                    root.after_cancel(capturing["after_id"])
                except Exception:
                    pass

            if capturing["button"]:
                capturing["button"].configure(text="Capturar")

            capturing["target"] = target
            capturing["button"] = button
            capturing["deadline"] = time.monotonic() + 8
            capturing["arm_at"] = time.monotonic() + 0.25
            capturing["armed"] = False
            capturing["baseline_vks"] = set()
            capturing["last_hotkey"] = ""
            capturing["stable_count"] = 0
            capture_status.set("Preparando captura...")
            button.configure(text="Aguardando...")
            root.lift()
            root.focus_force()
            root.after(30, root.focus_force)
            capturing["after_id"] = root.after(50, poll_capture)

        def finish_capture(message=None):
            if capturing["after_id"] is not None:
                try:
                    root.after_cancel(capturing["after_id"])
                except Exception:
                    pass

            if capturing["button"]:
                capturing["button"].configure(text="Capturar")
            if message:
                capture_status.set(message)

            capturing["target"] = None
            capturing["button"] = None
            capturing["after_id"] = None
            capturing["deadline"] = 0
            capturing["arm_at"] = 0
            capturing["armed"] = False
            capturing["baseline_vks"] = set()
            capturing["last_hotkey"] = ""
            capturing["stable_count"] = 0

        def poll_capture():
            if capturing["target"] is None:
                return

            if not capturing["armed"]:
                if time.monotonic() < capturing["arm_at"]:
                    capturing["after_id"] = root.after(35, poll_capture)
                    return

                capturing["armed"] = True
                capturing["baseline_vks"] = pressed_capture_vks()
                if capturing["button"]:
                    capturing["button"].configure(text="Pressione...")
                capture_status.set("Agora pressione uma tecla...")
                root.focus_force()
                capturing["after_id"] = root.after(80, poll_capture)
                return

            hotkey, current_vks = first_new_capture_hotkey(capturing["baseline_vks"])
            if hotkey:
                if hotkey == capturing["last_hotkey"]:
                    capturing["stable_count"] += 1
                else:
                    capturing["last_hotkey"] = hotkey
                    capturing["stable_count"] = 1

                if capturing["stable_count"] >= 2:
                    capturing["target"].set(hotkey)
                    finish_capture(f"Capturado: {hotkey_label([hotkey])}")
                    return
            else:
                capturing["baseline_vks"] = current_vks
                capturing["last_hotkey"] = ""
                capturing["stable_count"] = 0

            if time.monotonic() >= capturing["deadline"]:
                finish_capture("Captura cancelada.")
                return

            capturing["after_id"] = root.after(80, poll_capture)

        def on_key_press(event):
            if capturing["target"] is None:
                return
            if not capturing["armed"]:
                return "break"

            hotkey = hotkey_from_tk_event(event)
            if hotkey:
                capturing["target"].set(hotkey)
                finish_capture(f"Capturado: {hotkey_label([hotkey])}")
                return "break"

            return "break"

        root.bind_all("<KeyPress>", on_key_press, add="+")

        for index, button in enumerate(brightness_capture_buttons):
            button.configure(
                command=lambda variable=brightness_hotkey_vars[index], capture_button=button: start_capture(
                    variable,
                    capture_button,
                )
            )

        for index, button in enumerate(pip_capture_buttons):
            button.configure(
                command=lambda variable=pip_hotkey_vars[index], capture_button=button: start_capture(
                    variable,
                    capture_button,
                )
            )

        for index, button in enumerate(ghost_capture_buttons):
            button.configure(
                command=lambda variable=ghost_hotkey_vars[index], capture_button=button: start_capture(
                    variable,
                    capture_button,
                )
            )

        for index, button in enumerate(app_ghost_capture_buttons):
            button.configure(
                command=lambda variable=app_ghost_hotkey_vars[index], capture_button=button: start_capture(
                    variable,
                    capture_button,
                )
            )

        for variables, buttons in ((left_click_hotkey_vars, left_click_capture_buttons), (right_click_hotkey_vars, right_click_capture_buttons), (mouse_keys_toggle_hotkey_vars, mouse_keys_toggle_capture_buttons)):
            for index, button in enumerate(buttons):
                button.configure(command=lambda variable=variables[index], capture_button=button: start_capture(variable, capture_button))

        ttk.Checkbutton(frame, text="Cliques por tecla ativos", variable=mouse_keys_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Label(frame, textvariable=capture_status).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )

        def save_and_close():
            global settings_window

            proposed = {
                "brilho": normalize_hotkey_keys([variable.get() for variable in brightness_hotkey_vars], DEFAULT_BRIGHTNESS_HOTKEY),
                "PiP": normalize_hotkey_keys([variable.get() for variable in pip_hotkey_vars], DEFAULT_PIP_HOTKEY),
                "Modo Fantasma": normalize_hotkey_keys([variable.get() for variable in ghost_hotkey_vars], DEFAULT_GHOST_HOTKEY),
                "App Fantasma": normalize_hotkey_keys([variable.get() for variable in app_ghost_hotkey_vars], DEFAULT_APP_GHOST_HOTKEY),
                "clique esquerdo": normalize_hotkey_keys([variable.get() for variable in left_click_hotkey_vars], []),
                "clique direito": normalize_hotkey_keys([variable.get() for variable in right_click_hotkey_vars], []),
                "alternar cliques por tecla": normalize_hotkey_keys([variable.get() for variable in mouse_keys_toggle_hotkey_vars], DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY),
            }
            click_keys = [tuple(proposed[name]) for name in ("clique esquerdo", "clique direito")]
            for name, keys in proposed.items():
                if name in ("clique esquerdo", "clique direito") or not keys:
                    continue
                if tuple(keys) in click_keys:
                    messagebox.showerror(APP_TITLE, f"A tecla de {name} tambem esta configurada para um clique.", parent=root)
                    return
            if click_keys[0] and click_keys[0] == click_keys[1]:
                messagebox.showerror(APP_TITLE, "Escolha teclas diferentes para os dois cliques.", parent=root)
                return
            toggle_keys = tuple(proposed["alternar cliques por tecla"])
            for name, keys in proposed.items():
                if name != "alternar cliques por tecla" and tuple(keys) == toggle_keys:
                    messagebox.showerror(APP_TITLE, f"A tecla de alternar cliques por tecla tambem esta configurada para {name}.", parent=root)
                    return
            if mouse_keys_enabled_var.get() and not any(click_keys):
                messagebox.showerror(APP_TITLE, "Escolha ao menos uma tecla para ativar os cliques.", parent=root)
                return

            set_cycle_level(0, level_one.get())
            set_cycle_level(1, level_two.get())
            set_brightness_hotkey([variable.get() for variable in brightness_hotkey_vars])
            set_pip_hotkey([variable.get() for variable in pip_hotkey_vars])
            set_ghost_hotkey([variable.get() for variable in ghost_hotkey_vars])
            set_app_ghost_hotkey([variable.get() for variable in app_ghost_hotkey_vars])
            set_left_click_hotkey([variable.get() for variable in left_click_hotkey_vars])
            set_right_click_hotkey([variable.get() for variable in right_click_hotkey_vars])
            set_mouse_keys_toggle_hotkey([variable.get() for variable in mouse_keys_toggle_hotkey_vars])
            set_mouse_keys_enabled(mouse_keys_enabled_var.get())
            finish_capture()
            root.destroy()
            settings_window = None
            register_all_hotkeys()
            if tray_icon:
                try:
                    tray_icon.update_menu()
                except Exception:
                    log_event("tray update after settings save failed:\n" + traceback.format_exc())

        def close_settings():
            global settings_window

            finish_capture()
            root.destroy()
            settings_window = None
            register_all_hotkeys()

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancelar", command=close_settings).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Salvar", command=save_and_close).grid(row=0, column=1)

        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{width}x{height}+{screen_width - width - 40}+{screen_height - height - 80}")

    if ui_root is not None:
        try:
            ui_root.after(0, _show)
        except Exception:
            log_event("open settings schedule failed:\n" + traceback.format_exc())
    else:
        _show()


def request_brightness(value):
    try:
        while True:
            brightness_queue.get_nowait()
    except queue.Empty:
        pass

    try:
        brightness_queue.put_nowait(value)
    except queue.Full:
        pass


def request_next_brightness():
    global cycle_index, extra_dim_suspended

    if any(extra_dim_levels.values()):
        with cycle_lock:
            bright_level = max(BRIGHTNESS_LEVELS)
            dark_level = min(BRIGHTNESS_LEVELS)
            extra_dim_suspended = not extra_dim_suspended
            value = bright_level if extra_dim_suspended else dark_level
            request_brightness(value)
        save_config()
        if tray_icon:
            tray_icon.update_menu()
        log_event(f"brightness extra dim toggle target={value} suspended={extra_dim_suspended}")
        return

    current = get_current_brightness()
    with cycle_lock:
        first, second = BRIGHTNESS_LEVELS
        if brightness_matches(current, first):
            cycle_index = 1
            value = second
        elif brightness_matches(current, second):
            cycle_index = 0
            value = first
        elif current is not None:
            midpoint = (first + second) / 2
            if first >= second:
                cycle_index = 1 if current >= midpoint else 0
            else:
                cycle_index = 1 if current <= midpoint else 0
            value = BRIGHTNESS_LEVELS[cycle_index]
        else:
            cycle_index = (cycle_index + 1) % len(BRIGHTNESS_LEVELS)
            value = BRIGHTNESS_LEVELS[cycle_index]

        log_event(f"brightness toggle current={current} target={value} levels={BRIGHTNESS_LEVELS}")

    request_brightness(value)


def get_work_area(hwnd=None):
    target = hwnd or win32gui.GetDesktopWindow()
    monitor = win32api.MonitorFromWindow(target, win32con.MONITOR_DEFAULTTONEAREST)
    return win32api.GetMonitorInfo(monitor)["Work"]


def get_virtual_screen_rect():
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return (left, top, left + width, top + height)


def clamp_window_top_to_virtual(top, height):
    _, virtual_top, _, virtual_bottom = get_virtual_screen_rect()
    if height >= virtual_bottom - virtual_top:
        return virtual_top
    return max(virtual_top, min(top, virtual_bottom - height))


def window_info(hwnd):
    try:
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        return title, class_name, rect
    except Exception:
        return "", "", (0, 0, 0, 0)


def is_hidden_on_side(hwnd):
    title, class_name, rect = window_info(hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return False

    virtual_left, virtual_top, virtual_right, virtual_bottom = get_virtual_screen_rect()
    hidden_left = left < virtual_left and right <= virtual_left + PIP_VISIBLE_STRIP + 8
    hidden_right = right > virtual_right and left >= virtual_right - PIP_VISIBLE_STRIP - 8
    overlaps_vertical = bottom > virtual_top and top < virtual_bottom
    return overlaps_vertical and (hidden_left or hidden_right)


def is_window_visible_candidate(hwnd, include_hidden=False):
    if win32gui.IsIconic(hwnd):
        return False

    title, class_name, _rect = window_info(hwnd)
    title_lower = title.lower()
    class_lower = class_name.lower()
    is_visible = bool(win32gui.IsWindowVisible(hwnd))
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    is_topmost = bool(ex_style & win32con.WS_EX_TOPMOST)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return False
    if is_strong_pip_window(hwnd, include_hidden=include_hidden):
        return True
    if not (40 <= width and 30 <= height):
        return False
    if include_hidden and is_hidden_on_side(hwnd):
        return is_known_hidden_pip(hwnd)
    if not is_visible:
        return False
    virtual_left, _, virtual_right, _ = get_virtual_screen_rect()
    return right > virtual_left - 40 and left < virtual_right + 40


def score_pip_window(hwnd, include_hidden=False):
    if not is_window_visible_candidate(hwnd, include_hidden=include_hidden):
        return 0
    if not is_strong_pip_window(hwnd, include_hidden=include_hidden):
        return 0

    title, class_name, rect = window_info(hwnd)
    title = title.lower()
    class_name = class_name.lower()
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    ratio = width / height if height else 0
    score = 0

    text = f"{title} {class_name}"
    pip_words = ("picture", "pip", "imagem", "ecrã", "ecra", "pantalla", "bild", "image")
    if any(word in text for word in pip_words):
        score += 80
    if "youtube" in text or "chrome" in text or "msedge" in text:
        score += 35
    if class_name == "chrome_widgetwin_1":
        score += 30
    if 1.2 <= ratio <= 2.4:
        score += 15
    if title in ("picture-in-picture", "picture in picture"):
        score += 80
    if not title and class_name == "chrome_widgetwin_1":
        score += 15
    if include_hidden and is_hidden_on_side(hwnd):
        score += 45

    return score


def pip_candidate_sort_key(item):
    score, order, hwnd = item
    known = 1 if hwnd == pip_state.get("hwnd") else 0
    hovering = 1 if cursor_inside_window(hwnd) else 0
    hidden = 1 if is_known_hidden_pip(hwnd) else 0
    return (hidden, hovering, known, score, -order)


def reset_other_pip_opacity(selected_hwnd, candidates):
    if pip_opacity >= 100:
        return

    for _score, _order, hwnd in candidates:
        if hwnd == selected_hwnd:
            continue
        try:
            apply_pip_opacity(hwnd, 100)
        except Exception:
            log_event("pip reset other opacity failed:\n" + traceback.format_exc())


def find_pip_window(include_hidden=False, reset_others=False):
    candidates = []
    order = 0

    def collect(hwnd, _extra):
        nonlocal order
        current_order = order
        order += 1
        score = score_pip_window(hwnd, include_hidden=include_hidden)
        if score:
            candidates.append((score, current_order, hwnd))

    win32gui.EnumWindows(collect, None)
    if not candidates:
        return None

    candidates.sort(key=pip_candidate_sort_key, reverse=True)
    score, order, hwnd = candidates[0]
    title, class_name, rect = window_info(hwnd)
    log_event(
        f"pip candidate score={score} order={order} count={len(candidates)} "
        f"title={title!r} class={class_name!r} rect={rect}"
    )
    if score >= 45:
        if reset_others:
            reset_other_pip_opacity(hwnd, candidates)
        apply_pip_opacity(hwnd)
        return hwnd
    return None


def window_process_id(hwnd):
    try:
        _thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
        return process_id
    except Exception:
        return None


def find_browser_windows(owner_pid=None):
    candidates = []

    def collect(hwnd, _extra):
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return

        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        title_lower = title.lower()
        process_id = window_process_id(hwnd)
        if title_lower == "picture-in-picture":
            return
        if owner_pid is None and class_name != "Chrome_WidgetWin_1":
            return
        if owner_pid is not None and process_id != owner_pid:
            return

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width < 500 or height < 300:
            return

        score = 0
        if "youtube" in title_lower:
            score += 80
        if "microsoft edge" in title_lower or "google chrome" in title_lower:
            score += 40
        if owner_pid is not None and process_id == owner_pid:
            score += 120
        if class_name == "Chrome_WidgetWin_1":
            score += 20
        if title:
            score += 10
        candidates.append((score, hwnd))

    win32gui.EnumWindows(collect, None)
    candidates.sort(reverse=True)
    return [hwnd for _score, hwnd in candidates[:4]]


def send_appcommand(hwnd, command):
    try:
        win32gui.SendMessage(
            hwnd,
            WM_APPCOMMAND,
            hwnd,
            command << 16,
        )
        return True
    except Exception:
        return False


def send_pip_media_command(command, pip_hwnd=None):
    targets = []
    owner_pid = window_process_id(pip_hwnd) if pip_hwnd else None

    if pip_hwnd:
        targets.append(pip_hwnd)
    targets.extend(find_browser_windows(owner_pid=owner_pid))
    if owner_pid is None:
        targets.extend(find_browser_windows())

    sent = False
    for hwnd in dict.fromkeys(targets):
        sent = send_appcommand(hwnd, command) or sent
        time.sleep(0.02)

    log_event(
        f"media command sent command={command} owner_pid={owner_pid} "
        f"targets={len(dict.fromkeys(targets))} sent={sent}"
    )
    return sent


async def get_browser_media_session():
    if MediaSessionManager is None:
        return None

    manager = await MediaSessionManager.request_async()
    sessions = list(manager.get_sessions())
    if not sessions:
        return None

    current = manager.get_current_session()
    ordered = []
    if current:
        ordered.append(current)
    ordered.extend(session for session in sessions if session != current)

    for session in ordered:
        source = str(session.source_app_user_model_id or "").lower()
        if any(token in source for token in BROWSER_MEDIA_SOURCE_TOKENS):
            return session

    sources = []
    for session in ordered:
        try:
            playback_info = session.get_playback_info()
            status = playback_info.playback_status
        except Exception:
            status = "?"
        sources.append(f"{session.source_app_user_model_id}:{status}")
    log_event(f"media session skipped: no browser session sources={sources}")
    return None


async def get_browser_media_status_async():
    session = await get_browser_media_session()
    if not session:
        return None

    try:
        status = session.get_playback_info().playback_status
        source = session.source_app_user_model_id
        log_event(f"media session status source={source} status={status}")
        if MediaPlaybackStatus:
            if status == MediaPlaybackStatus.PLAYING:
                return "playing"
            if status == MediaPlaybackStatus.PAUSED:
                return "paused"
        return str(status)
    except Exception:
        log_event("media session status failed:\n" + traceback.format_exc())
        return None


def browser_media_status():
    if MediaSessionManager is None:
        return None

    try:
        return asyncio.run(get_browser_media_status_async())
    except Exception:
        log_event("browser media status failed:\n" + traceback.format_exc())
        return None


async def run_media_session_action(action):
    session = await get_browser_media_session()
    if not session:
        return False

    source = session.source_app_user_model_id
    playback_info = session.get_playback_info()
    status = playback_info.playback_status

    if action == "pause":
        if MediaPlaybackStatus and status == MediaPlaybackStatus.PAUSED:
            log_event(f"media session pause skipped source={source} status={status}")
            return True
        result = await session.try_pause_async()
        expected_status = MediaPlaybackStatus.PAUSED if MediaPlaybackStatus else None
    elif action == "play":
        if MediaPlaybackStatus and status == MediaPlaybackStatus.PLAYING:
            log_event(f"media session play skipped source={source} status={status}")
            return True
        result = await session.try_play_async()
        expected_status = MediaPlaybackStatus.PLAYING if MediaPlaybackStatus else None
    else:
        return False

    log_event(
        f"media session action={action} source={source} "
        f"status_before={status} result={result}"
    )
    return bool(result)


def media_session_action(action):
    if MediaSessionManager is None:
        log_event(f"media session unavailable action={action} error={WINRT_IMPORT_ERROR}")
        return False

    try:
        return bool(asyncio.run(run_media_session_action(action)))
    except Exception:
        log_event("media session action failed:\n" + traceback.format_exc())
        return False


def detect_pip_visual_state(hwnd):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None

    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width < 120 or height < 80:
            return None

        center_x = left + width // 2
        center_y = top + height // 2

        crop_size = max(58, min(96, int(min(width, height) * 0.45)))
        half = crop_size // 2
        bbox = (
            max(left, center_x - half),
            max(top, center_y - half),
            min(right, center_x + half),
            min(bottom, center_y + half),
        )
        image = ImageGrab.grab(bbox=bbox).convert("L")

        w, h = image.size
        pixels = image.load()
        column_counts = []
        row_counts = [0] * h
        total_bright = 0
        for x in range(w):
            count = 0
            for y in range(h):
                if pixels[x, y] >= 205:
                    count += 1
                    row_counts[y] += 1
            column_counts.append(count)
            total_bright += count

        if total_bright < 25:
            log_event("pip visual state unknown: not enough bright pixels")
            return None
        if total_bright > int(w * h * 0.42):
            log_event(f"pip visual state unknown: too many bright pixels bright={total_bright} size={w}x{h}")
            return None

        threshold = max(3, int(h * 0.14))
        components = []
        start = None
        for index, count in enumerate(column_counts):
            if count >= threshold and start is None:
                start = index
            elif count < threshold and start is not None:
                components.append((start, index - 1))
                start = None
        if start is not None:
            components.append((start, len(column_counts) - 1))

        components = [
            (a, b)
            for a, b in components
            if b - a + 1 >= 3 and sum(column_counts[a : b + 1]) >= 12
        ]
        widths = [b - a + 1 for a, b in components]

        if len(components) >= 2:
            left_component, right_component = components[0], components[-1]
            gap = right_component[0] - left_component[1]
            if (
                gap >= 5
                and max(widths) <= int(w * 0.24)
                and min(widths[0], widths[-1]) >= max(3, int(w * 0.04))
                and left_component[0] > 2
                and right_component[1] < w - 3
            ):
                log_event(f"pip visual state=playing components={components} bright={total_bright}")
                return "playing"

        if len(components) == 1:
            component = components[0]
            component_width = component[1] - component[0] + 1
            if (
                int(w * 0.08) <= component_width <= int(w * 0.38)
                and component[0] > 3
                and component[1] < w - 4
            ):
                log_event(f"pip visual state=paused components={components} bright={total_bright}")
                return "paused"

        log_event(f"pip visual state unknown components={components} bright={total_bright}")
        return None
    except Exception:
        log_event("pip visual state failed:\n" + traceback.format_exc())
        return None


def pip_playback_status(hwnd):
    status = browser_media_status()
    if status in ("playing", "paused"):
        return status

    visual_status = detect_pip_visual_state(hwnd)
    if visual_status in ("playing", "paused"):
        return visual_status

    return None


def pause_pip_playback(hwnd):
    if send_pip_extension_command("pause"):
        return "extension"

    status = pip_playback_status(hwnd)
    if status == "paused":
        log_event("pip pause skipped: already paused")
        return "already_paused"

    if media_session_action("pause"):
        time.sleep(0.2)
        confirmed_status = pip_playback_status(hwnd)
        if confirmed_status == "paused":
            return "media"
        if confirmed_status is None:
            log_event("pip media pause accepted without readable confirmation")
            return "media"
        log_event(f"pip media pause not confirmed status_after={confirmed_status}")

    sent = send_pip_media_command(APPCOMMAND_MEDIA_PAUSE, hwnd)
    if sent:
        time.sleep(0.2)
        confirmed_status = pip_playback_status(hwnd)
        if confirmed_status != "playing":
            log_event(f"pip appcommand pause accepted status_after={confirmed_status}")
            return "media_command"
        log_event("pip appcommand pause sent but playback still looks playing")

    log_event("pip pause failed; hide cancelled")
    return None


def play_pip_playback(hwnd):
    if send_pip_extension_command("play"):
        return True
    if media_session_action("play"):
        return True
    sent = send_pip_media_command(APPCOMMAND_MEDIA_PLAY, hwnd)
    log_event(f"pip play fallback sent={sent}")
    return sent


def resume_pip_playback(hwnd, paused_by_app=False, pause_method=None, force=False):
    if not paused_by_app and not force:
        log_event("pip resume skipped: pause was not confirmed")
        return False
    if pause_method == "already_paused":
        log_event("pip resume skipped: video was already paused")
        return False
    if pause_method == "click":
        status = pip_playback_status(hwnd)
        if status == "playing":
            log_event("pip resume skipped: already playing")
            return True
        if send_pip_extension_command("play"):
            return True
        if media_session_action("play"):
            return True
        log_event("pip resume skipped: old click method disabled")
        return False
    if pause_method == "extension":
        if send_pip_extension_command("play"):
            return True
        if media_session_action("play"):
            return True
        sent = send_pip_media_command(APPCOMMAND_MEDIA_PLAY, hwnd)
        log_event(f"pip resume fallback method=extension sent={sent}")
        return sent
    if pause_method == "toggle":
        status = pip_playback_status(hwnd)
        if status == "playing":
            log_event("pip resume skipped: already playing")
            return True
        sent = send_pip_media_command(APPCOMMAND_MEDIA_PLAY_PAUSE, hwnd)
        log_event(f"pip resume fallback method=play_pause sent={sent}")
        return sent
    if pause_method == "media_command":
        status = pip_playback_status(hwnd)
        if status == "playing":
            log_event("pip resume skipped: already playing")
            return True
        sent = send_pip_media_command(APPCOMMAND_MEDIA_PLAY, hwnd)
        log_event(f"pip resume fallback method=media_command sent={sent}")
        return sent
    if media_session_action("play"):
        return True
    sent = send_pip_media_command(APPCOMMAND_MEDIA_PLAY, hwnd)
    log_event(f"pip resume fallback sent={sent}")
    return sent


def move_pip_to_side(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    virtual_left, virtual_top, virtual_right, virtual_bottom = get_virtual_screen_rect()
    center_x = left + width / 2
    distance_to_left = abs(center_x - virtual_left)
    distance_to_right = abs(virtual_right - center_x)

    if distance_to_left <= distance_to_right:
        side = "left"
        new_left = virtual_left - width + PIP_VISIBLE_STRIP
    else:
        side = "right"
        new_left = virtual_right - PIP_VISIBLE_STRIP

    new_top = clamp_window_top_to_virtual(top, height)
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        new_left,
        new_top,
        width,
        height,
        win32con.SWP_SHOWWINDOW,
    )
    apply_pip_opacity(hwnd)
    log_event(
        "pip hidden "
        f"side={side} virtual={(virtual_left, virtual_top, virtual_right, virtual_bottom)} "
        f"rect={(new_left, new_top, new_left + width, new_top + height)}"
    )


def default_restore_rect(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = max(320, right - left)
    height = max(180, bottom - top)
    work_left, work_top, work_right, work_bottom = get_work_area(hwnd)
    margin = 36
    new_left = max(work_left, work_right - width - margin)
    new_top = max(work_top, work_bottom - height - margin)
    return (new_left, new_top, new_left + width, new_top + height)


def restore_pip(hwnd, rect=None):
    if not rect:
        rect = default_restore_rect(hwnd)

    left, top, right, bottom = rect
    width = max(120, right - left)
    height = max(80, bottom - top)
    virtual_left, virtual_top, virtual_right, virtual_bottom = get_virtual_screen_rect()
    if right <= virtual_left or left >= virtual_right or bottom <= virtual_top or top >= virtual_bottom:
        left, top, right, bottom = default_restore_rect(hwnd)
        width = max(120, right - left)
        height = max(80, bottom - top)
    top = clamp_window_top_to_virtual(top, height)
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        left,
        top,
        width,
        height,
        win32con.SWP_SHOWWINDOW,
    )
    apply_pip_opacity(hwnd)
    log_event(f"pip restored rect={(left, top, left + width, top + height)}")


def reset_pip_state():
    global pip_state

    pip_state = {
        "hidden": False,
        "hwnd": None,
        "rect": None,
        "last_rect": None,
        "hidden_at": 0,
        "paused_by_app": False,
        "pause_method": None,
        "last_action": time.time(),
    }


def is_valid_pip_handle(hwnd, include_hidden=False):
    return bool(hwnd and win32gui.IsWindow(hwnd) and score_pip_window(hwnd, include_hidden=include_hidden) >= 45)


def toggle_pip_window():
    global pip_state, pip_last_action_time

    if not pip_lock.acquire(blocking=False):
        log_event("pip action ignored because another action is running")
        return

    try:
        now = time.monotonic()
        if now - pip_last_action_time < PIP_ACTION_COOLDOWN_SECONDS:
            log_event("pip action ignored by cooldown")
            return
        pip_last_action_time = now

        stored_hwnd = pip_state.get("hwnd")
        current_hwnd = find_pip_window(include_hidden=True, reset_others=True)
        if pip_state.get("hidden") and not is_valid_pip_handle(stored_hwnd, include_hidden=True):
            log_event("pip state reset: stored hwnd is no longer a PiP window")
            reset_pip_state()
            stored_hwnd = None

        if (
            pip_state.get("hidden")
            and stored_hwnd
            and is_hidden_on_side(stored_hwnd)
            and (not current_hwnd or current_hwnd == stored_hwnd or is_hidden_on_side(current_hwnd))
        ):
            hwnd = stored_hwnd
            restore_pip(hwnd, pip_state.get("rect") or pip_state.get("last_rect"))
            time.sleep(0.08)
            resume_pip_playback(
                hwnd,
                paused_by_app=pip_state.get("paused_by_app", True),
                pause_method=pip_state.get("pause_method"),
            )
            pip_state = {
                "hidden": False,
                "hwnd": hwnd,
                "rect": win32gui.GetWindowRect(hwnd),
                "last_rect": win32gui.GetWindowRect(hwnd),
                "hidden_at": 0,
                "paused_by_app": False,
                "pause_method": None,
                "last_action": time.time(),
            }
            log_event("pip action=restore-from-state")
            return

        hwnd = current_hwnd
        if not hwnd:
            log_event("pip action skipped: no candidate found")
            return

        if is_hidden_on_side(hwnd):
            restore_pip(hwnd, pip_state.get("rect") or pip_state.get("last_rect"))
            time.sleep(0.08)
            resume_pip_playback(
                hwnd,
                paused_by_app=pip_state.get("paused_by_app", True),
                pause_method=pip_state.get("pause_method"),
                force=not pip_state.get("pause_method"),
            )
            restored_rect = win32gui.GetWindowRect(hwnd)
            pip_state = {
                "hidden": False,
                "hwnd": hwnd,
                "rect": restored_rect,
                "last_rect": restored_rect,
                "hidden_at": 0,
                "paused_by_app": False,
                "pause_method": None,
                "last_action": time.time(),
            }
            log_event("pip action=restore-detected-hidden")
            return

        rect = win32gui.GetWindowRect(hwnd)
        pause_method = pause_pip_playback(hwnd)
        if pause_method is None:
            log_event("pip hide cancelled: pause was not confirmed or sent")
            return

        paused = pause_method != "already_paused"
        time.sleep(0.08)
        move_pip_to_side(hwnd)
        pip_state = {
            "hidden": True,
            "hwnd": hwnd,
            "rect": rect,
            "last_rect": rect,
            "hidden_at": time.time(),
            "paused_by_app": paused,
            "pause_method": pause_method,
            "last_action": time.time(),
        }
        log_event(f"pip action=hide paused={paused} method={pause_method}")
    except Exception as error:
        log_event("pip action failed:\n" + traceback.format_exc())
        report_error(f"Erro no controle do picture-in-picture:\n{error}")
    finally:
        pip_lock.release()


def request_hotkey_refresh():
    for hotkey_id in hotkey_active:
        hotkey_active[hotkey_id] = False
        hotkey_last_fire[hotkey_id] = 0
        hotkey_release_since[hotkey_id] = 0


def register_all_hotkeys():
    global hotkeys_suspended

    hotkeys_suspended = False
    request_hotkey_refresh()


def unregister_all_hotkeys():
    global hotkeys_suspended

    hotkeys_suspended = True
    request_hotkey_refresh()


def dispatch_hotkey(hotkey_id):
    log_event(f"hotkey fired id={hotkey_id}")
    if hotkey_id == HOTKEY_BRIGHTNESS_ID:
        threading.Thread(target=request_next_brightness, daemon=True).start()
    elif hotkey_id == HOTKEY_PIP_ID:
        threading.Thread(target=toggle_pip_window, daemon=True).start()
    elif hotkey_id == HOTKEY_GHOST_ID:
        threading.Thread(target=toggle_pip_ghost, daemon=True).start()
    elif hotkey_id == HOTKEY_APP_GHOST_ID:
        threading.Thread(target=toggle_app_ghost, daemon=True).start()
    elif hotkey_id == HOTKEY_LEFT_CLICK_ID and mouse_keys_enabled:
        click_at_cursor(False)
    elif hotkey_id == HOTKEY_RIGHT_CLICK_ID and mouse_keys_enabled:
        click_at_cursor(True)
    elif hotkey_id == HOTKEY_MOUSE_KEYS_TOGGLE_ID:
        set_mouse_keys_enabled(not mouse_keys_enabled, refresh_hotkeys=False)


def click_at_cursor(right):
    down, up = (0x0008, 0x0010) if right else (0x0002, 0x0004)
    events = (WindowsInput * 2)(
        WindowsInput(0, InputData(mi=MouseInput(0, 0, 0, down, 0, 0))),
        WindowsInput(0, InputData(mi=MouseInput(0, 0, 0, up, 0, 0))),
    )
    sent = send_input(2, events, ctypes.sizeof(WindowsInput))
    if sent == 1:
        send_input(1, ctypes.byref(events, ctypes.sizeof(WindowsInput)), ctypes.sizeof(WindowsInput))
    if sent != 2:
        log_event(f"mouse click failed button={'right' if right else 'left'} sent={sent} error={ctypes.get_last_error()}")


def is_modifier_pressed(modifier):
    if modifier == "ctrl":
        return is_vk_pressed(0x11) or is_vk_pressed(0xA2) or is_vk_pressed(0xA3)
    if modifier == "alt":
        return is_vk_pressed(0x12) or is_vk_pressed(0xA4) or is_vk_pressed(0xA5)
    if modifier == "shift":
        return is_vk_pressed(0x10) or is_vk_pressed(0xA0) or is_vk_pressed(0xA1)
    if modifier == "windows":
        return is_vk_pressed(0x5B) or is_vk_pressed(0x5C)
    return False


def is_hotkey_pressed(hotkey):
    vks = parse_hotkey_state(hotkey)
    if not vks:
        return False

    return all(is_vk_pressed(vk) for vk in vks)


def poll_hotkey(hotkey_id, hotkey):
    vks = parse_hotkey_state(hotkey)
    if not vks:
        hotkey_active[hotkey_id] = False
        hotkey_release_since[hotkey_id] = 0
        return

    pressed_states = [is_vk_pressed(vk) for vk in vks]
    pressed = all(pressed_states)
    any_pressed = any(pressed_states)
    was_active = hotkey_active.get(hotkey_id, False)
    now = time.monotonic()

    if pressed and not was_active:
        cooldown = 0.12 if hotkey_id in (HOTKEY_LEFT_CLICK_ID, HOTKEY_RIGHT_CLICK_ID) else HOTKEY_COOLDOWN_SECONDS
        if now - hotkey_last_fire.get(hotkey_id, 0) < cooldown:
            hotkey_active[hotkey_id] = True
            hotkey_release_since[hotkey_id] = 0
            return

        hotkey_active[hotkey_id] = True
        hotkey_release_since[hotkey_id] = 0
        hotkey_last_fire[hotkey_id] = now
        dispatch_hotkey(hotkey_id)
    elif was_active:
        if any_pressed:
            hotkey_release_since[hotkey_id] = 0
            return

        if hotkey_release_since.get(hotkey_id, 0) == 0:
            hotkey_release_since[hotkey_id] = now
        elif now - hotkey_release_since[hotkey_id] >= (0.03 if hotkey_id in (HOTKEY_LEFT_CLICK_ID, HOTKEY_RIGHT_CLICK_ID) else 0.15):
            hotkey_active[hotkey_id] = False
            hotkey_release_since[hotkey_id] = 0


def run_hotkey_loop():
    while not stop_event.is_set():
        try:
            if not hotkeys_suspended:
                poll_hotkey(HOTKEY_BRIGHTNESS_ID, brightness_hotkey)
                poll_hotkey(HOTKEY_PIP_ID, pip_hotkey)
                poll_hotkey(HOTKEY_GHOST_ID, ghost_hotkey)
                poll_hotkey(HOTKEY_APP_GHOST_ID, app_ghost_hotkey)
                poll_hotkey(HOTKEY_MOUSE_KEYS_TOGGLE_ID, mouse_keys_toggle_hotkey)
                if mouse_keys_enabled:
                    poll_hotkey(HOTKEY_LEFT_CLICK_ID, left_click_hotkey)
                    poll_hotkey(HOTKEY_RIGHT_CLICK_ID, right_click_hotkey)
            time.sleep(0.025)
        except Exception:
            log_event("run_hotkey_loop error:\n" + traceback.format_exc())
            time.sleep(0.2)


def start_hotkey_thread():
    global hotkey_thread

    if hotkey_thread and hotkey_thread.is_alive():
        return

    hotkey_thread = threading.Thread(target=run_hotkey_loop, daemon=True)
    hotkey_thread.start()


def set_brightness_hotkey(value):
    global brightness_hotkey

    value = normalize_hotkey_keys(value, DEFAULT_BRIGHTNESS_HOTKEY)

    brightness_hotkey = value
    save_config()
    log_event(f"brightness hotkey set to {hotkey_label(brightness_hotkey)}")
    request_hotkey_refresh()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def set_pip_hotkey(value):
    global pip_hotkey

    value = normalize_hotkey_keys(value, DEFAULT_PIP_HOTKEY)

    pip_hotkey = value
    save_config()
    log_event(f"pip hotkey set to {hotkey_label(pip_hotkey)}")
    request_hotkey_refresh()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def set_ghost_hotkey(value):
    global ghost_hotkey

    value = normalize_hotkey_keys(value, DEFAULT_GHOST_HOTKEY)

    ghost_hotkey = value
    save_config()
    log_event(f"ghost hotkey set to {hotkey_label(ghost_hotkey)}")
    request_hotkey_refresh()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def set_app_ghost_hotkey(value):
    global app_ghost_hotkey

    value = normalize_hotkey_keys(value, DEFAULT_APP_GHOST_HOTKEY)

    app_ghost_hotkey = value
    save_config()
    log_event(f"app ghost hotkey set to {hotkey_label(app_ghost_hotkey)}")
    request_hotkey_refresh()
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass


def set_left_click_hotkey(value):
    global left_click_hotkey
    left_click_hotkey = normalize_hotkey_keys(value, [])
    save_config()
    request_hotkey_refresh()
    if tray_icon:
        tray_icon.update_menu()


def set_right_click_hotkey(value):
    global right_click_hotkey
    right_click_hotkey = normalize_hotkey_keys(value, [])
    save_config()
    request_hotkey_refresh()
    if tray_icon:
        tray_icon.update_menu()


def set_mouse_keys_toggle_hotkey(value):
    global mouse_keys_toggle_hotkey
    mouse_keys_toggle_hotkey = normalize_hotkey_keys(value, DEFAULT_MOUSE_KEYS_TOGGLE_HOTKEY)
    save_config()
    request_hotkey_refresh()
    if tray_icon:
        tray_icon.update_menu()


def set_mouse_keys_enabled(enabled, refresh_hotkeys=True):
    global mouse_keys_enabled
    mouse_keys_enabled = bool(enabled)
    if refresh_hotkeys:
        request_hotkey_refresh()
    for hotkey_id, hotkey in ((HOTKEY_LEFT_CLICK_ID, left_click_hotkey), (HOTKEY_RIGHT_CLICK_ID, right_click_hotkey)):
        hotkey_active[hotkey_id] = mouse_keys_enabled and is_hotkey_pressed(hotkey)
        hotkey_release_since[hotkey_id] = 0
    save_config()
    if tray_icon:
        if refresh_hotkeys:
            tray_icon.update_menu()
        else:
            threading.Thread(target=tray_icon.update_menu, daemon=True).start()


def run_brightness_worker():
    while not stop_event.is_set():
        try:
            value = brightness_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        set_brightness(value)


def make_icon_image():
    image = Image.new("RGBA", (64, 64), (20, 22, 28, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 10, 48, 42), fill=(255, 207, 84, 255))
    draw.rectangle((26, 42, 38, 51), fill=(255, 207, 84, 255))
    draw.rectangle((23, 51, 41, 56), fill=(150, 158, 171, 255))
    draw.line((32, 2, 32, 8), fill=(255, 232, 160, 255), width=3)
    draw.line((8, 26, 14, 26), fill=(255, 232, 160, 255), width=3)
    draw.line((50, 26, 56, 26), fill=(255, 232, 160, 255), width=3)
    return image


def quit_app():
    stop_event.set()
    sync_pip_ghost()
    sync_app_ghost()
    if ui_root:
        try:
            ui_root.after(0, ui_root.quit)
        except Exception:
            pass
    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass


def display_signature():
    return tuple(entry["key"] for entry in load_displays(force=True))


def run_monitor_watcher():
    previous = display_signature()
    while not stop_event.wait(5):
        try:
            current = display_signature()
            if current != previous:
                previous = current
                log_event(f"monitors changed keys={list(current)}")
                if tray_icon:
                    tray_icon.menu = build_menu()
                    tray_icon.update_menu()
        except Exception:
            log_event("monitor watcher error:\n" + traceback.format_exc())


def start_monitor_watcher():
    global monitor_thread

    if monitor_thread and monitor_thread.is_alive():
        return

    monitor_thread = threading.Thread(target=run_monitor_watcher, daemon=True)
    monitor_thread.start()


def current_pip_handle_for_hover():
    global pip_hover_last_scan

    stored_hwnd = pip_state.get("hwnd")
    if is_valid_pip_handle(stored_hwnd, include_hidden=True):
        return stored_hwnd

    if not pip_ghost:
        return None

    now = time.monotonic()
    if now - pip_hover_last_scan < 1:
        return None

    pip_hover_last_scan = now
    return find_pip_window(include_hidden=True)


def run_pip_hover_watcher():
    global pip_hover_active

    while not stop_event.wait(0.08):
        try:
            if pip_opacity >= 100:
                if pip_hover_active:
                    pip_hover_active = False
                continue

            hwnd = current_pip_handle_for_hover()
            if not hwnd:
                if pip_hover_active:
                    pip_hover_active = False
                continue

            if pip_ghost:
                if pip_hover_active:
                    pip_hover_active = False
                apply_pip_opacity(hwnd, pip_opacity)
                continue

            hovering = cursor_inside_window(hwnd)
            if hovering == pip_hover_active:
                continue

            pip_hover_active = hovering
            apply_pip_opacity(hwnd, 100 if hovering else pip_opacity)
        except Exception:
            log_event("pip opacity watcher error:\n" + traceback.format_exc())
            time.sleep(0.3)


def start_pip_hover_watcher():
    global pip_hover_thread

    if pip_hover_thread and pip_hover_thread.is_alive():
        return

    pip_hover_thread = threading.Thread(target=run_pip_hover_watcher, daemon=True)
    pip_hover_thread.start()


def dim_monitors():
    return [win32api.GetMonitorInfo(handle) for handle, _dc, _rect in win32api.EnumDisplayMonitors()]


def set_extra_dim(device, value):
    global extra_dim_suspended
    extra_dim_levels[device] = max(0, min(95, int(value)))
    extra_dim_suspended = False
    save_config()
    if tray_icon:
        tray_icon.update_menu()


def is_extra_dim_enabled():
    return not extra_dim_suspended and any(extra_dim_levels.values())


def set_extra_dim_enabled(enabled):
    global extra_dim_suspended
    if enabled and not any(extra_dim_levels.values()):
        for info in dim_monitors():
            extra_dim_levels[info["Device"]] = 20
    extra_dim_suspended = not bool(enabled)
    save_config()
    if tray_icon:
        tray_icon.update_menu()


def clear_extra_dim():
    global extra_dim_suspended
    extra_dim_levels.clear()
    extra_dim_suspended = False
    save_config()
    if tray_icon:
        tray_icon.update_menu()


def sync_extra_dim():
    # All overlay windows belong to the Tk thread and never take input focus.
    import tkinter as tk
    if stop_event.is_set():
        return
    try:
        active = set()
        for info in dim_monitors():
            device = info["Device"]
            level = 0 if extra_dim_suspended else extra_dim_levels.get(device, 0)
            if not level:
                continue
            active.add(device)
            if device not in extra_dim_windows:
                window = tk.Toplevel(ui_root)
                window.withdraw()
                window.overrideredirect(True)
                window.configure(background="black")
                window.attributes("-topmost", True)
                window.update_idletasks()
                hwnd = win32gui.GetParent(window.winfo_id()) or window.winfo_id()
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE)
                extra_dim_windows[device] = (window, hwnd)
            window, hwnd = extra_dim_windows[device]
            left, top, right, bottom = info["Monitor"]
            win32gui.SetLayeredWindowAttributes(hwnd, 0, round(level * 255 / 100), win32con.LWA_ALPHA)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, left, top, right-left, bottom-top, win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW)
        for device in list(extra_dim_windows):
            if device not in active:
                window, _hwnd = extra_dim_windows.pop(device)
                window.destroy()
    except Exception:
        log_event("extra dim failed:\n" + traceback.format_exc())
    ui_root.after(150, sync_extra_dim)


def build_extra_dim_menu():
    items = [pystray.MenuItem(lambda item: "Desativar filtro" if is_extra_dim_enabled() else "Ativar filtro",
                             lambda *args: set_extra_dim_enabled(not is_extra_dim_enabled()))]
    for index, info in enumerate(dim_monitors(), 1):
        device = info["Device"]
        items.append(pystray.MenuItem(
            f"Monitor {index} ({device})",
            pystray.Menu(*(pystray.MenuItem(
                "Desativado" if level == 0 else f"{level}%",
                lambda *args, key=device, value=level: set_extra_dim(key, value),
                checked=lambda item, key=device, value=level: extra_dim_levels.get(key, 0) == value,
                radio=True,
            ) for level in [0, 10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95])),
        ))
    return pystray.Menu(*items)


def build_app_ghost_menu():
    items = [
        pystray.MenuItem("Atualizar lista", lambda *args: refresh_tray_menu()),
        pystray.MenuItem("Nenhum app selecionado", lambda *args: set_app_ghost_target("", ""), checked=lambda item: not app_ghost_target_key, radio=True),
        pystray.Menu.SEPARATOR,
    ]

    targets = open_app_targets()
    if not targets:
        items.append(pystray.MenuItem("Nenhum app aberto detectado", None, enabled=False))
    else:
        for target in targets:
            key = target["key"]
            label = target["label"]
            items.append(
                pystray.MenuItem(
                    label,
                    lambda *args, selected_key=key, selected_label=label: set_app_ghost_target(selected_key, selected_label),
                    checked=lambda item, selected_key=key: app_ghost_target_key == selected_key,
                    radio=True,
                )
            )

    return pystray.Menu(*items)


def build_app_ghost_enable_menu():
    items = [pystray.MenuItem("Atualizar lista", lambda *args: refresh_tray_menu())]
    targets = open_app_targets()
    if not targets:
        items.append(pystray.MenuItem("Nenhum app aberto detectado", None, enabled=False))
    else:
        for target in targets:
            key = target["key"]
            label = target["label"]
            items.append(
                pystray.MenuItem(
                    label,
                    lambda *args, selected_key=key, selected_label=label: set_app_ghost_target_and_enable(selected_key, selected_label),
                    checked=lambda item, selected_key=key: app_ghost_enabled and app_ghost_target_key == selected_key,
                    radio=True,
                )
            )

    return pystray.Menu(*items)


def build_menu():
    displays = load_displays()

    def section_label(text):
        return pystray.MenuItem(text, None, enabled=False)

    def brightness_cycle_text():
        if any(extra_dim_levels.values()):
            return f"{max(BRIGHTNESS_LEVELS)}% / {min(BRIGHTNESS_LEVELS)}% + filtro extra"
        return f"{BRIGHTNESS_LEVELS[0]}% / {BRIGHTNESS_LEVELS[1]}%"

    def app_ghost_target_text():
        return app_ghost_target_label or "nenhum app"

    field_one_menu = pystray.Menu(
        *(
            pystray.MenuItem(
                f"{value}%",
                lambda *args, level=value: set_cycle_level(0, level, apply_now=True),
                checked=lambda item, level=value: BRIGHTNESS_LEVELS[0] == level,
                radio=True,
            )
            for value in TRAY_BRIGHTNESS_LEVELS
        )
    )
    field_two_menu = pystray.Menu(
        *(
            pystray.MenuItem(
                f"{value}%",
                lambda *args, level=value: set_cycle_level(1, level, apply_now=True),
                checked=lambda item, level=value: BRIGHTNESS_LEVELS[1] == level,
                radio=True,
            )
            for value in TRAY_BRIGHTNESS_LEVELS
        )
    )
    pip_opacity_menu = pystray.Menu(
        *(
            pystray.MenuItem(
                f"{value}%",
                lambda *args, level=value: set_pip_opacity(level),
                checked=lambda item, level=value: pip_opacity == level,
                radio=True,
            )
            for value in PIP_OPACITY_LEVELS
        )
    )
    app_ghost_opacity_menu = pystray.Menu(
        *(
            pystray.MenuItem(
                f"{value}%",
                lambda *args, level=value: set_app_ghost_opacity(level),
                checked=lambda item, level=value: app_ghost_opacity == level,
                radio=True,
            )
            for value in APP_GHOST_OPACITY_LEVELS
        )
    )
    monitor_items = [
        pystray.MenuItem(
            "Todos os monitores",
            lambda *args: set_all_monitors_selected(),
            checked=lambda item: not SELECTED_MONITOR_KEYS,
            radio=True,
        ),
        pystray.MenuItem("Atualizar lista", lambda *args: refresh_monitor_list()),
        pystray.Menu.SEPARATOR,
    ]
    if displays:
        for entry in displays:
            key = entry["key"]
            label = entry["label"]
            monitor_items.append(
                pystray.MenuItem(
                    lambda item, text=label: text,
                    pystray.Menu(
                        pystray.MenuItem(
                            "Usar no atalho",
                            lambda *args, monitor_key=key: toggle_monitor_selection(monitor_key),
                            checked=lambda item, monitor_key=key: is_monitor_selected(monitor_key),
                            radio=False,
                        ),
                        pystray.Menu.SEPARATOR,
                        *(
                            pystray.MenuItem(
                                f"{value}%",
                                lambda *args, monitor_key=key, level=value: set_monitor_brightness(
                                    monitor_key,
                                    level,
                                ),
                            )
                            for value in TRAY_BRIGHTNESS_LEVELS
                        ),
                    ),
                )
            )
    else:
        monitor_items.append(pystray.MenuItem("Nenhum monitor detectado", None, enabled=False))

    monitors_menu = pystray.Menu(*monitor_items)

    return pystray.Menu(
        section_label("ACOES RAPIDAS"),
        pystray.MenuItem(
            lambda item: f"Alternar brilho ({hotkey_label(brightness_hotkey)}): {brightness_cycle_text()}",
            lambda *args: request_next_brightness(),
        ),
        pystray.MenuItem(lambda item: f"Ocultar/restaurar PiP ({hotkey_label(pip_hotkey)})", lambda *args: toggle_pip_window()),
        pystray.MenuItem(lambda item: f"Alternar Modo Fantasma ({hotkey_label(ghost_hotkey)})", lambda *args: toggle_pip_ghost()),
        pystray.MenuItem(
            lambda item: f"Alternar App Fantasma ({hotkey_label(app_ghost_hotkey)}): {app_ghost_target_text()}",
            lambda *args: toggle_app_ghost(),
            enabled=lambda item: bool(app_ghost_target_key),
        ),
        pystray.Menu.SEPARATOR,
        section_label("CLIQUES POR TECLA"),
        pystray.MenuItem(lambda item: f"Alternar cliques por tecla ({hotkey_label(mouse_keys_toggle_hotkey)}): {'ativados' if mouse_keys_enabled else 'desativados'}", lambda *args: set_mouse_keys_enabled(not mouse_keys_enabled), checked=lambda item: mouse_keys_enabled),
        pystray.MenuItem(lambda item: f"Clique esquerdo ({hotkey_label(left_click_hotkey)})", lambda *args: click_at_cursor(False)),
        pystray.MenuItem(lambda item: f"Clique direito ({hotkey_label(right_click_hotkey)})", lambda *args: click_at_cursor(True)),
        pystray.MenuItem("Configurar teclas...", lambda *args: open_settings_window()),
        pystray.Menu.SEPARATOR,
        section_label("BRILHO"),
        pystray.MenuItem(lambda item: f"Nivel claro: {BRIGHTNESS_LEVELS[0]}%", field_one_menu),
        pystray.MenuItem(lambda item: f"Nivel escuro: {BRIGHTNESS_LEVELS[1]}%", field_two_menu),
        pystray.MenuItem("Hotkeys e niveis...", lambda *args: open_settings_window()),
        pystray.Menu.SEPARATOR,
        section_label("PICTURE-IN-PICTURE"),
        pystray.MenuItem(lambda item: f"Alternar opacidade do PiP: {pip_opacity}%", lambda *args: cycle_pip_opacity()),
        pystray.MenuItem(lambda item: f"Escolher opacidade do PiP: {pip_opacity}%", pip_opacity_menu),
        pystray.MenuItem("Modo Fantasma", lambda *args: toggle_pip_ghost(), checked=lambda item: pip_ghost),
        pystray.Menu.SEPARATOR,
        section_label("APPS"),
        pystray.MenuItem(lambda item: f"App selecionado: {app_ghost_target_text()}", build_app_ghost_menu()),
        pystray.MenuItem(lambda item: f"Escolher app e ativar: {app_ghost_target_text()}", build_app_ghost_enable_menu()),
        pystray.MenuItem(lambda item: f"Alternar opacidade do App Fantasma: {app_ghost_opacity}%", lambda *args: cycle_app_ghost_opacity()),
        pystray.MenuItem(lambda item: f"Escolher opacidade do App Fantasma: {app_ghost_opacity}%", app_ghost_opacity_menu),
        pystray.MenuItem(
            "Modo Fantasma do App",
            lambda *args: toggle_app_ghost(),
            checked=lambda item: app_ghost_enabled,
            enabled=lambda item: bool(app_ghost_target_key),
        ),
        pystray.MenuItem(
            "Usar App Fantasma",
            lambda *args: set_app_ghost_click_through(False),
            checked=lambda item: not app_ghost_click_through,
            enabled=lambda item: bool(app_ghost_target_key),
        ),
        pystray.MenuItem(
            "Cliques atravessam o App",
            lambda *args: set_app_ghost_click_through(True),
            checked=lambda item: app_ghost_click_through,
            enabled=lambda item: bool(app_ghost_target_key),
        ),
        pystray.Menu.SEPARATOR,
        section_label("TELAS E FILTROS"),
        pystray.MenuItem(
            lambda item: "Monitores do atalho: todos" if not SELECTED_MONITOR_KEYS else f"Monitores do atalho: {len(SELECTED_MONITOR_KEYS)}",
            monitors_menu,
        ),
        pystray.MenuItem("Filtro de escurecimento", build_extra_dim_menu()),
        pystray.Menu.SEPARATOR,
        section_label("SISTEMA"),
        pystray.MenuItem(
            "Abrir junto com o Windows",
            lambda *args: set_startup_enabled(not is_startup_enabled()),
            checked=lambda item: is_startup_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Fechar app (Esc)", lambda *args: quit_app()),
    )


class StyledTrayIcon(pystray.Icon):
    def _on_notify(self, wparam, lparam):
        if lparam in (win32con.WM_LBUTTONUP, win32con.WM_RBUTTONUP):
            try:
                open_tray_menu(sys.modules[__name__])
            except Exception:
                log_event("tray panel dispatch failed:\n" + traceback.format_exc())
        else:
            super()._on_notify(wparam, lparam)


def main():
    global tray_icon, ui_root

    if redirect_source_run_to_exe():
        return

    if not ensure_single_instance():
        return

    install_exception_logging()
    log_event("app starting")
    if MediaSessionManager is None:
        log_event(f"media winrt unavailable error={WINRT_IMPORT_ERROR}")
    else:
        log_event("media winrt available")
    load_config()
    log_event(
        f"loaded brightness_hotkey={hotkey_label(brightness_hotkey)} "
        f"pip_hotkey={hotkey_label(pip_hotkey)} "
        f"ghost_hotkey={hotkey_label(ghost_hotkey)} "
        f"app_ghost_hotkey={hotkey_label(app_ghost_hotkey)}"
    )
    load_displays()
    start_pip_extension_server()
    start_hotkey_thread()
    start_monitor_watcher()
    start_pip_hover_watcher()
    threading.Thread(target=run_pip_ghost_watcher, daemon=True).start()
    worker = threading.Thread(target=run_brightness_worker, daemon=True)
    worker.start()

    import tkinter as tk

    ui_root = tk.Tk()
    ui_root.withdraw()
    ui_root.protocol("WM_DELETE_WINDOW", quit_app)
    ui_root.after(0, sync_extra_dim)

    tray_icon = StyledTrayIcon(
        APP_NAME,
        make_icon_image(),
        APP_TITLE,
        build_menu(),
    )
    log_event("tray starting detached")
    tray_icon.run_detached()
    log_event("tk mainloop starting")
    try:
        ui_root.mainloop()
    finally:
        log_event("app stopping")
        stop_event.set()
        sync_pip_ghost()
        sync_app_ghost()
        try:
            if tray_icon:
                tray_icon.stop()
        except Exception:
            log_event("tray stop failed:\n" + traceback.format_exc())
        try:
            ui_root.destroy()
        except Exception:
            pass
        log_event("app stopped")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_event("fatal error:\n" + traceback.format_exc())
        raise
