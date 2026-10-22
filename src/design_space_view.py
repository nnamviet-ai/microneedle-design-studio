"""Opt-in sweep UI with immutable run snapshots and explicit candidate transfer."""
from dataclasses import asdict
from datetime import datetime, timezone
import json

import streamlit as st

from src.prediction import Needle
from src.comparison import dimensions
from src.design_space import (FIELDS, METRICS, ASSUMPTIONS, SweepAxis, supported_fields,
                              sweep, sensitivity_figure, figure_html)


def baseline_from_state(state, source):
    """Read either active widgets or saved workspace values without editing them."""
    compare = source != "Single design"
    mode = "comparison" if compare else "single"
    values = dict(state.get(f"studio_saved_{mode}",{}))
    values.update(dict(state))
    prefix = "compare_a" if source=="Design A" else "compare_b" if compare else "pred"
    inputs = {key:values.get(f"{prefix}_{key}",default) for key,default in asdict(Needle()).items()}
    if compare:
        inputs["youngs_modulus_MPa"] = values.get("compare_shared_youngs_modulus_MPa",3000.)
        inputs["yield_strength_MPa"] = None
    elif not values.get("pred_use_yield",False):
        inputs["yield_strength_MPa"] = None
    if inputs["shape"]=="circular":
        inputs.update(base_depth_um=inputs["base_width_um"],tip_depth_um=inputs["tip_width_um"])
    needle = Needle(**inputs)
    def load(field, default):
        key = (f"compare_{field}" if field in ("count","plane") else f"compare_shared_{field}") if compare else f"pred_{field}"
        return values.get(key,default)
    loading = dict(axial_total_N=load("axial",.001), lateral_total_N=load("lateral",0.),
                   loaded_needles=load("count",1), eccentricity_um=load("eccentricity",0.),bending_plane=load("plane",0))
    return needle, loading


@st.cache_data(show_spinner=False,max_entries=8)
def cached_sweep(needle, axes, loading):
    return sweep(needle,axes,loading)


def load_candidate(row, switch_workspace):
    """Button callback runs before studio widgets are instantiated on the next run."""
    if row["status"]!="estimated":
        raise ValueError("Rejected candidates cannot be transferred.")
    if st.session_state.get("studio_compare",False):
        st.session_state.studio_compare = False
        switch_workspace()
    for field in asdict(Needle()):
        value = row[field]
        st.session_state[f"pred_{field}"] = value if value is not None else 0.
    preset = "New user-defined design"
    st.session_state.update(pred_preset=preset,pred_initialised=preset,
                            pred_material="User-supplied elastic material",
                            pred_use_yield=row["yield_strength_MPa"] is not None)
    for field, key in (("axial_total_N","axial"),("lateral_total_N","lateral"),
                       ("loaded_needles","count"),("eccentricity_um","eccentricity"),("bending_plane","plane")):
        st.session_state[f"pred_{key}"] = int(row[field]) if key in ("count","plane") else float(row[field])
    st.session_state["space_transfer_notice"] = f"Candidate {int(row['candidate_id'])} loaded into the single-design studio with its fixed sweep conditions."


