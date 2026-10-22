"""Bounded parameter sampling; all mechanics are delegated to prediction.estimate."""
from dataclasses import asdict, dataclass, replace
from itertools import product
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.prediction import Needle, estimate, MODEL_VERSION

FIELDS = {"length_um":"Height (µm)", "base_width_um":"Base diameter / width (µm)",
          "tip_width_um":"Tip diameter / width (µm)", "base_depth_um":"Base depth (µm)",
          "tip_depth_um":"Tip depth (µm)"}
METRICS = {"needle_axial_stiffness_N_per_mm":"Axial stiffness (N/mm/needle)",
           "axial_deformation_um":"Axial compression (µm)",
           "lateral_deformation_um":"Lateral displacement (µm)",
           "elastic_buckling_indicator_N_per_needle":"Buckling indicator (N/needle)"}
ASSUMPTIONS = ("Unvalidated analytical estimates; homogeneous uncoated linear-elastic solid; linear taper with finite tip; "
               "clamped root/free tip; equal load sharing; no contact, skin penetration, fracture, coating failure, "
               "plasticity, shear, base compliance, array interactions or second-order response. "
               "Lower displacement does not establish insertion effectiveness. No clinical or experimental ranking; no FEA validation.")


@dataclass(frozen=True)
class SweepAxis:
    field: str
    minimum: float
    maximum: float
    points: int

    def values(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.minimum,self.maximum)) or self.maximum <= self.minimum:
            raise ValueError("Sweep bounds must be finite, positive and increasing.")
        if isinstance(self.points,bool) or not isinstance(self.points,int) or not 2 <= self.points <= 25:
            raise ValueError("Use 2–25 samples per axis.")
        return np.linspace(self.minimum,self.maximum,self.points)


def supported_fields(needle):
    return list(FIELDS) if needle.shape=="rectangular" else list(FIELDS)[:3]


def sweep(needle, axes, loading):
    """Retain rejected grid locations as gaps, never interpolate invalid designs."""
    needle.validate()
    if len(axes) not in (1,2) or len({a.field for a in axes}) != len(axes):
        raise ValueError("Select one or two distinct parameters.")
    if any(a.field not in supported_fields(needle) for a in axes):
        raise ValueError("Unsupported sweep variable for this section; pitch has no structural effect in this model.")
    samples = [a.values() for a in axes]
    if math.prod(map(len,samples)) > 225:
        raise ValueError("Limit sweeps to 225 candidates to keep screening responsive.")
    # Validate the fixed loads once, including the engine's integer count checks.
    estimate(needle,**loading)
    rows = []
    for index, values in enumerate(product(*samples)):
        candidate = replace(needle,**dict(zip([a.field for a in axes],map(float,values))))
        if candidate.shape=="circular":
            candidate = replace(candidate,base_depth_um=candidate.base_width_um,tip_depth_um=candidate.tip_width_um)
        row = dict(candidate_id=index,**asdict(candidate),**loading)
        try:
            result = estimate(candidate,**loading)
            row.update({key:result[key] for key in METRICS})
            row.update(status="estimated",rejection_reason="",warnings=" | ".join(result["warnings"]),
                       compression_to_buckling_ratio=result["compression_to_buckling_ratio"],
                       buckling_basis_relative_change=result["buckling_basis_relative_change"])
        except (ValueError,ArithmeticError) as exc:
            row.update({key:None for key in METRICS})
            row.update(status="rejected",rejection_reason=str(exc),warnings="")
        rows.append(row)
    engine_hash = hashlib.sha256(Path(__file__).with_name("prediction.py").read_bytes()).hexdigest()
    frame = pd.DataFrame(rows)
    frame["model_version"] = MODEL_VERSION
    frame["engine_sha256"] = engine_hash
    frame["assumptions"] = ASSUMPTIONS
    frame["sweep_axes_json"] = json.dumps([asdict(a) for a in axes],sort_keys=True)
    return frame


def sensitivity_figure(frame, axes, metric):
    valid = frame.status.eq("estimated")
    if len(axes)==1:
        fig = make_subplots(rows=2,cols=2,subplot_titles=list(METRICS.values()),vertical_spacing=.22)
        for i,(key,label) in enumerate(METRICS.items()):
            # Rejected values stay in the trace as None: lines must not bridge gaps.
            fig.add_trace(go.Scatter(x=frame[axes[0].field],y=frame[key],mode="lines+markers",
                                    customdata=frame.candidate_id,connectgaps=False,name=label,
                                    hovertemplate="%{x:.5g} µm<br>%{y:.5g}<extra>"+label+"</extra>"),row=i//2+1,col=i%2+1)
            fig.update_xaxes(title_text=FIELDS[axes[0].field],row=i//2+1,col=i%2+1)
    else:
        x,y = [a.field for a in axes]
        grid = frame.pivot(index=y,columns=x,values=metric).sort_index().sort_index(axis=1)
        fig = go.Figure(go.Heatmap(x=grid.columns.tolist(),y=grid.index.tolist(),z=grid.where(pd.notna(grid),None).values.tolist(),
                                  colorscale="Cividis",colorbar=dict(title="Estimate"),hoverongaps=False,
                                  hovertemplate="x %{x:.5g} µm<br>y %{y:.5g} µm<br>Estimate %{z:.5g}<extra></extra>"))
        # Scatter points make Plotly point-selection available on a heatmap.
        points = frame.loc[valid]
        fig.add_trace(go.Scatter(x=points[x],y=points[y],mode="markers",customdata=points.candidate_id,
                                marker=dict(size=13,color="rgba(80,80,80,0.25)",line=dict(width=1,color="white")),
                                hovertemplate="Candidate %{customdata}<br>x %{x:.5g} µm<br>y %{y:.5g} µm<extra></extra>"))
        fig.update_xaxes(title=FIELDS[x])
        fig.update_yaxes(title=FIELDS[y])
    fig.update_layout(height=560,showlegend=False,margin=dict(l=35,r=25,t=75,b=55),
                      title=dict(text="Unvalidated analytical screening"+(" · "+METRICS[metric] if len(axes)==2 else ""),font=dict(size=15)),
                      clickmode="event+select",dragmode="pan",uirevision="sweep-view")
    return fig


def figure_html(figure, manifest):
    """Self-contained high-resolution browser export with a full input manifest."""
    from html import escape
    html = figure.to_html(include_plotlyjs=True,config={"displaylogo":False,
         "toImageButtonOptions":{"format":"png","filename":"microneedle_design_space","width":2600,"height":1800,"scale":1}})
    return html.replace("</body>","<details><summary>Recorded inputs and model assumptions</summary><pre>"+
                        escape(json.dumps(manifest,indent=2))+"</pre></details></body>")
