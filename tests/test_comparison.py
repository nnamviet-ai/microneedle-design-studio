"""A/B presentation, fairness, integrity and live UI regression checks."""
from dataclasses import replace

from unittest import TestCase
from streamlit.testing.v1 import AppTest
from src.prediction import Needle, estimate
from src.comparison import comparison_figure, comparison_table, interactive_html
from src.paths import ROOT


class ComparisonTests(TestCase):
    def test_shared_bounds_scale_and_real_geometry(self):
        a = Needle()
        b = replace(a,shape="rectangular",length_um=1600,base_width_um=300,base_depth_um=150)
        f = comparison_figure(a,b)
        for axis in ("xaxis","yaxis","zaxis"):
            self.assertEqual(getattr(f.layout.scene,axis).range,getattr(f.layout.scene2,axis).range)
        self.assertEqual(f.layout.scene.aspectratio,f.layout.scene2.aspectratio)
        spans = [getattr(f.layout.scene,axis).range[1]-getattr(f.layout.scene,axis).range[0] for axis in ("xaxis","yaxis","zaxis")]
        self.assertAlmostEqual(f.layout.scene.aspectratio.x/f.layout.scene.aspectratio.z,spans[0]/spans[2])
        meshes = [t for t in f.data if t.type=="mesh3d"]
        self.assertEqual(max(meshes[0].z),1000)
        self.assertEqual(max(meshes[1].z),1600)
        self.assertEqual(len([t for t in comparison_figure(a,b,array=True).data if t.type=="mesh3d"]),34)

    def test_differences_and_zero_baselines(self):
        a = estimate(Needle())
        b = estimate(replace(Needle(),length_um=2000))
        table = comparison_table(a,b)
        self.assertAlmostEqual(table.iloc[0]['B − A'],a['axial_deformation_um'])
        self.assertAlmostEqual(table.iloc[0]['Change from A (%)'],100)
        self.assertAlmostEqual(table.iloc[1]['Change from A (%)'],-50)
        self.assertTrue(table.iloc[2].isna()['Change from A (%)'])
        self.assertTrue(comparison_table(None,b)['B − A'].isna().all())

    def test_camera_and_standalone_export(self):
        html = interactive_html(comparison_figure(Needle(),Needle()),"test-camera")
        self.assertIn("localStorage.setItem",html)
        self.assertIn("plotly_relayout",html)
        self.assertIn(".finally",html)
        self.assertNotIn('src="https://cdn.plot.ly',html)
        self.assertIn('"width": 2400',html)

    def test_default_toggle_live_inputs_errors_and_exports(self):
        app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        self.assertFalse(app.toggle(key="studio_compare").value)
        app.number_input(key="pred_length_um").set_value(1250.).run()
        app.toggle(key="studio_compare").set_value(True).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.tabs)
        self.assertEqual(len(app.dataframe),1)
        app.number_input(key="compare_b_length_um").set_value(1500.).run()
        self.assertFalse(app.exception)
        self.assertNotEqual(app.dataframe[0].value.iloc[0]['Design A'],app.dataframe[0].value.iloc[0]['Design B'])
        app.number_input(key="compare_shared_youngs_modulus_MPa").set_value(0.).run()
        self.assertEqual(len(app.error),2)
        self.assertFalse(app.exception)
        app.number_input(key="compare_shared_youngs_modulus_MPa").set_value(3000.).run()
        app.segmented_control(key="compare_b_shape").set_value("rectangular").run()
        self.assertFalse(app.exception)
        app.number_input(key="compare_b_tip_width_um").set_value(9999.).run()
        self.assertTrue(any("Design B calculation unavailable" in e.value for e in app.error))
        self.assertTrue(app.dataframe[0].value['Design B'].isna().all())
        app.toggle(key="studio_compare").set_value(False).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="pred_length_um").value,1250.)
        app.toggle(key="studio_compare").set_value(True).run()
        self.assertEqual(app.number_input(key="compare_b_length_um").value,1500.)
