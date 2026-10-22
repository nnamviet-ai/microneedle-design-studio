"""Streamlit controls for user-defined designs and structural estimates."""
from dataclasses import asdict
import hashlib
import json

import pandas as pd
import streamlit as st
from src.comparison import interactive_html

from src.prediction import Needle, estimate
from src.prediction_figures import geometry_figure, response_figure
from src.paths import ROOT
from src.geometry_3d import studio_figure


@st.cache_data(show_spinner=False)
def cached_estimate(needle, axial, lateral, count, eccentricity, plane):
    return estimate(needle,axial,lateral,count,eccentricity,plane)


def render_prediction_dashboard():
    choices = ["New user-defined design"]
    left,centre,right = st.columns([1.15,2.35,1.3],gap="medium")
    with left:
        st.markdown("#### Design configuration")
        preset_column = st.container()
        with preset_column:
            preset = st.selectbox("Starting design",choices,index=0, disabled=True,key="pred_preset")
    defaults = asdict(Needle())
    if st.session_state.get("pred_initialised") != preset:
        for key, value in defaults.items():
            if key not in ("shape",):
                st.session_state[f"pred_{key}"] = value if value is not None else 0.0
        st.session_state["pred_use_yield"] = defaults.get("yield_strength_MPa") is not None
        st.session_state["pred_material"] = "User-supplied elastic material"
        st.session_state["pred_shape"] = "circular"
        st.session_state["pred_initialised"] = preset
    with left:
        with st.container():
            shape = st.radio("Needle shape",["circular","rectangular"],
                             format_func=str.title,horizontal=True,key="pred_shape")
        def dimension(label,field):
            return st.number_input(label,min_value=0.0,format="%g",key=f"pred_{field}")
        a,b = st.columns(2,gap="small")
        with a:
            length = dimension("Needle height (µm)","length_um")
        with b:
            width = dimension("Base diameter (µm)" if shape=="circular" else "Base width (µm)","base_width_um")
        with a:
            tip = dimension("Tip diameter (µm)" if shape=="circular" else "Tip width (µm)","tip_width_um")
        with b:
            pitch = st.number_input("Array pitch (µm)",min_value=1.0,value=600.0,format="%g",key="pred_pitch")
        depth,tip_depth = width,tip
        if shape=="rectangular":
            if "pred_base_depth_um" not in st.session_state:
                st.session_state["pred_base_depth_um"] = 200.0
                st.session_state["pred_tip_depth_um"] = 25.0
            a,b = st.columns(2,gap="small")
            with a:
                depth = dimension("Base depth (µm)","base_depth_um")
            with b:
                tip_depth = dimension("Tip depth (µm)","tip_depth_um")
        material_choices = ["User-supplied elastic material"]
        st.selectbox("Material",material_choices,key="pred_material")
        modulus = dimension("Young's modulus (MPa)","youngs_modulus_MPa")
        a,b = st.columns(2,gap="small")
        with a:
            axial = st.number_input("Total compressive force (N)",min_value=0.0,value=0.001,format="%g",key="pred_axial")
        with b:
            count = st.number_input("Loaded needles",min_value=1,value=1,step=1,key="pred_count")
        st.caption("Centre-to-centre · 4 × 4 arrangement. Loaded count controls equal force sharing independently.")
        with st.expander("Advanced loading and material settings",expanded=False):
            with st.container():
                scenario = st.selectbox("Loading scenario",["Uniform load sharing","Reduced needle contact","Eccentric loading"],key="pred_scenario")
            st.caption("Dimensions, elastic modulus, strength and loads are user assumptions. Defaults are illustrative inputs, not measured engineering results.")
            st.caption("Force is shared equally across the selected loaded needles. Reduced contact uses the same equations with fewer needles; eccentricity is a per-needle tip offset.")
            a,b = st.columns(2)
            with a:
                lateral = st.number_input("Total transverse tip force (N)",min_value=0.0,value=0.0,format="%g",key="pred_lateral")
            with b:
                eccentricity = st.number_input("Axial tip-load eccentricity (µm)",min_value=0.0,value=0.0,format="%g",key="pred_eccentricity")
            plane = st.selectbox("Bending plane",[0,1],format_func=lambda p:"Width direction" if p==0 else "Depth direction",key="pred_plane")
            use_yield = st.checkbox("Screen nominal stress against a supplied yield strength",key="pred_use_yield")
            yield_strength = dimension("Yield strength (MPa)","yield_strength_MPa") if use_yield else None
            st.caption("Enable screening only with an explicitly supplied strength. No custom material strength is inferred.")
            st.caption("Boundary condition: clamped needle root, free tip. Tip force/eccentric moment act in the selected plane and reinforce one another. Loads are user scenarios, not literature measurements.")
            st.caption("Numerical settings are fixed by the existing model: adaptive quadrature and nested 8/16/24-term Ritz bases.")
        if scenario=="Eccentric loading" and eccentricity==0:
            st.caption("Set a nonzero tip-load eccentricity in advanced settings to apply an eccentric moment.")
        if lateral or eccentricity:
            st.caption(f"Active additional loads: transverse {lateral:.4g} N; eccentricity {eccentricity:.4g} µm. These remain active in every scenario.")
    needle = Needle(shape,length,width,tip,depth,tip_depth,modulus,yield_strength)
    with centre:
        st.markdown("#### Geometry workspace")
        a,b,c = st.columns([2,1,1],gap="small")
        with a:
            view = st.segmented_control("View",["Single needle","4 × 4 array"],default="Single needle",key="studio_view",label_visibility="collapsed")
        with b:
            wireframe = st.checkbox("Wireframe",key="studio_wire")
        with c:
            dark = st.toggle("Dark",key="studio_dark")
        try:
            figure = studio_figure(needle,array=view=="4 × 4 array",pitch=pitch,wireframe=wireframe,dark=dark)
            with st.container(key="pred_preview"):
                st.iframe(interactive_html(figure,"microneedle-single-camera-v1"),height=485)
            st.caption(f"Height {length:g} µm · Base {width:g}" + (f" × {depth:g}" if shape=="rectangular" else " diameter") + f" µm · Tip {tip:g}" + (f" × {tip_depth:g}" if shape=="rectangular" else " diameter") + " µm")
            if view=="4 × 4 array":
                st.caption(f"16 needles · {pitch:g} µm pitch · Connected base is illustrative; no base compliance or array interaction is solved.")
                if pitch < max(width,depth):
                    st.caption("Review: base footprints overlap at this pitch; interactions are outside this model.")
            st.caption("Drag to rotate · Scroll to zoom · Right-drag to pan · Camera icon exports PNG")
            with st.expander("Dimension diagram and presentation export"):
                st.caption("Camera orientation is retained in this browser where storage is available. HTML export retains interactive camera controls.")
                st.plotly_chart(geometry_figure(needle),width="stretch",key="studio_dimensions")
                st.download_button("Download interactive 3D HTML",lambda: figure.to_html(include_plotlyjs=True).encode("utf-8"),file_name="microneedle_geometry.html",mime="text/html",key="studio_html",on_click="ignore")
        except ValueError as exc:
            st.info(f"Geometry preview unavailable: {exc}")
    input_sources = {field: "User-entered design assumption" for field in asdict(needle)}
    with right:
        st.markdown("#### Predicted structural response")
        try:
            result = cached_estimate(needle,axial,lateral,int(count),eccentricity,plane)
        except (ValueError,ArithmeticError) as exc:
            st.error(f"Calculation unavailable: {exc}")
            result = None
        if result:
            a,b = st.columns(2,gap="small")
            a.metric("Estimated axial compression (µm)",f"{result['axial_deformation_um']:.4g}")
            b.metric("Estimated lateral tip deflection (µm)",f"{result['lateral_deformation_um']:.4g}")
            a,b = st.columns(2,gap="small")
            a.metric("Needle axial stiffness (N/mm)",f"{result['needle_axial_stiffness_N_per_mm']:.4g}")
            b.metric("Elastic buckling indicator (N/needle)",f"{result['elastic_buckling_indicator_N_per_needle']:.4g}")
            with st.expander("Nominal stress and additional outputs"):
                st.markdown(f"**Compression / buckling:** {result['compression_to_buckling_ratio']:.4g}  ·  **Nominal stress:** {result['nominal_peak_normal_stress_MPa']:.4g} MPa")
                if result['yield_ratio'] is not None:
                    st.caption(f"Stress / supplied yield: {result['yield_ratio']:.4g}")
                st.caption(f"Per-needle compression {result['axial_per_needle_N']:.4g} N · Transverse force {result['lateral_per_needle_N']:.4g} N · Array stiffness {result['array_axial_stiffness_N_per_mm']:.4g} N/mm")
            with st.container():
                st.markdown("**Engineering interpretation**")
                st.caption(f"Estimated shortening: {100*result['axial_deformation_um']/length:.3g}% of height; lateral motion: {result['lateral_deformation_um']:.4g} µm in the {'width' if plane==0 else 'depth'} direction. {len(result['warnings'])} applicability review trigger(s); see details below.")
                st.caption("First-order elastic screen with equal load sharing. Buckling and yield ratios are screening indicators; no fracture or skin penetration prediction. A low ratio does not establish safety.")
            with st.expander("Axial response plot",expanded=False):
                st.plotly_chart(response_figure(result,axial,int(count)),width="stretch",key="pred_response",config={"displaylogo":False})
                st.caption("First-order axial response from integrated section compliance. The line shows the equation, including any loads outside its applicability; it does not establish physical stability or material validity.")
            with st.expander("Detailed engineering interpretation",expanded=False):
                st.write(f"Under {axial:.4g} N shared by {int(count)} needle(s), estimated shortening is {result['axial_deformation_um']:.4g} µm ({100*result['axial_deformation_um']/length:.3g}% of height). Each needle's axial stiffness is {result['needle_axial_stiffness_N_per_mm']:.4g} N/mm.")
                st.write(f"The selected transverse force and eccentric moment produce {result['lateral_deformation_um']:.4g} µm lateral tip displacement in the {'width' if plane==0 else 'depth'} direction. This first-order bending estimate omits shear and second-order effects.")
                st.write(f"Compression / ideal elastic buckling indicator: {result['compression_to_buckling_ratio']:.4g}. This is a susceptibility screen, not a certified capacity or fracture criterion.")
                st.write(f"Nominal peak normal stress: {result['nominal_peak_normal_stress_MPa']:.4g} MPa at {result['stress_location_from_root_um']:.4g} µm from the root.")
                if result['yield_ratio'] is not None:
                    st.write(f"Nominal stress / supplied yield strength: {result['yield_ratio']:.4g} (material-range screen only).")
            with st.expander(f"Quality and applicability · {len(result['warnings'])} review trigger(s)",expanded=False):
                for warning in result["warnings"]:
                    st.write("• " + warning)
                st.caption(f"Ritz basis change, 16 → 24 terms: {100*result['buckling_basis_relative_change']:.4g}%. Numerical convergence is not physical validation.")
                st.dataframe(pd.DataFrame([{"Quantity":k,"Value":str(v)} for k,v in result.items() if k!='warnings']),hide_index=True,width="stretch")
            report = {"inputs":asdict(needle),"input_sources":input_sources,
                      "loading":{"total_compression_N":axial,"total_transverse_N":lateral,"loaded_needles":int(count),"eccentricity_um":eccentricity,"bending_plane":plane},
                      "estimates":result,"assumptions":"Homogeneous uncoated elastic core; straight linear taper; finite tip; clamped root/free tip; equal load sharing; no shear, base compliance, contact, plasticity or second-order response",
                      "code_sha256":hashlib.sha256((ROOT/"src/prediction.py").read_bytes()).hexdigest(),
                      "evidence":"Unvalidated model; numerical convergence is not physical validation; all loading user-proposed",
                      "registered_references":[]}
            st.download_button("Calculation report (JSON)",json.dumps(report,indent=2),file_name="structural_estimate.json",mime="application/json",key="pred_report")
        with st.expander("Assumptions and limitations"):
            st.caption("No recorded FEA or experimental observations are included in this deployment.")
            st.write("Homogeneous uncoated core; straight centred sections; linear elastic, quasi-static response. No machine or substrate compliance, coating stiffness, skin contact or penetration model.")
            st.write("Homogeneous, uncoated, linear-elastic core with a straight linear taper and finite tip. Clamped root, free tip and equal load sharing. Short columns, imperfections, plasticity and local damage require separate assessment. No substrate compliance, contact, skin or second-order deformation model. HalfCyl, hollow, curved and layered/coated sections are unsupported.")
        with st.expander("Calculation method",expanded=False):
            st.latex(r"\delta_a=P\int_0^L\frac{dz}{E A(z)},\qquad k_a=\left[\int_0^L\frac{dz}{E A(z)}\right]^{-1}")
            st.latex(r"\delta_b=\int_0^L\frac{[F_t(L-z)+Pe](L-z)}{E I(z)}\,dz")
            st.latex(r"P_{cr}=\min_s\frac{\int_0^L E I(z)[s'(z)]^2dz}{\int_0^L s(z)^2dz},\quad s(0)=0")
            st.write("Diameter or width/depth changes linearly from root to finite tip. Circular A=πd²/4, I=πd⁴/64; rectangular A=wh, I=hw³/12 or wh³/12. Constant-section solutions arise only when both endpoint sections match.")
            st.write("Adaptive quadrature uses the actual A(z), I(z). Fixed-free buckling uses nested Legendre slope spaces (8, 16, 24 terms), exact polynomial Gauss integration and the weaker of two bending directions. No fitted equivalent diameter, plasticity or P–Δ response is supplied.")
            st.caption("The 10% buckling, 1% strain, 5% lateral-deflection and length/base <10 warnings are review triggers chosen for this implementation, not universal literature failure criteria. HalfCyl, hollow, curved and layered/coated sections are unsupported.")
        with st.expander("Input provenance",expanded=False):
            inputs = []
            for field,value in asdict(needle).items():
                source = input_sources[field]
                inputs.append({"Input":field,"Value":str(value),"Origin":source})
            st.dataframe(pd.DataFrame(inputs),hide_index=True,width="stretch")

    with st.expander("Evidence availability", expanded=False):
        st.info("Recorded FEA/MTS results, registered geometries, literature presets and workbook provenance are not included in this public deployment. Calculations use user-entered assumptions and are not independently validated.")
