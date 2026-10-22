"""Optional A/B workspace, using the existing analytical engine without changes."""
from dataclasses import asdict
import json

import streamlit as st

from src.prediction import Needle
from src.comparison import comparison_figure, comparison_table, dimensions, interactive_html


def geometry_inputs(label, prefix):
    defaults = asdict(Needle())
    # Seed A from the current single design once; B starts as a copy of A.
    for field in defaults:
        source = f"pred_{field}" if prefix == "compare_a" else f"compare_a_{field}"
        st.session_state.setdefault(f"{prefix}_{field}", st.session_state.get(source, defaults[field]))
    st.markdown(f"#### Design {label}")
    shape = st.segmented_control(f"Section {label}", ["circular", "rectangular"],
                                 key=f"{prefix}_shape", format_func=str.title)
    def dim(text, field, column):
        with column:
            return st.number_input(text, min_value=0., format="%g", key=f"{prefix}_{field}")
    cols = st.columns(3)
    length = dim("Height (µm)", "length_um", cols[0])
    width = dim("Base diameter (µm)" if shape == "circular" else "Base width (µm)", "base_width_um", cols[1])
    tip = dim("Tip diameter (µm)" if shape == "circular" else "Tip width (µm)", "tip_width_um", cols[2])
    depth, tip_depth = width, tip
    if shape == "rectangular":
        cols = st.columns(2)
        depth = dim("Base depth (µm)", "base_depth_um", cols[0])
        tip_depth = dim("Tip depth (µm)", "tip_depth_um", cols[1])
    return Needle(shape, length, width, tip, depth, tip_depth)


