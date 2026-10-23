import importlib.util
import ast
import pathlib
import queue
import unittest
import tkinter as tk

spec = importlib.util.spec_from_file_location("tray_popup", pathlib.Path(__file__).parents[1] / "tray_popup.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeRoot:
    def __init__(self):
        self.next_id = 0
        self.callbacks = {}

    def after(self, delay, callback):
        self.next_id += 1
        self.callbacks[self.next_id] = callback
        return self.next_id

    def after_cancel(self, after_id):
        self.callbacks.pop(after_id, None)


class TrayPanelTests(unittest.TestCase):
    def core(self):
        tree = ast.parse((pathlib.Path(__file__).parents[1] / "controle_brilho.pyw").read_text(encoding="utf-8-sig"))
        names = {"display_info_value", "make_display_label", "set_extra_dim_enabled", "is_extra_dim_enabled"}
        scope = {"extra_dim_suspended": False, "extra_dim_levels": {"screen": 37}, "tray_icon": None,
                 "save_config": lambda: None, "dim_monitors": lambda: [{"Device": "screen"}]}
        selected = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
        exec(compile(selected, "core", "exec"), scope)
        return scope

    def test_filter_toggle_preserves_intensity(self):
        scope = self.core()
        scope["set_extra_dim_enabled"](False)
        self.assertFalse(scope["is_extra_dim_enabled"]())
        self.assertEqual(scope["extra_dim_levels"], {"screen": 37})
        scope["set_extra_dim_enabled"](True)
        self.assertTrue(scope["is_extra_dim_enabled"]())
        self.assertEqual(scope["extra_dim_levels"], {"screen": 37})

    def test_filter_first_activation_sets_visible_default(self):
        scope = self.core()
        scope["extra_dim_levels"] = {}
        scope["set_extra_dim_enabled"](True)
        self.assertEqual(scope["extra_dim_levels"], {"screen": 20})

    def test_monitor_label_contains_only_friendly_name(self):
        scope = self.core()
        label = scope["make_display_label"]({"name": "Asus 05F2", "method": type("WMI", (), {})}, 0)
        self.assertEqual(label, "Monitor 1: Asus 05F2")
        self.assertEqual(scope["make_display_label"]({}, 1), "Monitor 2")

    def test_friendly_key_display_preserves_saved_key_code(self):
        tree = ast.parse((pathlib.Path(__file__).parents[1] / "controle_brilho.pyw").read_text(encoding="utf-8-sig"))
        cls = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "CapturedKeyVar")
        scope = {"tk": tk, "hotkey_label": lambda keys: "Tecla de teste"}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "key_display", "exec"), scope)
        previous = tk._default_root
        interpreter = tk.Tcl()
        tk._default_root = interpreter
        try:
            value = scope["CapturedKeyVar"]("vk193")
            self.assertEqual(value.get(), "vk193")
            self.assertEqual(interpreter.globalgetvar(str(value)), "Tecla de teste")
            value.set("z")
            self.assertEqual(value.get(), "z")
            value.set("")
            self.assertEqual(interpreter.globalgetvar(str(value)), "")
            del value
        finally:
            tk._default_root = previous

    def panel(self):
        panel = object.__new__(module.TrayPanel)
        panel.root = FakeRoot()
        panel.jobs = queue.Queue()
        panel.pending = {}
        panel.inflight = 0
        return panel

    def test_drag_coalesces_and_flush_keeps_final_value(self):
        panel = self.panel()
        values = []
        panel.debounce("opacity", lambda: values.append(10))
        panel.debounce("opacity", lambda: values.append(35))
        panel.debounce("opacity", lambda: values.append(72))
        self.assertEqual(len(panel.root.callbacks), 1)
        panel.flush()
        self.assertFalse(panel.pending)
        self.assertFalse(panel.root.callbacks)
        panel.jobs.get()[0]()
        self.assertEqual(values, [72])
        self.assertTrue(panel.jobs.empty())

    def test_pending_slider_applies_before_next_action(self):
        panel = self.panel()
        values = []
        panel.debounce("monitor", lambda: values.append("old monitor brightness"))
        panel.submit(lambda: values.append("switch monitor"))
        while not panel.jobs.empty():
            panel.jobs.get()[0]()
        self.assertEqual(values, ["old monitor brightness", "switch monitor"])

    def test_geometry_respects_negative_monitor_and_small_work_area(self):
        self.assertEqual(module.popup_geometry((-5, 1000), (-1920, 0, 0, 1040)), "368x554-373+446")
        self.assertEqual(module.popup_geometry((10, 10), (0, 0, 320, 480)), "312x472+4+4")


if __name__ == "__main__":
    unittest.main()
