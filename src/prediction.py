"""Uncalibrated small-strain structural estimates; mm/N/MPa internally.

Axial/bending flexibility integrates actual sections. Elastic buckling uses
a Rayleigh quotient. Contact and material failure forces are outside scope.
"""
from dataclasses import dataclass
import math
import numpy as np
from numpy.polynomial.legendre import Legendre, leggauss
from scipy.integrate import quad
from scipy.linalg import eigh
from scipy.optimize import minimize_scalar

MODEL_VERSION = "tapered-solid-1.0"
MESSAGE = "Literature-informed structural estimates available; independent validation pending"


@dataclass(frozen=True)
class PredictionAvailability:
    available: bool = True
    message: str = MESSAGE
    reason: str = "Linear elasticity and ideal beam stability only; no puncture, fracture or skin-penetration prediction."


def prediction_availability():
    return PredictionAvailability()


@dataclass(frozen=True)
class Needle:
    shape: str = "circular"
    length_um: float = 1000.0
    base_width_um: float = 200.0  # Diameter for circular sections.
    tip_width_um: float = 25.0
    base_depth_um: float = 200.0
    tip_depth_um: float = 25.0
    youngs_modulus_MPa: float = 3000.0
    yield_strength_MPa: float | None = None

    def validate(self):
        if self.shape not in ("circular", "rectangular"):
            raise ValueError("Supported sections are solid circular and centred rectangular tapers; HalfCyl is unsupported.")
        names = ["length_um", "base_width_um", "tip_width_um", "youngs_modulus_MPa"]
        if self.shape == "rectangular":
            names += ["base_depth_um", "tip_depth_um"]
        if any(not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0 for name in names):
            raise ValueError("Length, section dimensions and modulus must be finite and positive. Zero-area apices have singular axial compliance.")
        if self.tip_width_um > self.base_width_um or (self.shape == "rectangular" and self.tip_depth_um > self.base_depth_um):
            raise ValueError("Tip dimensions must not exceed the corresponding base dimensions.")
        if self.yield_strength_MPa is not None and (not math.isfinite(self.yield_strength_MPa) or self.yield_strength_MPa <= 0):
            raise ValueError("Optional yield strength must be finite and positive.")

    def section(self, t):
        """Root t=0, tip t=1. Return A, width/depth bending I, c values."""
        w = (self.base_width_um + (self.tip_width_um - self.base_width_um) * np.asarray(t)) / 1000
        if self.shape == "circular":
            area, inertia = np.pi * w**2 / 4, np.pi * w**4 / 64
            return area, inertia, inertia, w / 2, w / 2
        d = (self.base_depth_um + (self.tip_depth_um - self.base_depth_um) * np.asarray(t)) / 1000
        return w*d, d*w**3/12, w*d**3/12, w/2, d/2


def buckling_load(needle, plane, order):
    """Fixed-free dead-load beam eigenvalue: Ritz upper-bound estimate.

    s(t)=t*sum(a_i*P_i(2t-1)) enforces clamped-root rotation.
    Pcr=min integral(E I s_t^2)/[L^2 integral(s^2)]. Natural tip conditions
    follow from the energy principle. No equivalent-diameter shortcut.
    """
    nodes, weights = leggauss(max(64, 2*order+8))
    t, weights = (nodes+1)/2, weights/2
    slopes, derivatives = [], []
    for i in range(order):
        poly = Legendre.basis(i)
        slopes.append(t*poly(nodes))
        derivatives.append(poly(nodes)+2*t*poly.deriv()(nodes))
    slopes, derivatives = np.array(slopes), np.array(derivatives)
    inertia = needle.section(t)[1+plane]
    bending = (derivatives*(weights*needle.youngs_modulus_MPa*inertia)) @ derivatives.T
    geometric = (slopes*weights) @ slopes.T
    try:
        value = eigh(bending, geometric, subset_by_index=[0,0], check_finite=True)[0][0]
    except np.linalg.LinAlgError as exc:
        raise ValueError("Buckling eigensystem is unresolved; review section dimensions.") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("A positive elastic buckling eigenvalue could not be resolved.")
    return float(value/(needle.length_um/1000)**2)


