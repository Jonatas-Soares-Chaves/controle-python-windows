"""Visual preview with fake controls; never changes real brightness or windows."""
import pathlib
import sys
import threading
import tkinter as tk
import traceback
from types import SimpleNamespace

import win32api
import win32con

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from tray_popup import TrayPanel


root = tk.Tk()
root.withdraw()
display = SimpleNamespace(value=65)
display.get_brightness = lambda: display.value
app = SimpleNamespace(
    ui_root=root, win32api=win32api, win32con=win32con, traceback=traceback,
    BRIGHTNESS_LEVELS=[70, 10], pip_opacity=80, pip_ghost=False,
    app_ghost_opacity=45, app_ghost_enabled=False, app_ghost_click_through=False,
    app_ghost_target_key="example", app_ghost_target_label="Aplicativo de teste",
    mouse_keys_enabled=False, left_click_hotkey=["z"], right_click_hotkey=["x"],
    mouse_keys_toggle_hotkey=["f5"], extra_dim_levels={"test": 20},
)
app.log_event = lambda message: print(message, flush=True)
app.load_displays = lambda **kwargs: [{"key": "test", "label": "Monitor principal", "display": display}]
app.dim_monitors = lambda: [{"Device": "test"}]
app.is_monitor_selected = lambda key: True
app.toggle_monitor_selection = lambda key: None
app.set_cycle_level = lambda index, value, apply_now=False: app.BRIGHTNESS_LEVELS.__setitem__(index, value)
app.set_monitor_brightness = lambda key, value: setattr(display, "value", value)
app.set_extra_dim = lambda key, value: app.extra_dim_levels.__setitem__(key, value)
app.clear_extra_dim = lambda: app.extra_dim_levels.clear()
app.request_next_brightness = lambda: None
app.toggle_pip_window = lambda: None
app.toggle_pip_ghost = lambda: setattr(app, "pip_ghost", not app.pip_ghost)
app.set_pip_opacity = lambda value: setattr(app, "pip_opacity", value)
app.set_app_ghost_opacity = lambda value: setattr(app, "app_ghost_opacity", value)
app.set_app_ghost_enabled = lambda value: setattr(app, "app_ghost_enabled", value)
app.set_app_ghost_click_through = lambda value: setattr(app, "app_ghost_click_through", value)
app.set_mouse_keys_enabled = lambda value: setattr(app, "mouse_keys_enabled", value)
app.is_startup_enabled = lambda: False
app.set_startup_enabled = lambda value: None
app.hotkey_label = lambda keys: " + ".join(keys) or "nenhuma"
app.open_app_targets = lambda: [{"key": "example", "label": "Aplicativo de teste"}]
app.set_app_ghost_target = lambda key, label: setattr(app, "app_ghost_target_key", key)
app.open_settings_window = lambda: None
app.quit_app = root.quit
info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTONEAREST))
right, bottom = info["Work"][2:]
TrayPanel.dismiss = lambda self, event: None
panel = TrayPanel(app, (right - 18, bottom - 18))
panel.root.overrideredirect(False)


def check_closed():
    if panel.closed:
        root.destroy()
    else:
        root.after(100, check_closed)


root.after(100, check_closed)
root.after(120000, root.destroy)
root.mainloop()
