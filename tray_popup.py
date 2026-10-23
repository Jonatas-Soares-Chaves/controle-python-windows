"""Compact tray controls; all widgets stay on the Tk thread."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

BG = "#202124"
TEXT = "#e8eaed"
MUTED = "#aeb4b9"
LINE = "#3f4245"
GREEN = "#167b58"
SURFACE = "#2c2e31"


def popup_geometry(point, work, width=368, height=554):
    left, top, right, bottom = work
    width = min(width, right - left - 8)
    height = min(height, bottom - top - 8)
    x = max(left + 4, min(point[0] - width, right - width - 4))
    y = max(top + 4, min(point[1] - height, bottom - height - 4))
    return f"{width}x{height}{x:+d}{y:+d}"


class TrayPanel:
    def __init__(self, app, point):
        self.app = app
        self.root = tk.Toplevel(app.ui_root)
        self.root.title("Controles do Windows")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=LINE)
        self.pending = {}
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.closed = False
        self.inflight = 0
        self.poll_id = None
        self.dismiss_id = None
        self.resize_id = None
        self.dragging = False
        self.generation = 0
        self.tracked = []
        self.tab = "Brilho"
        self.display_key = ""
        self.filter_key = ""
        self.widgets = {}
        self.point = point
        threading.Thread(target=self.worker, daemon=True).start()
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(self.shell, bg=BG, padx=16, pady=12)
        header.pack(fill="x")
        self.label(header, "Controles do Windows", bold=True, size=12).pack(side="left")
        self.button(header, "\u00d7", self.close).pack(side="right")
        quick = tk.Frame(self.shell, bg=BG, padx=16)
        quick.pack(fill="x", pady=(0, 10))
        self.button(quick, "Alternar brilho", lambda: self.submit(app.request_next_brightness)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.button(quick, "Ocultar / restaurar PiP", lambda: self.submit(app.toggle_pip_window)).pack(side="left", fill="x", expand=True)
        bar = tk.Frame(self.shell, bg=BG, padx=12)
        bar.pack(fill="x")
        self.tab_buttons = {}
        for name in ("Brilho", "PiP", "Apps", "Teclas", "Sistema"):
            button = self.button(bar, name, lambda selected=name: self.render(selected))
            button.configure(padx=0)
            button.pack(side="left", fill="x", expand=True, padx=2)
            self.tab_buttons[name] = button
        tk.Frame(self.shell, height=1, bg=LINE).pack(fill="x", pady=(10, 0))
        area = tk.Frame(self.shell, bg=BG)
        area.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(area, bg=BG, highlightthickness=0)
        self.scrollbar = tk.Canvas(area, width=8, bg=BG, highlightthickness=0)
        self.scrollbar.pack(side="right", fill="y")
        self.scroll_fractions = (0.0, 1.0)
        self.scrollbar.bind("<Configure>", lambda event: self.paint_scrollbar())
        self.scrollbar.bind("<Button-1>", self.drag_scrollbar)
        self.scrollbar.bind("<B1-Motion>", self.drag_scrollbar)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.update_scrollbar)
        self.body = tk.Frame(self.canvas, bg=BG, padx=16, pady=12)
        self.body_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.body_id, width=event.width))
        self.root.bind("<MouseWheel>", self.scroll)
        footer = tk.Frame(self.shell, bg=BG, padx=16, pady=10)
        footer.pack(fill="x")
        self.button(footer, "Configurar atalhos", self.settings).pack(side="left")
        self.status = self.label(footer, "", color=MUTED, size=8)
        self.status.pack(side="right")
        self.fixed_sections = (header, quick, bar, footer)
        self.root.bind("<Escape>", lambda event: self.close())
        self.root.bind("<FocusOut>", self.dismiss)
        monitor = app.win32api.MonitorFromPoint(point, app.win32con.MONITOR_DEFAULTTONEAREST)
        work = app.win32api.GetMonitorInfo(monitor)["Work"]
        self.work = work
        self.root.geometry(popup_geometry(point, work))
        self.render("Brilho")
        self.root.deiconify()
        self.root.lift()
        try:
            hwnd = app.win32gui.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            app.win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.root.focus_force()
        self.poll_id = self.root.after(150, self.poll)

    def worker(self):
        while True:
            item = self.jobs.get()
            if item is None:
                return
            action, callback = item
            try:
                value = action()
                self.results.put((callback, value, False))
            except Exception:
                self.app.log_event("tray panel action failed:\n" + self.app.traceback.format_exc())
                self.results.put((None, None, True))

    def submit(self, action, callback=None):
        self.flush()
        self.enqueue(action, callback)

    def enqueue(self, action, callback=None):
        self.inflight += 1
        self.jobs.put((action, callback))

    def flush(self):
        for key in list(self.pending):
            after_id, action = self.pending.pop(key)
            self.root.after_cancel(after_id)
            self.enqueue(action)

    def debounce(self, key, action):
        if key in self.pending:
            self.root.after_cancel(self.pending.pop(key)[0])
        def send():
            pending = self.pending.pop(key, None)
            if pending:
                self.enqueue(pending[1])
        self.pending[key] = (self.root.after(140, send), action)

    def label(self, parent, text, bold=False, color=TEXT, size=10):
        return tk.Label(parent, text=text, bg=BG, fg=color, anchor="w", font=("Segoe UI", size, "bold" if bold else "normal"))

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=SURFACE, fg=TEXT,
                         activebackground=GREEN, activeforeground="white", relief="flat", bd=0,
                         padx=9, pady=6, font=("Segoe UI", 9), cursor="hand2", takefocus=True)

    def heading(self, text):
        self.label(self.body, text, bold=True).pack(fill="x", pady=(0, 10))

    def separator(self):
        tk.Frame(self.body, bg=LINE, height=1).pack(fill="x", pady=12)

    def slider(self, key, text, get, set_value, minimum=0, maximum=100):
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x")
        self.label(row, text, size=9).pack(side="left")
        value = tk.IntVar(value=int(get()))
        output = self.label(row, f"{value.get()}%", size=9, color=MUTED)
        output.pack(side="right")
        def changed(raw):
            number = int(float(raw))
            output.configure(text=f"{number}%")
            if self.dragging:
                self.debounce(key, lambda n=number: set_value(n))
        control = tk.Scale(self.body, from_=minimum, to=maximum, orient="horizontal", variable=value,
                           showvalue=False, command=changed, resolution=1, bg=GREEN, fg=TEXT,
                           troughcolor="#aeb8b3", activebackground="#29a67a", highlightthickness=0,
                           bd=0, sliderrelief="flat", sliderlength=16, width=9)
        control.pack(fill="x", pady=(2, 10))
        control.bind("<ButtonPress-1>", lambda event: setattr(self, "dragging", True))
        def released(event):
            self.dragging = False
            self.debounce(key, lambda n=int(control.get()): set_value(n))
            self.flush()
        control.bind("<ButtonRelease-1>", released)
        control.bind("<KeyRelease>", lambda event: self.debounce(key, lambda n=int(control.get()): set_value(n)))
        self.tracked.append((value, get, output))
        self.widgets[key] = control

    def check(self, text, get, setter):
        value = tk.BooleanVar(value=bool(get()))
        control = tk.Checkbutton(self.body, text=text, variable=value,
                                command=lambda: self.submit(lambda enabled=value.get(): setter(enabled)),
                                bg=BG, fg=TEXT, activebackground=BG, activeforeground=TEXT,
                                selectcolor=SURFACE, anchor="w", font=("Segoe UI", 9), bd=0, wraplength=285, justify="left")
        control.pack(fill="x", pady=4)
        self.tracked.append((value, get, None))
        return control

    def combo(self, text, labels, selected, callback):
        self.label(self.body, text, size=9).pack(fill="x", pady=(0, 5))
        value = tk.StringVar(value=selected)
        control = ttk.Combobox(self.body, textvariable=value, values=labels, state="readonly", width=25, font=("Segoe UI", 9))
        control.variable = value
        style = ttk.Style(self.root)
        style.map("Tray.TCombobox", foreground=[("readonly", "#202124")], fieldbackground=[("readonly", "#f7f8f8")])
        control.configure(style="Tray.TCombobox")
        control.pack(fill="x", pady=(0, 10))
        control.bind("<<ComboboxSelected>>", lambda event: callback(control.current()))
        return control

    def render(self, name):
        self.flush()
        self.generation += 1
        generation = self.generation
        self.tab = name
        self.tracked.clear()
        self.widgets.clear()
        for child in self.body.winfo_children():
            child.destroy()
        for key, button in self.tab_buttons.items():
            button.configure(bg=GREEN if key == name else SURFACE)
        self.canvas.yview_moveto(0)
        app = self.app
        if name == "Brilho":
            self.heading("Niveis do atalho")
            for index, label in enumerate(("Nivel claro", "Nivel escuro")):
                self.slider(f"level-{index}", label, lambda i=index: app.BRIGHTNESS_LEVELS[i],
                            lambda value, i=index: app.set_cycle_level(i, value, apply_now=True))
            self.separator()
            self.heading("Monitores e filtro")
            self.label(self.body, "Carregando monitores...", color=MUTED, size=9).pack(fill="x")
            self.submit(app.load_displays, lambda displays: self.render_monitors(displays) if generation == self.generation else None)
        elif name == "PiP":
            self.heading("Picture-in-picture")
            self.slider("pip-opacity", "Opacidade", lambda: app.pip_opacity, app.set_pip_opacity, 1)
            self.check("Modo Fantasma", lambda: app.pip_ghost, lambda enabled: app.toggle_pip_ghost() if enabled != app.pip_ghost else None)
            self.button(self.body, "Ocultar / restaurar", lambda: self.submit(app.toggle_pip_window)).pack(fill="x", pady=10)
        elif name == "Apps":
            self.heading("App Fantasma")
            self.label(self.body, "Carregando aplicativos...", color=MUTED, size=9).pack(fill="x")
            self.submit(app.open_app_targets, lambda targets: self.render_apps(targets) if self.tab == "Apps" else None)
        elif name == "Teclas":
            self.heading("Cliques por tecla")
            self.check("Ativar cliques por tecla", lambda: app.mouse_keys_enabled, app.set_mouse_keys_enabled)
            for title, keys in (("Clique esquerdo", app.left_click_hotkey), ("Clique direito", app.right_click_hotkey), ("Ativar / desativar", app.mouse_keys_toggle_hotkey)):
                self.label(self.body, title, size=9).pack(fill="x", pady=(12, 2))
                self.label(self.body, app.hotkey_label(keys), color=MUTED, size=9).pack(fill="x")
        else:
            self.heading("Sistema")
            self.check("Abrir junto com o Windows", app.is_startup_enabled, app.set_startup_enabled)
            self.button(self.body, "Atualizar monitores", lambda: self.submit(lambda: app.load_displays(force=True))).pack(fill="x", pady=12)
            self.button(self.body, "Desativar filtros", lambda: self.submit(app.clear_extra_dim)).pack(fill="x", pady=4)
            self.button(self.body, "Encerrar aplicativo", lambda: self.exit_app()).pack(fill="x", pady=(20, 4))
        self.request_resize()

    def request_resize(self):
        if self.resize_id:
            self.root.after_cancel(self.resize_id)
        self.resize_id = self.root.after_idle(self.resize)

    def resize(self):
        self.resize_id = None
        if self.closed:
            return
        self.root.update_idletasks()
        height = min(554, max(280, self.body.winfo_reqheight() + sum(widget.winfo_reqheight() for widget in self.fixed_sections) + 30))
        self.root.geometry(popup_geometry(self.point, self.work, height=height))

    def render_monitors(self, displays):
        for child in self.body.winfo_children():
            if isinstance(child, tk.Label) and child.cget("text") == "Carregando monitores...":
                child.destroy()
        app = self.app
        for entry in displays:
            key = entry["key"]
            self.check(entry["label"], lambda k=key: app.is_monitor_selected(k),
                       lambda enabled, k=key: app.toggle_monitor_selection(k) if enabled != app.is_monitor_selected(k) else None)
        if displays:
            selected = next((i for i, entry in enumerate(displays) if entry["key"] == self.display_key), 0)
            self.display_key = displays[selected]["key"]
            self.combo("Brilho do monitor", [entry["label"] for entry in displays], displays[selected]["label"],
                       lambda index: self.choose_display(displays[index]["key"]))
            current = {"value": app.BRIGHTNESS_LEVELS[0]}
            key = self.display_key
            generation = self.generation
            def set_brightness(value):
                app.set_monitor_brightness(key, value)
                current["value"] = value
            self.slider("monitor-brightness", "Brilho", lambda: current["value"], set_brightness)
            self.submit(lambda: displays[selected]["display"].get_brightness(),
                        lambda value: self.set_read_brightness(value, current) if generation == self.generation else None)
        else:
            self.label(self.body, "Nenhum monitor compativel", color=MUTED, size=9).pack(fill="x")
        filters = app.dim_monitors()
        if filters:
            selected = next((i for i, entry in enumerate(filters) if entry["Device"] == self.filter_key), 0)
            self.filter_key = filters[selected]["Device"]
            device = self.filter_key
            labels = [f"Monitor {i + 1}" for i in range(len(filters))]
            self.combo("Filtro de escurecimento", labels, labels[selected], lambda index: self.choose_filter(filters[index]["Device"]))
            self.slider("extra-dim", "Escurecimento extra", lambda: app.extra_dim_levels.get(device, 0),
                        lambda value: app.set_extra_dim(device, value), maximum=95)
        self.request_resize()

    def set_read_brightness(self, value, current):
        if self.tab != "Brilho" or "monitor-brightness" not in self.widgets or self.dragging:
            return
        if isinstance(value, list):
            value = value[0] if value else 100
        current["value"] = int(value)

    def choose_display(self, key):
        self.flush()
        self.display_key = key
        self.render("Brilho")

    def choose_filter(self, key):
        self.flush()
        self.filter_key = key
        self.render("Brilho")

    def render_apps(self, targets):
        if self.tab != "Apps":
            return
        for child in self.body.winfo_children()[1:]:
            child.destroy()
        self.tracked.clear()
        app = self.app
        labels = ["Nenhum app"] + [target["label"] for target in targets]
        selected = next((i + 1 for i, target in enumerate(targets) if target["key"] == app.app_ghost_target_key), 0)
        def select(index):
            target = targets[index - 1] if index else {"key": "", "label": ""}
            self.submit(lambda: app.set_app_ghost_target(target["key"], target["label"]))
        self.combo("Aplicativo", labels, labels[selected], select)
        self.button(self.body, "Atualizar lista", lambda: self.submit(app.open_app_targets, self.render_apps)).pack(fill="x", pady=(0, 12))
        self.slider("app-opacity", "Opacidade", lambda: app.app_ghost_opacity, app.set_app_ghost_opacity, 1)
        self.check("Modo Fantasma", lambda: app.app_ghost_enabled, app.set_app_ghost_enabled)
        self.check("Cliques atravessam o app", lambda: app.app_ghost_click_through, app.set_app_ghost_click_through)
        self.request_resize()

    def poll(self):
        if self.closed:
            return
        while not self.results.empty():
            callback, value, failed = self.results.get()
            self.inflight = max(0, self.inflight - 1)
            if failed:
                self.status.configure(text="Ajuste indisponivel")
            elif callback:
                try:
                    callback(value)
                except Exception:
                    self.app.log_event("tray panel refresh failed:\n" + self.app.traceback.format_exc())
        if not self.dragging and not self.pending and not self.inflight:
            for variable, get, output in self.tracked:
                try:
                    value = get()
                    if variable.get() != value:
                        variable.set(value)
                        if output:
                            output.configure(text=f"{int(value)}%")
                except (tk.TclError, ValueError):
                    pass
        self.poll_id = self.root.after(250, self.poll)

    def scroll(self, event):
        self.canvas.yview_scroll(-int(event.delta / 120), "units")
        return "break"

    def update_scrollbar(self, first, last):
        self.scroll_fractions = (float(first), float(last))
        self.paint_scrollbar()

    def paint_scrollbar(self):
        self.scrollbar.delete("all")
        first, last = self.scroll_fractions
        height = self.scrollbar.winfo_height()
        if last - first < .999:
            self.scrollbar.create_rectangle(1, first * height, 7, max(first * height + 14, last * height), fill="#73787b", outline="")

    def drag_scrollbar(self, event):
        first, last = self.scroll_fractions
        height = max(1, self.scrollbar.winfo_height())
        self.canvas.yview_moveto(max(0, min(1, event.y / height - (last - first) / 2)))

    def settings(self):
        self.close()
        self.app.open_settings_window()

    def exit_app(self):
        self.close()
        self.app.quit_app()

    def dismiss(self, event):
        def check():
            if not self.closed:
                focus = self.root.tk.call("focus", "-displayof", self.root)
                if not focus:
                    self.close()
        if self.dismiss_id:
            self.root.after_cancel(self.dismiss_id)
        self.dismiss_id = self.root.after(180, check)

    def close(self):
        if self.closed:
            return
        self.flush()
        self.closed = True
        for after_id in (self.poll_id, self.dismiss_id, self.resize_id):
            if after_id:
                self.root.after_cancel(after_id)
        self.jobs.put(None)
        self.root.destroy()


def open_tray_menu(app):
    point = app.win32gui.GetCursorPos()
    def show():
        try:
            old = getattr(app, "tray_panel", None)
            if old and not old.closed:
                old.close()
            app.tray_panel = TrayPanel(app, point)
        except Exception:
            app.log_event("tray panel failed:\n" + app.traceback.format_exc())
            app.pystray.Icon._on_notify(app.tray_icon, 0, app.win32con.WM_RBUTTONUP)
    app.ui_root.after(0, show)
