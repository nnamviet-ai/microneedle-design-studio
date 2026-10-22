"""Presentation helpers only; structural equations remain in prediction.py."""
import copy
import json

import pandas as pd
from plotly.subplots import make_subplots

from src.geometry_3d import studio_figure


METRICS = (
    ("Axial compression (µm)", "axial_deformation_um"),
    ("Axial stiffness (N/mm/needle)", "needle_axial_stiffness_N_per_mm"),
    ("Lateral displacement (µm)", "lateral_deformation_um"),
    ("Elastic buckling indicator (N/needle)", "elastic_buckling_indicator_N_per_needle"),
)


def comparison_table(a, b):
    """Signed differences relative to A; zero baselines have no percent change."""
    rows = []
    for label, key in METRICS:
        av, bv = a[key] if a else None, b[key] if b else None
        delta = bv-av if av is not None and bv is not None else None
        rows.append({"Quantity": label, "Design A": av, "Design B": bv,
                     "B − A": delta, "Change from A (%)":
                     100*delta/abs(av) if delta is not None and av != 0 else None})
    return pd.DataFrame(rows)


def dimensions(needle):
    base = f"Ø{needle.base_width_um:g}" if needle.shape == "circular" else f"{needle.base_width_um:g} × {needle.base_depth_um:g}"
    tip = f"Ø{needle.tip_width_um:g}" if needle.shape == "circular" else f"{needle.tip_width_um:g} × {needle.tip_depth_um:g}"
    return f"{needle.shape.title()} · Height {needle.length_um:g} µm · Base {base} µm · Tip {tip} µm"


def comparison_figure(a, b, *, array=False, pitch=600., wireframe=False, dark=False):
    """Paired scenes share bounds and explicit aspect ratios (one physical scale)."""
    figures = [studio_figure(n, array=array, pitch=pitch, wireframe=wireframe, dark=dark) for n in (a,b)]
    fig = make_subplots(rows=1, cols=2, specs=[[{"type":"scene"}, {"type":"scene"}]],
                        horizontal_spacing=.04, subplot_titles=("Design A", "Design B"))
    # Include dimension lines and the illustrative array base in the common envelope.
    bounds = []
    for axis in ("x", "y", "z"):
        values = [v for f in figures for t in f.data for v in getattr(t, axis) if v is not None]
        lo, hi = min(values), max(values)
        pad = max((hi-lo)*.10, 1.)
        bounds.append([lo-pad, hi+pad])
    spans = [hi-lo for lo,hi in bounds]
    # Bound the longest visual extent so slender models fill the viewport
    # without cropping. Both scenes retain exactly the same physical scale.
    normaliser = max(spans)/2.2
    for i, source in enumerate(figures, 1):
        for trace in source.data:
            fig.add_trace(trace, row=1, col=i)
        scene = copy.deepcopy(source.layout.scene.to_plotly_json())
        scene.update(aspectmode="manual", aspectratio=dict(zip(("x","y","z"), [s/normaliser for s in spans])),
                     uirevision="comparison-camera-v1",domain=dict(y=[.18,1]))
        for axis, limits in zip(("xaxis","yaxis","zaxis"), bounds):
            scene[axis].update(range=limits, autorange=False, nticks=4 if axis=="zaxis" else 3)
        fig.update_layout(**{f"scene{i if i > 1 else ''}":scene})
    for x, needle in ((.24,a),(.76,b)):
        fig.add_annotation(text=dimensions(needle).replace(" · ","<br>",1),
                           x=x,y=.065,xref="paper",yref="paper",showarrow=False,font=dict(size=11))
    fig.add_annotation(text="PARAMETRIC GEOMETRY · UNVALIDATED ANALYTICAL MODEL",
                       x=.5,y=.005,xref="paper",yref="paper",showarrow=False,font=dict(size=10))
    fig.update_layout(height=520, margin=dict(l=0,r=0,t=40,b=10), showlegend=False,
                      paper_bgcolor=figures[0].layout.paper_bgcolor,
                      font=figures[0].layout.font, uirevision="comparison-camera-v1")
    return fig


def interactive_html(fig, storage_key, *, caption="Parametric geometry · analytical estimates are unvalidated"):
    """Self-contained export and embedded viewer; persist and synchronise cameras.

    Streamlit can remount charts despite uirevision. Browser storage survives an
    iframe remount. Storage failure is harmless (e.g. browser privacy settings).
    """
    script = r"""
    const gd = document.getElementById('{plot_id}');
    const storageKey = STORAGE_KEY;
    const scenes = Object.keys(gd.layout).filter(k => /^scene\d*$/.test(k));
    let busy = false;
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (saved) Plotly.relayout(gd, Object.fromEntries(scenes.map(s => [s+'.camera', saved])));
    } catch(e) {}
    gd.on('plotly_relayout', function(event) {
      if (busy) return;
      const source = scenes.find(s => event[s+'.camera']);
      if (!source) return;
      const camera = event[source+'.camera'];
      try { localStorage.setItem(storageKey, JSON.stringify(camera)); } catch(e) {}
      busy = true;
      Plotly.relayout(gd, Object.fromEntries(scenes.map(s => [s+'.camera',camera])))
        .finally(() => { busy = false; });
    });
    """.replace("STORAGE_KEY", json.dumps(storage_key))
    html = fig.to_html(include_plotlyjs=True, full_html=True, post_script=script,
                       config={"displaylogo":False, "scrollZoom":True, "responsive":True,
                               "toImageButtonOptions":{"format":"png", "filename":"microneedle_comparison" if "scene2" in fig.layout else "microneedle_geometry",
                                                       "width":2400,"height":1400,"scale":1}})
    # Caption uses static text supplied by the app, never user HTML.
    from html import escape
    return html.replace("<body>", '<body style="margin:0"><div style="font:14px sans-serif;padding:10px;color:#334155;background:#fff">'+escape(caption)+'</div>')