def render_design_space(switch_workspace):
    with st.expander("Design Space Explorer · analytical screening",expanded=False):
        if not st.checkbox("Enable design space exploration",key="space_enabled"):
            return
        st.caption("Unvalidated analytical screening, not a geometry optimiser. Capture the current studio design and fixed conditions when running a sweep. Array pitch is excluded: the model has no pitch-dependent structural response.")
        source = st.selectbox("Sweep starting design",["Single design","Design A","Design B"],key="space_source")
        needle, loading = baseline_from_state(st.session_state,source)
        st.caption(dimensions(needle))
        with st.expander("Fixed inputs and assumptions"):
            st.json(dict(geometry=asdict(needle),loading=loading))
            st.write(ASSUMPTIONS)
        fields = supported_fields(needle)
        cols = st.columns(2)
        with cols[0]:
            first = st.selectbox("Sweep parameter",fields,format_func=FIELDS.get,key=f"space_x_{needle.shape}")
        with cols[1]:
            second = st.selectbox("Second parameter",[None]+[f for f in fields if f!=first],
                                  format_func=lambda f: "None · 1D sensitivity" if f is None else FIELDS[f],key=f"space_y_{needle.shape}_{first}")
        axes = []
        with st.form("space_bounds"):
            for field in [first]+([second] if second else []):
                cols = st.columns([2,2,1])
                value = getattr(needle,field)
                with cols[0]:
                    lo = st.number_input(FIELDS[field]+" · minimum",min_value=0.,value=float(value*.75),key=f"space_min_{field}")
                with cols[1]:
                    hi = st.number_input(FIELDS[field]+" · maximum",min_value=0.,value=float(value*1.25),key=f"space_max_{field}")
                with cols[2]:
                    count = st.number_input("Samples",min_value=2,max_value=25,value=7,step=1,key=f"space_n_{field}")
                axes.append(SweepAxis(field,lo,hi,int(count)))
            st.caption("Uniform samples; maximum 225 candidates. Material, force, contact count, eccentricity, bending direction and all other dimensions stay fixed within each run. Edit these in the studio before running again.")
            run = st.form_submit_button("Run analytical sweep",key="space_run")
        if run:
            try:
                with st.spinner("Evaluating existing analytical model…"):
                    frame = cached_sweep(needle,tuple(axes),loading)
                manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),source=source,
                                baseline=asdict(needle),loading=loading,axes=[asdict(a) for a in axes],
                                assumptions=ASSUMPTIONS,model_version=frame.model_version.iloc[0],
                                engine_sha256=frame.engine_sha256.iloc[0])
                frame["created_utc"] = manifest["created_utc"]
                frame["starting_design"] = source
                st.session_state.space_result = dict(frame=frame,axes=axes,manifest=manifest)
                st.session_state.space_run_id = st.session_state.get("space_run_id",0)+1
                st.session_state.pop("space_candidate",None)
            except (ValueError,ArithmeticError) as exc:
                st.error(f"Sweep unavailable: {exc}")
                st.session_state.pop("space_result",None)
        result = st.session_state.get("space_result")
        if not result:
            return
        frame, axes, manifest = result["frame"],result["axes"],result["manifest"]
        valid = frame.loc[frame.status.eq("estimated")]
        st.caption(f"Last completed run: {manifest['source']} · {len(valid)} estimated / {len(frame)} sampled · {manifest['created_utc']}. Inputs above affect results only after Run analytical sweep.")
        if len(valid)!=len(frame):
            st.warning(f"{len(frame)-len(valid)} combinations rejected; gaps have no predictions and cannot be selected.")
            with st.expander("Rejected combinations"):
                st.dataframe(frame.loc[frame.status.eq("rejected"),[a.field for a in axes]+["rejection_reason"]],hide_index=True)
        if valid.empty:
            st.error("No valid candidates. Review the bounds and fixed geometry.")
        metric = next(iter(METRICS))
        if len(axes)==2:
            metric = st.selectbox("Heatmap response",list(METRICS),format_func=METRICS.get,key="space_metric")
        figure = sensitivity_figure(frame,axes,metric)
        fixed = manifest["loading"]
        summary = (f"Fixed E={manifest['baseline']['youngs_modulus_MPa']:g} MPa · "
                   f"axial={fixed['axial_total_N']:g} N · transverse={fixed['lateral_total_N']:g} N · "
                   f"loaded={fixed['loaded_needles']} · eccentricity={fixed['eccentricity_um']:g} µm · "
                   f"{'width' if fixed['bending_plane']==0 else 'depth'} bending")
        figure.update_layout(title_text=figure.layout.title.text+"<br><sup>"+summary+"</sup>",margin=dict(t=100))
        event = st.plotly_chart(figure,width="stretch",key=f"space_plot_{st.session_state.space_run_id}_{metric}",
                               on_select="rerun",selection_mode="points",
                               config={"displaylogo":False,"toImageButtonOptions":{"format":"png","filename":"microneedle_design_space","width":2600,"height":1800,"scale":1}})
        st.caption("Click a curve marker or heatmap dot to inspect a sampled candidate. Heatmap shading summarises grid samples; it is not an evaluated continuous surface. Gaps are rejected designs. No candidates are ranked.")
        if not valid.empty:
            points = event.selection.points if hasattr(event,"selection") else []
            token = (st.session_state.space_run_id,metric,repr(points))
            if points and st.session_state.get("space_selection_event") != token:
                selected = points[-1].get("customdata")
                if selected in valid.candidate_id.values:
                    st.session_state.space_candidate = int(selected)
            st.session_state.space_selection_event = token
            ids = [int(i) for i in valid.candidate_id]
            if st.session_state.get("space_candidate") not in ids:
                st.session_state.space_candidate = ids[0]
            candidate_id = st.selectbox("Selected candidate",ids,key="space_candidate",
                format_func=lambda i: f"Candidate {i} · "+" · ".join(f"{FIELDS[a.field]}: {frame.loc[frame.candidate_id.eq(i),a.field].iloc[0]:g}" for a in axes))
            row = frame.loc[frame.candidate_id.eq(candidate_id)].iloc[0].to_dict()
            # pandas can represent an absent optional strength as NaN.
            if not manifest["baseline"]["yield_strength_MPa"]:
                row["yield_strength_MPa"] = None
            st.caption(dimensions(Needle(**{f:row[f] for f in asdict(Needle())})))
            cols = st.columns(4)
            for col,(key,label) in zip(cols,METRICS.items()):
                col.metric(label,f"{row[key]:.5g}")
            if row["warnings"]:
                st.warning("Applicability review: "+row["warnings"])
            st.button("Load candidate into 3D Design Studio",key="space_apply",on_click=load_candidate,args=(row,switch_workspace))
            st.caption("Transfers the selected dimensions and fixed sweep material/loading conditions to the single-design studio. A/B designs are preserved.")
        with st.expander("Sweep data and presentation export"):
            st.caption("Camera icon exports a 2600 × 1800 PNG. Standalone HTML includes interactive figures and the full input manifest; CSV records every candidate, fixed inputs, rejections, warnings, assumptions and engine hash.")
            st.download_button("Download sweep CSV",frame.to_csv(index=False),file_name="design_space.csv",mime="text/csv",key="space_csv",on_click="ignore")
            st.download_button("Download sensitivity figure (HTML)",figure_html(figure,manifest),file_name="design_space.html",mime="text/html",key="space_html",on_click="ignore")
            st.download_button("Download sweep inputs (JSON)",json.dumps(manifest,indent=2),file_name="design_space_inputs.json",mime="application/json",key="space_json",on_click="ignore")
