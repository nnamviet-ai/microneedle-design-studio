"""Independent dimensional and topology checks of rendered geometry."""
from dataclasses import replace
from collections import Counter
import numpy as np
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from src.prediction import Needle
from src.geometry_3d import section_mesh, studio_figure
from src.paths import ROOT


class StudioGeometryTests(TestCase):
    def test_closed_solid_exact_end_sections_and_outward_winding(self):
        for shape in ("circular","rectangular"):
            needle = Needle(shape=shape,length_um=1500,base_width_um=300,tip_width_um=40,
                            base_depth_um=180,tip_depth_um=20)
            v,f,n = section_mesh(needle)
            self.assertEqual(np.ptp(v[:,2]),1500)
            self.assertEqual(np.ptp(v[:n,0]),300)
            self.assertEqual(np.ptp(v[n:2*n,0]),40)
            self.assertEqual(np.ptp(v[:n,1]),300 if shape=="circular" else 180)
            self.assertEqual(np.ptp(v[n:2*n,1]),40 if shape=="circular" else 20)
            edges=Counter(tuple(sorted((a,b))) for face in f for a,b in zip(face,np.roll(face,-1)))
            self.assertTrue(all(count==2 for count in edges.values()))
            normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
            centre=v[f].mean(axis=1)-[0,0,750]
            self.assertTrue(np.all(np.sum(normal*centre,axis=1)>0))

    def test_array_count_pitch_and_connected_base(self):
        for pitch in (400.,800.):
            fig=studio_figure(Needle(),array=True,pitch=pitch)
            needles=[t for t in fig.data if t.type=="mesh3d" and t.name.startswith("Needle")]
            self.assertEqual(len(needles),16)
            centres=sorted(set(round((max(t.x)+min(t.x))/2,8) for t in needles))
            np.testing.assert_allclose(np.diff(centres),[pitch]*3)
            self.assertEqual(len([t for t in fig.data if t.name=="Illustrative connected base"]),1)
            self.assertEqual(fig.layout.scene.aspectmode,"data")
            self.assertEqual(fig.layout.uirevision,studio_figure(Needle()).layout.uirevision)
        for bad in (replace(Needle(),shape="HalfCyl"),replace(Needle(),tip_width_um=0)):
            with self.assertRaises(ValueError): studio_figure(bad)

    def test_evidence_is_lazy_and_geometry_is_independent_of_material(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        self.assertFalse(app.tabs)
        self.assertFalse(any(s.key=='mts_run' for s in app.selectbox))
        self.assertFalse(any(s.key=='fea_inspector' for s in app.selectbox))
        app.number_input(key='pred_youngs_modulus_MPa').set_value(0).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Calculation unavailable' in e.value for e in app.error))
        self.assertGreater(len(app.get('plotly_chart')),0)