def render_comparison():
    from dataclasses import replace
    from src.prediction_view import cached_estimate

    st.caption("Independent geometry · shared material and loads · signed differences relative to Design A")
    a_col, b_col = st.columns(2, gap="large")
    with a_col:
        a = geometry_inputs("A", "compare_a")
    with b_col:
        b = geometry_inputs("B", "compare_b")
    with st.expander("Shared material and loading · change conditions", expanded=False):
        st.caption("These conditions apply to both designs. All values are explicit user assumptions. Clamped root, free tip; equal sharing across loaded needles.")
        fields = [("Young's modulus (MPa)", "youngs_modulus_MPa", 3000.),
                  ("Total compressive force (N)", "axial", .001),
                  ("Total transverse tip force (N)", "lateral", 0.),
                  ("Axial tip-load eccentricity (µm)", "eccentricity", 0.)]
        values = {}
        cols = st.columns(2)
        for i,(label,field,default) in enumerate(fields):
            key = f"compare_shared_{field}"
            st.session_state.setdefault(key, st.session_state.get(f"pred_{field}", default))
            with cols[i%2]:
                values[field] = st.number_input(label, min_value=0., format="%g", key=key)
        count = st.number_input("Loaded needles (both designs)", min_value=1,
                                value=int(st.session_state.get("pred_count",1)), step=1, key="compare_count")
        plane = st.selectbox("Bending plane (both designs)", [0,1],
                             format_func=lambda p: "Width direction" if p==0 else "Depth direction", key="compare_plane")
    a, b = [replace(n, youngs_modulus_MPa=values["youngs_modulus_MPa"]) for n in (a,b)]
    controls = st.columns([3,1,1])
    with controls[0]:
        view = st.segmented_control("Comparison view", ["Single needle", "4 × 4 array"], default="Single needle", key="compare_view")
    with controls[1]:
        wire = st.checkbox("Wireframe", key="compare_wire")
    with controls[2]:
        dark = st.toggle("Dark geometry", key="compare_dark")
    pitch = 600.
    if view == "4 × 4 array":
        with st.expander("Array display settings"):
            pitch = st.number_input("Shared array pitch (µm)", min_value=1., value=600., key="compare_pitch")
        st.caption("16 needles per display; illustrative connected base. Loaded count controls force sharing independently. No base compliance or array interaction is solved.")
        if pitch < max(a.base_width_um,a.base_depth_um,b.base_width_um,b.base_depth_um):
            st.warning("Base footprints overlap at this pitch; interactions are outside this model.")
    results = []
    for label, needle, col in (("A",a,a_col),("B",b,b_col)):
        with col:
            st.caption(dimensions(needle))
        try:
            result = cached_estimate(needle,values["axial"],values["lateral"],int(count),values["eccentricity"],plane)
        except (ValueError,ArithmeticError) as exc:
            st.error(f"Design {label} calculation unavailable: {exc}")
            result = None
        results.append(result)
    figure = None
    try:
        figure = comparison_figure(a,b,array=view=="4 × 4 array",pitch=pitch,wireframe=wire,dark=dark)
        st.iframe(interactive_html(figure,"microneedle-compare-camera-v1"),height=565)
        st.caption("Equal physical scales and linked cameras · Drag to rotate · Scroll to zoom · Camera icon exports a 2400 × 1400 PNG")
    except ValueError as exc:
        st.info(f"Comparison geometry unavailable: {exc}")
    st.markdown("#### Analytical comparison")
    st.caption(f"Shared E = {values['youngs_modulus_MPa']:g} MPa · Compression {values['axial']:g} N · Transverse {values['lateral']:g} N · {int(count)} loaded needle(s) · Eccentricity {values['eccentricity']:g} µm · {'Width' if plane==0 else 'Depth'} bending")
    table = comparison_table(*results)
    st.dataframe(table.style.format({c:"{:.5g}" for c in table.columns[1:]},na_rep="—"),hide_index=True,width="stretch")
    st.caption("Δ = B − A; percentage = 100 × (B − A) / |A|. — means unavailable or a zero A baseline. Differences describe response, not performance rankings.")
    st.caption("Unvalidated first-order elastic estimates. Buckling is an ideal elastic screening indicator, not a certified capacity. No fracture, skin penetration, contact, base compliance or second-order response is modelled. Stored FEA/MTS evidence does not validate these designs.")
    with st.expander("Applicability and additional outputs"):
        for label, result in zip(("A","B"),results):
            st.markdown(f"**Design {label}**")
            if result:
                st.write(f"Compression / buckling indicator: {result['compression_to_buckling_ratio']:.5g}")
                for warning in result["warnings"]:
                    st.write(warning)
                st.caption(f"16 → 24 term basis change: {100*result['buckling_basis_relative_change']:.4g}%. Numerical convergence is not physical validation.")
            else:
                st.write("Calculation unavailable; review inputs.")
    with st.expander("Presentation export"):
        st.caption("Download the standalone figure, open it in a browser and use its camera icon for a high-resolution PNG. Both models export together. The HTML includes dimensions and conditions; PNG contains the paired geometry. Camera state is retained in this browser where storage is available.")
        if figure is not None:
            caption = (f"Design A: {dimensions(a)} | Design B: {dimensions(b)} | "
                       f"Shared E={values['youngs_modulus_MPa']:g} MPa; axial={values['axial']:g} N; transverse={values['lateral']:g} N; loaded={count}; eccentricity={values['eccentricity']:g} µm; plane={plane}. Unvalidated analytical model.")
            st.download_button("Download comparison figure (HTML)",interactive_html(figure,"microneedle-compare-export-v1",caption=caption),
                               file_name="microneedle_comparison.html",mime="text/html",key="compare_html",on_click="ignore")
        st.download_button("Download comparison values (CSV)",table.to_csv(index=False),file_name="microneedle_comparison.csv",mime="text/csv",key="compare_csv",on_click="ignore")
        report = {"design_a":asdict(a),"design_b":asdict(b),"shared_conditions":dict(values,loaded_needles=int(count),bending_plane=plane),
                  "results_a":results[0],"results_b":results[1],"evidence":"Unvalidated analytical estimates; no FEA validation implied"}
        st.download_button("Download comparison report (JSON)",json.dumps(report,indent=2),file_name="microneedle_comparison.json",mime="application/json",key="compare_json",on_click="ignore")
