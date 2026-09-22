"""Styled tray popup using the existing menu callbacks."""
import tkinter as tk
from PIL import ImageTk


def open_tray_menu(app):
    point = app.win32gui.GetCursorPos()

    def open_native_menu():
        try:
            app.pystray.Icon._on_notify(app.tray_icon, 0, app.win32con.WM_RBUTTONUP)
        except Exception:
            app.log_event("tray native fallback failed:\n" + app.traceback.format_exc())

    def item_value(item, name, default=None):
        try:
            value = getattr(item, name, default)
            if callable(value):
                return value(item)
            return value
        except Exception:
            app.log_event(f"tray item {name} failed:\n" + app.traceback.format_exc())
            return default

    def show():
        try:
            old = getattr(app, "tray_popup", None)
            if old is not None and old.winfo_exists():
                old.destroy()
            root = tk.Toplevel(app.ui_root)
            app.tray_popup = root
            root.withdraw()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(background="#41454a")
            shell = tk.Frame(root, background="#202326", padx=8, pady=8)
            shell.pack(fill="both", expand=True, padx=1, pady=1)
            header = tk.Frame(shell, background="#202326", padx=8, pady=8)
            header.pack(fill="x")
            root.logo = ImageTk.PhotoImage(app.make_icon_image().resize((26, 26)), master=root)
            tk.Label(header, image=root.logo, background="#202326").pack(side="left", padx=(0, 10))
            title = tk.Label(header, text="Controle de Brilho", font=("Segoe UI", 11, "bold"), foreground="#f5f7f8", background="#202326")
            title.pack(side="left")
            tk.Frame(shell, height=1, background="#3a3f44").pack(fill="x", pady=(7, 6))
            body = tk.Frame(shell, background="#202326")
            body.pack(fill="both", expand=True)
            history = []

            def close():
                if root.winfo_exists():
                    root.destroy()

            def position():
                root.update_idletasks()
                monitor = app.win32api.MonitorFromPoint(point, app.win32con.MONITOR_DEFAULTTONEAREST)
                left, top, right, bottom = app.win32api.GetMonitorInfo(monitor)["Work"]
                width, height = root.winfo_reqwidth(), root.winfo_reqheight()
                x = max(left + 4, min(point[0] - width, right - width - 4))
                y = max(top + 4, min(point[1] - height, bottom - height - 4))
                root.geometry(f"{width}x{height}{x:+d}{y:+d}")

            def row(text, marker, callback, enabled=True):
                frame = tk.Frame(body, background="#202326", padx=10, pady=7, cursor="hand2" if enabled else "arrow")
                frame.pack(fill="x", pady=1)
                label = tk.Label(frame, text=str(text), anchor="w", font=("Segoe UI", 10), background="#202326", foreground="#eef1f3" if enabled else "#808991")
                label.pack(side="left", fill="x", expand=True)
                trailing = tk.Label(frame, text=marker, width=2, font=("Segoe UI", 11), background="#202326", foreground="#6dd8b4")
                trailing.pack(side="right", padx=(12, 0))
                def hover(color):
                    for widget in (frame, label, trailing):
                        widget.configure(background=color)
                for widget in (frame, label, trailing):
                    widget.bind("<Enter>", lambda e: hover("#32383e") if enabled else None)
                    widget.bind("<Leave>", lambda e: hover("#202326"))
                    if enabled:
                        widget.bind("<ButtonRelease-1>", lambda e: callback())

            def section(text):
                frame = tk.Frame(body, background="#202326", padx=10, pady=(9, 3))
                frame.pack(fill="x")
                tk.Label(
                    frame,
                    text=str(text),
                    anchor="w",
                    font=("Segoe UI", 8, "bold"),
                    background="#202326",
                    foreground="#7bd9bf",
                ).pack(side="left", fill="x", expand=True)

            def render(menu, heading="Controle de Brilho"):
                for child in body.winfo_children():
                    child.destroy()
                title.configure(text=str(heading))
                if history:
                    row("Voltar", "<", back)
                    tk.Frame(body, height=1, background="#3a3f44").pack(fill="x", pady=5)
                for item in menu:
                    text = item_value(item, "text", "")
                    visible = bool(item_value(item, "visible", True))
                    enabled = bool(item_value(item, "enabled", True))
                    checked = bool(item_value(item, "checked", False))
                    submenu = item_value(item, "submenu", None)
                    if not visible:
                        continue
                    if text == "- - - -":
                        tk.Frame(body, height=1, background="#3a3f44").pack(fill="x", pady=5)
                        continue
                    if not enabled and not submenu and text and str(text).isupper():
                        section(text)
                        continue
                    marker = ">" if submenu else ("✓" if checked else "")
                    def activate(entry=item, entry_text=text, entry_submenu=submenu):
                        if entry_submenu:
                            history.append((menu, heading))
                            render(entry_submenu, entry_text)
                        else:
                            close()
                            def run():
                                try:
                                    entry(app.tray_icon)
                                except Exception:
                                    app.log_event("tray action failed:\n" + app.traceback.format_exc())
                            app.threading.Thread(target=run, daemon=True).start()
                    row(text, marker, activate, enabled)
                position()

            def back():
                menu, heading = history.pop()
                render(menu, heading)

            root.bind("<Escape>", lambda e: close())
            def dismiss(_event):
                def check():
                    if root.winfo_exists() and root.focus_get() is None:
                        close()
                root.after(100, check)
            root.bind("<FocusOut>", dismiss)
            render(app.build_menu())
            root.deiconify()
            root.lift()
            root.focus_force()
            app.log_event("tray popup opened")
        except Exception:
            app.log_event("tray popup show failed:\n" + app.traceback.format_exc())
            open_native_menu()
    app.ui_root.after(0, show)
