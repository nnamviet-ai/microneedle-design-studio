"""Check the public app without a workbook or source-project imports."""
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from src.paths import ROOT


class PublicAppTests(TestCase):
    def test_startup_rectangular_array_controls_and_exports(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertGreater(len(app.metric), 0)
        self.assertTrue(any("not included" in item.value for item in app.info))
        self.assertFalse((ROOT / "data").exists())
        app.radio(key="pred_shape").set_value("rectangular").run()
        app.number_input(key="pred_base_depth_um").set_value(180.).run()
        app.segmented_control(key="studio_view").set_value("4 \u00d7 4 array").run()
        app.checkbox(key="studio_wire").check().run()
        app.toggle(key="studio_dark").set_value(True).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertGreater(len(app.get("iframe")), 0)
        self.assertGreaterEqual(len(app.get("download_button")), 2)

    def test_private_records_cannot_be_loaded(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertFalse(app.exception)
        keys = {item.key for item in app.checkbox}
        self.assertNotIn("studio_load_fea", keys)
        self.assertNotIn("studio_load_mts", keys)
        self.assertEqual(app.selectbox(key="pred_preset").value,
                         "New user-defined design")
