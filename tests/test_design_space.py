"""Independent scaling, exact-engine parity, rejected grids and UI transfers."""
from dataclasses import replace
from io import StringIO

from unittest import TestCase
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.prediction import Needle, estimate
from src.design_space import SweepAxis, sweep, sensitivity_figure, figure_html, METRICS
from src.design_space_view import baseline_from_state
from src.paths import ROOT

LOAD = dict(axial_total_N=.001,lateral_total_N=.00001,loaded_needles=2,eccentricity_um=2.,bending_plane=0)


class DesignSpaceTests(TestCase):
    def test_exact_engine_and_constant_section_scaling(self):
        needle = Needle(base_width_um=100.,tip_width_um=100.)
        axes = [SweepAxis("length_um",1000.,2000.,2)]
        frame = sweep(needle,axes,LOAD)
        for _,row in frame.iterrows():
            expected = estimate(replace(needle,length_um=row.length_um),**LOAD)
            for metric in METRICS:
                self.assertEqual(row[metric],expected[metric])
        self.assertAlmostEqual(frame.iloc[1].axial_deformation_um/frame.iloc[0].axial_deformation_um,2.)
        self.assertAlmostEqual(frame.iloc[1].needle_axial_stiffness_N_per_mm/frame.iloc[0].needle_axial_stiffness_N_per_mm,.5)
        self.assertAlmostEqual(frame.iloc[1].elastic_buckling_indicator_N_per_needle/frame.iloc[0].elastic_buckling_indicator_N_per_needle,.25)

    def test_rejected_combinations_never_get_predictions(self):
        axes = [SweepAxis("base_width_um",20.,40.,3),SweepAxis("tip_width_um",20.,60.,3)]
        frame = sweep(Needle(),axes,LOAD)
        invalid = frame.status.eq("rejected")
        self.assertEqual(invalid.sum(),5)
        self.assertTrue(frame.loc[invalid,list(METRICS)].isna().all().all())
        self.assertTrue(frame.loc[invalid,"rejection_reason"].str.contains("Tip dimensions").all())
        self.assertTrue((frame.base_depth_um==frame.base_width_um).all())
        self.assertEqual(frame.loaded_needles.unique().tolist(),[2])
        figure = sensitivity_figure(frame,axes,next(iter(METRICS)))
        self.assertEqual(len(figure.data[1].x),4)

    def test_rectangular_depth_and_fixed_inputs(self):
        needle = Needle(shape="rectangular",base_width_um=180.,tip_width_um=30.,yield_strength_MPa=40.)
        axes = [SweepAxis("base_depth_um",100.,200.,2)]
        frame = sweep(needle,axes,LOAD)
        for key in ("length_um","base_width_um","tip_width_um","youngs_modulus_MPa","yield_strength_MPa"):
            self.assertTrue(frame[key].eq(getattr(needle,key)).all())
        self.assertLess(frame.iloc[0].needle_axial_stiffness_N_per_mm,frame.iloc[1].needle_axial_stiffness_N_per_mm)

    def test_bounds_budget_unsupported_axes_and_loads(self):
        for axes in ([],[SweepAxis("pitch",100.,200.,2)],
                     [SweepAxis("base_depth_um",100.,200.,2)],
                     [SweepAxis("length_um",0.,200.,2)],
                     [SweepAxis("length_um",200.,100.,2)],
                     [SweepAxis("length_um",100.,200.,26)],
                     [SweepAxis("length_um",100.,200.,16),SweepAxis("base_width_um",100.,200.,16)],
                     [SweepAxis("length_um",100.,200.,2)]*2):
            with self.assertRaises(ValueError):
                sweep(Needle(),axes,LOAD)
        with self.assertRaises(ValueError):
            sweep(Needle(),[SweepAxis("length_um",100.,200.,2)],dict(LOAD,loaded_needles=1.5))

    def test_exports_record_inputs_assumptions_and_gaps(self):
        axes = [SweepAxis("base_width_um",20.,40.,3)]
        frame = sweep(Needle(),axes,LOAD)
        csv = pd.read_csv(StringIO(frame.to_csv(index=False)))
        for key in ("assumptions","engine_sha256","model_version","sweep_axes_json",*LOAD,*METRICS):
            self.assertIn(key,csv)
        figure = sensitivity_figure(frame,axes,next(iter(METRICS)))
        self.assertFalse(figure.data[0].connectgaps)
        html = figure_html(figure,{"inputs":{"load":.001},"assumptions":"Unvalidated"})
        self.assertIn("Recorded inputs",html)
        self.assertIn("2600",html)
        self.assertNotIn('src="https://cdn.plot.ly',html)

    def test_baseline_matches_current_and_saved_studio(self):
        state = dict(studio_saved_single={"pred_length_um":1400.,"pred_axial":.002,"pred_plane":1},
                     compare_b_length_um=1800.,compare_shared_youngs_modulus_MPa=1200.,compare_count=4,
                     compare_shared_lateral=.003,compare_b_shape="rectangular")
        n,load = baseline_from_state(state,"Single design")
        self.assertEqual((n.length_um,load["axial_total_N"],load["bending_plane"]),(1400.,.002,1))
        n,load = baseline_from_state(state,"Design B")
        self.assertEqual((n.length_um,n.youngs_modulus_MPa,load["loaded_needles"]),(1800.,1200.,4))

    def app(self):
        return AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()

    def test_opt_in_sweep_selection_transfer_and_fixed_snapshot(self):
        app = self.app()
        self.assertFalse(app.checkbox(key="space_enabled").value)
        self.assertFalse(app.tabs)
        app.number_input(key="pred_lateral").set_value(.00001).run()
        app.checkbox(key="space_enabled").check().run()
        app.number_input(key="space_n_length_um").set_value(3)
        app.button(key="space_run").click().run()
        self.assertFalse(app.exception)
        result = app.session_state["space_result"]
        self.assertEqual(len(result["frame"]),3)
        app.selectbox(key="space_candidate").select(2).run()
        expected = result["frame"].iloc[2]
        app.number_input(key="pred_lateral").set_value(0.).run()
        self.assertEqual(app.session_state["space_result"]["manifest"]["loading"]["lateral_total_N"],.00001)
        app.button(key="space_apply").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="pred_length_um").value,expected.length_um)
        self.assertEqual(app.number_input(key="pred_lateral").value,.00001)

    def test_two_axes_and_transfer_from_comparison_preserves_b(self):
        app = self.app()
        app.toggle(key="studio_compare").set_value(True).run()
        app.number_input(key="compare_b_length_um").set_value(1650.).run()
        app.checkbox(key="space_enabled").check().run()
        app.selectbox(key="space_source").select("Design B").run()
        app.selectbox(key="space_y_circular_length_um").select("base_width_um").run()
        app.number_input(key="space_n_length_um").set_value(2)
        app.number_input(key="space_n_base_width_um").set_value(2)
        app.button(key="space_run").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["space_result"]["frame"]),4)
        app.selectbox(key="space_candidate").select(3).run()
        expected = app.session_state["space_result"]["frame"].iloc[3].length_um
        app.button(key="space_apply").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.toggle(key="studio_compare").value)
        self.assertEqual(app.number_input(key="pred_length_um").value,expected)
        app.toggle(key="studio_compare").set_value(True).run()
        self.assertEqual(app.number_input(key="compare_b_length_um").value,1650.)
