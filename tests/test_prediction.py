"""Original engine regressions against closed-form analytical solutions."""
from dataclasses import replace
import math
import numpy as np
from unittest import TestCase
from src.prediction import Needle, estimate, buckling_load


class PredictionTests(TestCase):
    def test_uniform_cylinder_axial_bending_eccentricity_and_euler_limits(self):
        needle = Needle(length_um=2000,base_width_um=100,tip_width_um=100,youngs_modulus_MPa=3000)
        result = estimate(needle,axial_total_N=0.0001,lateral_total_N=0.0002,eccentricity_um=10)
        length,d,e = 2,0.1,3000
        area,inertia = math.pi*d*d/4,math.pi*d**4/64
        self.assertAlmostEqual(result['axial_deformation_um'],0.0001*length/(e*area)*1000,places=10)
        expected = (0.0002*length**3/(3*e*inertia)+0.0001*0.01*length**2/(2*e*inertia))*1000
        self.assertAlmostEqual(result['lateral_deformation_um'],expected,places=9)
        euler = math.pi**2*e*inertia/(4*length**2)
        self.assertLess(abs(result['elastic_buckling_indicator_N_per_needle']/euler-1),1e-7)

    def test_tapered_circle_closed_form_compliance(self):
        needle = Needle()
        result = estimate(needle,lateral_total_N=0.00001)
        length,db,dt,e = 1,0.2,0.025,3000
        self.assertAlmostEqual(result['needle_axial_stiffness_N_per_mm'],math.pi*e*db*dt/(4*length),places=9)
        flexibility = 64*length**3/(3*math.pi*e*db**3*dt)
        self.assertAlmostEqual(result['lateral_deformation_um'],0.00001*flexibility*1000,places=9)
        uniform = estimate(replace(needle,tip_width_um=needle.base_width_um))
        self.assertGreater(result['axial_deformation_um'],uniform['axial_deformation_um'])
        self.assertLess(result['elastic_buckling_indicator_N_per_needle'],uniform['elastic_buckling_indicator_N_per_needle'])

    def test_rectangular_section_axes_and_nonproportional_taper(self):
        needle = Needle(shape='rectangular',base_width_um=100,tip_width_um=100,base_depth_um=200,tip_depth_um=200)
        width,depth,length,e = 0.1,0.2,1,3000
        first = estimate(needle,lateral_total_N=0.00001,bending_plane=0)
        second = estimate(needle,lateral_total_N=0.00001,bending_plane=1)
        self.assertAlmostEqual(first['needle_axial_stiffness_N_per_mm'],e*width*depth/length)
        self.assertAlmostEqual(first['lateral_deformation_um']/second['lateral_deformation_um'],4.0)
        expected = math.pi**2*e*depth*width**3/(48*length**2)
        self.assertLess(abs(first['elastic_buckling_indicator_N_per_needle']/expected-1),1e-7)
        taper = replace(needle,tip_width_um=20,tip_depth_um=100)
        result = estimate(taper)
        # Analytic partial-fraction integration of 1/[(a+bt)(c+dt)].
        a,b,c,d = 0.1,-0.08,0.2,-0.1
        integral = math.log((a+b)*c/(a*(c+d)))/(b*c-a*d)
        self.assertAlmostEqual(result['needle_axial_stiffness_N_per_mm'],e/integral,places=8)

    def test_array_load_sharing_and_material_scaling(self):
        needle = Needle()
        one = estimate(needle,axial_total_N=0.001)
        array = estimate(needle,axial_total_N=0.016,loaded_needles=16)
        self.assertAlmostEqual(array['axial_deformation_um'],one['axial_deformation_um'])
        self.assertAlmostEqual(array['array_axial_stiffness_N_per_mm'],16*one['needle_axial_stiffness_N_per_mm'])
        stiff = estimate(replace(needle,youngs_modulus_MPa=6000))
        self.assertAlmostEqual(stiff['axial_deformation_um'],one['axial_deformation_um']/2)
        self.assertAlmostEqual(stiff['elastic_buckling_indicator_N_per_needle'],2*one['elastic_buckling_indicator_N_per_needle'])

    def test_buckling_nested_basis_and_physical_bounds(self):
        needle = Needle()
        values = [buckling_load(needle,0,n) for n in (8,16,24)]
        self.assertTrue(all(a>=b-1e-10 for a,b in zip(values,values[1:])))
        self.assertLess(abs(values[-2]/values[-1]-1),0.01)
        length = needle.length_um/1000
        tip_i,base_i = needle.section(1)[1],needle.section(0)[1]
        self.assertGreater(values[-1],math.pi**2*needle.youngs_modulus_MPa*tip_i/(4*length**2))
        self.assertLess(values[-1],math.pi**2*needle.youngs_modulus_MPa*base_i/(4*length**2))

    def test_invalid_geometry_loads_and_point_apex_are_rejected(self):
        for needle in (Needle(tip_width_um=0),Needle(length_um=-1),Needle(shape='HalfCyl'),Needle(youngs_modulus_MPa=float('nan')),Needle(tip_width_um=500)):
            with self.subTest(needle=needle),self.assertRaises(ValueError):
                estimate(needle)
        for count in (0,1.5,True):
            with self.assertRaises(ValueError): estimate(Needle(),loaded_needles=count)
        with self.assertRaises(ValueError): estimate(Needle(),axial_total_N=float('inf'))
        with self.assertRaises(ValueError): estimate(Needle(),lateral_total_N=-1)

    def test_model_range_warnings_and_zero_load(self):
        zero = estimate(Needle(),axial_total_N=0)
        self.assertEqual(zero['axial_deformation_um'],0)
        self.assertEqual(zero['nominal_peak_normal_stress_MPa'],0)
        loaded = estimate(Needle(yield_strength_MPa=1),axial_total_N=1,lateral_total_N=0.1)
        warnings = ' '.join(loaded['warnings'])
        self.assertIn('outside its stable-use range',warnings)
        self.assertIn('yield strength',warnings)
        self.assertIn('nonlinear review',warnings)

    def test_peak_bending_stress_can_occur_inside_taper(self):
        needle = Needle(length_um=2000,base_width_um=200,tip_width_um=50)
        result = estimate(needle,axial_total_N=0,lateral_total_N=0.00001)
        self.assertGreater(result['stress_location_from_root_um'],0)
        self.assertLess(result['stress_location_from_root_um'],needle.length_um)
        t = result['stress_location_from_root_um']/needle.length_um
        expected = 0.00001*2*(1-t)*needle.section(t)[3]/needle.section(t)[1]
        self.assertAlmostEqual(result['nominal_peak_normal_stress_MPa'],expected)

