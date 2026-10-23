import importlib.util
import pathlib
import queue
import unittest

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
