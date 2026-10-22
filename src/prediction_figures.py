"""Presentation of actual input sections and first-order analytical response."""
import numpy as np
import plotly.graph_objects as go


def geometry_figure(needle):
    """Dimensioned orthographic profiles; never a mesh or deformation result."""
    fig = go.Figure()
    profiles = [("Width profile", needle.base_width_um, needle.tip_width_um, 0)]
    if needle.shape == "rectangular":
        profiles.append(("Depth profile", needle.base_depth_um, needle.tip_depth_um,
                         max(needle.base_width_um, needle.base_depth_um) * 3.5))
    for label, base, tip, offset in profiles:
        x = np.array([-base/2, -tip/2, tip/2, base/2, -base/2]) + offset
        y = [0, needle.length_um, needle.length_um, 0, 0]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", fill="toself", name=label,
                                line=dict(color="#668b9b", width=2),
                                fillcolor="rgba(102,139,155,0.16)",
                                hovertemplate=label + "<br>x: %{x:.6g} µm<br>Height: %{y:.6g} µm<extra></extra>"))
        for height, size, title in [(0, base, "Base"), (needle.length_um, tip, "Tip")]:
            fig.add_shape(type="line", x0=offset-size/2, x1=offset+size/2,
                          y0=height, y1=height, line=dict(color="#668b9b", width=1))
            fig.add_annotation(x=offset, y=height, text=f"{title} {size:.4g} µm",
                               showarrow=False, font=dict(size=11), yshift=-16 if height == 0 else 16)
        fig.add_annotation(x=offset, y=needle.length_um/2, text=label,
                           showarrow=False, textangle=-90)
    height_x = -profiles[0][1]*0.85
    fig.add_annotation(x=height_x, y=needle.length_um, ax=height_x, ay=0,
                       axref="x", ayref="y", text="", showarrow=True,
                       arrowhead=2, arrowside="end+start", arrowcolor="#668b9b")
    fig.add_annotation(x=height_x, y=needle.length_um/2,
                       text=f"Height {needle.length_um:.4g} µm", textangle=-90,
                       xshift=-18, showarrow=False)
    fig.update_layout(height=210, margin=dict(l=25, r=15, t=24, b=24),
                      showlegend=False, dragmode="pan", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
                      yaxis=dict(visible=False, range=[-needle.length_um*.025, needle.length_um*1.025]))
    return fig


def array_figure(needle, pitch):
    """User-proposed 4 × 4 footprint, independent of loaded-needle count."""
    fig = go.Figure()
    for row in range(4):
        for col in range(4):
            x, y = col*pitch, row*pitch
            w = needle.base_width_um/2
            d = w if needle.shape == "circular" else needle.base_depth_um/2
            fig.add_shape(type="circle" if needle.shape == "circular" else "rect",
                          x0=x-w, x1=x+w, y0=y-d, y1=y+d,
                          line=dict(color="#668b9b", width=1), fillcolor="rgba(102,139,155,0.16)")
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=15, b=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(title="Arrangement x (µm)", scaleanchor="y", scaleratio=1),
                      yaxis=dict(title="Arrangement y (µm)"))
    return fig


def response_figure(result, axial, count):
    """Linear axial relation from the engine's integrated compliance only."""
    loads = np.linspace(0, axial, 41)
    compression = loads / result["array_axial_stiffness_N_per_mm"] * 1000
    fig = go.Figure(go.Scatter(x=loads, y=compression, mode="lines",
                              name="First-order analytical estimate", line=dict(color="#668b9b", width=2),
                              hovertemplate="Total force: %{x:.7g} N<br>Compression: %{y:.7g} µm<extra></extra>"))
    fig.add_trace(go.Scatter(x=[axial], y=[result["axial_deformation_um"]], mode="markers",
                             name="Selected load", marker=dict(color="#668b9b", size=9)))
    fig.update_layout(height=245, margin=dict(l=20, r=15, t=10, b=30), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_title=f"Total compressive force (N) · {count} loaded needle(s)",
                      yaxis_title="Axial compression (µm)")
    return fig


def registered_arrangement_figure(record):
    """Uniform-pitch reference from registered metadata; no CAD reconstruction."""
    px, py = float(record.pitch_x_um), float(record.pitch_y_um)
    rows, columns = int(record.array_rows), int(record.array_columns)
    if not np.isfinite([px,py]).all() or min(px,py,rows,columns) <= 0:
        raise ValueError("Recorded arrangement is incomplete.")
    x,y = np.meshgrid(np.arange(columns)*px,np.arange(rows)*py)
    fig = go.Figure(go.Scatter(x=x.ravel(),y=y.ravel(),mode="markers",
                              marker=dict(symbol="cross",color="#668b9b",size=10),
                              hovertemplate="Nominal array centre<br>x: %{x:.6g} µm<br>y: %{y:.6g} µm<extra></extra>"))
    fig.update_layout(height=260, margin=dict(l=20,r=20,t=10,b=30),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(title="Recorded x spacing (µm)",scaleanchor="y",scaleratio=1),
                      yaxis=dict(title="Recorded y spacing (µm)"))
    return fig