def estimate(needle, axial_total_N=0.001, lateral_total_N=0.0,
             loaded_needles=1, eccentricity_um=0.0, bending_plane=0):
    needle.validate()
    if any(not math.isfinite(v) or v < 0 for v in (axial_total_N, lateral_total_N, eccentricity_um)):
        raise ValueError("Compressive/transverse force and eccentricity must be finite and nonnegative.")
    if isinstance(loaded_needles, bool) or not isinstance(loaded_needles, (int,np.integer)) or loaded_needles < 1:
        raise ValueError("Loaded needle count must be a positive integer.")
    if bending_plane not in (0,1):
        raise ValueError("Bending plane must be width (0) or depth (1).")
    length, modulus = needle.length_um/1000, needle.youngs_modulus_MPa
    axial, lateral = axial_total_N/loaded_needles, lateral_total_N/loaded_needles
    moment = axial*eccentricity_um/1000
    def integrate(function):
        result, error = quad(function,0,1,epsabs=1e-12,epsrel=1e-9,limit=200)
        if not math.isfinite(result) or error > max(1e-11,abs(result)*1e-6):
            raise ValueError("Section-flexibility integration did not converge; review dimensions.")
        return result
    ca = length/modulus*integrate(lambda t: 1/needle.section(t)[0])
    cf = length**3/modulus*integrate(lambda t: (1-t)**2/needle.section(t)[1+bending_plane])
    cm = length**2/modulus*integrate(lambda t: (1-t)/needle.section(t)[1+bending_plane])
    lateral_mm = lateral*cf+moment*cm
    critical, changes = [], []
    for plane in (0,1):
        values = [buckling_load(needle,plane,order) for order in (8,16,24)]
        critical.append(values[-1])
        changes.append(abs(values[-2]-values[-1])/values[-1])
    pcr = min(critical)
    def stress(t):
        area, iw, id_, cw, cd = needle.section(t)
        inertia, extreme = (iw,cw) if bending_plane == 0 else (id_,cd)
        return float(axial/area+(lateral*length*(1-t)+moment)*extreme/inertia)
    grid = np.linspace(0,1,1001)
    index = int(np.argmax([stress(t) for t in grid]))
    maximum = minimize_scalar(lambda t: -stress(t),bounds=(grid[max(0,index-1)],grid[min(1000,index+1)]),method="bounded")
    peak_stress, stress_location = max([(stress(0),0.0),(stress(1),1.0),(stress(maximum.x),float(maximum.x))])
    ratio, warnings = axial/pcr, []
    base_size = max(needle.base_width_um,needle.base_depth_um if needle.shape == "rectangular" else needle.base_width_um)
    if needle.length_um/base_size < 10:
        warnings.append("Short/thick needle: beam bending/buckling omits shear and 3D root/tip effects; use solid FEA for design decisions.")
    if max(changes) > 0.01:
        warnings.append("Buckling basis has not converged to 1%; this Ritz upper bound is unresolved and must not be used as a capacity.")
    if ratio >= 1:
        warnings.append("Applied compression reaches/exceeds the ideal elastic bifurcation estimate; linear deformation is outside its stable-use range.")
    elif ratio >= 0.1:
        warnings.append("Compression exceeds 10% of the elastic buckling indicator; omitted second-order bending may be significant.")
    if peak_stress/modulus > 0.01 or axial*ca/length > 0.01 or lateral_mm/length > 0.05:
        warnings.append("Small-strain/small-deflection screening limit exceeded; linear estimates require nonlinear review.")
    if needle.yield_strength_MPa is not None and peak_stress >= needle.yield_strength_MPa:
        warnings.append("Nominal stress reaches/exceeds supplied yield strength; linear elasticity is outside its material range. No failure force is predicted.")
    if min(needle.tip_width_um/needle.base_width_um,needle.tip_depth_um/needle.base_depth_um if needle.shape == "rectangular" else 1) < 0.02:
        warnings.append("Very small terminal section: results are sensitive to tip metrology and local contact; no point-apex regularisation is inferred.")
    return {
        "model_version": MODEL_VERSION,
        "axial_per_needle_N": axial,"lateral_per_needle_N": lateral,
        "axial_deformation_um": axial*ca*1000,
        "needle_axial_stiffness_N_per_mm": 1/ca,
        "array_axial_stiffness_N_per_mm": loaded_needles/ca,
        "lateral_deformation_um": lateral_mm*1000,"lateral_stiffness_N_per_mm": 1/cf,
        "elastic_buckling_indicator_N_per_needle": pcr,
        "buckling_width_N": critical[0],"buckling_depth_N": critical[1],
        "buckling_basis_relative_change": max(changes),"compression_to_buckling_ratio": ratio,
        "nominal_peak_normal_stress_MPa": peak_stress,
        "stress_location_from_root_um": stress_location*needle.length_um,
        "yield_ratio": peak_stress/needle.yield_strength_MPa if needle.yield_strength_MPa else None,
        "warnings": warnings,
    }
