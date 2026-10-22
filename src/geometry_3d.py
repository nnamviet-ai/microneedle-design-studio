"""Dimensionally faithful, lightweight parametric solids; no solved FEA fields."""
import math
import numpy as np
import plotly.graph_objects as go


def section_mesh(needle, x=0, y=0):
    """Closed linear taper with finite end caps. Coordinates are micrometres."""
    if needle.shape not in ("circular", "rectangular"):
        raise ValueError("No parametric replacement is available for this CAD geometry.")
    dims = [needle.length_um, needle.base_width_um, needle.tip_width_um]
    if needle.shape == "rectangular":
        dims += [needle.base_depth_um, needle.tip_depth_um]
    if not all(math.isfinite(v) and v > 0 for v in dims):
        raise ValueError("Enter finite, positive geometry dimensions; a zero-area tip is unsupported.")
    if needle.tip_width_um > needle.base_width_um or (needle.shape == "rectangular" and needle.tip_depth_um > needle.base_depth_um):
        raise ValueError("Tip dimensions must not exceed the base.")
    if needle.shape == "circular":
        theta = np.arange(64)*2*np.pi/64
        unit = np.column_stack((np.cos(theta), np.sin(theta)))
        base = unit*needle.base_width_um/2
        tip = unit*needle.tip_width_um/2
    else:
        unit = np.array([[-1,-1],[1,-1],[1,1],[-1,1]])/2
        base = unit*[needle.base_width_um, needle.base_depth_um]
        tip = unit*[needle.tip_width_um, needle.tip_depth_um]
    n = len(base)
    vertices = np.vstack((np.column_stack((base, np.zeros(n))),
                          np.column_stack((tip, np.full(n, needle.length_um))),
                          [[0,0,0],[0,0,needle.length_um]]))
    vertices[:,0] += x
    vertices[:,1] += y
    faces = []
    for i in range(n):
        j = (i+1)%n
        faces.extend([(i,j,n+j),(i,n+j,n+i),(2*n,j,i),(2*n+1,n+i,n+j)])
    return vertices, np.array(faces), n


def studio_figure(needle, *, array=False, pitch=600., wireframe=False, dark=False):
    """Single needle or 4 by 4 array on an explicitly illustrative connected base."""
    if not math.isfinite(pitch) or pitch <= 0:
        raise ValueError("Pitch must be finite and positive.")
    fig = go.Figure()
    colour = "#c5cdd7" if dark else "#a8b7c7"
    edge = "#c9d3df" if dark else "#52647a"
    centres = [(0.,0.)] if not array else [(c*pitch-1.5*pitch,r*pitch-1.5*pitch) for r in range(4) for c in range(4)]
    for index,(x,y) in enumerate(centres):
        v,f,n = section_mesh(needle,x,y)
        fig.add_trace(go.Mesh3d(x=v[:,0].tolist(),y=v[:,1].tolist(),z=v[:,2].tolist(),
            i=f[:,0].tolist(),j=f[:,1].tolist(),k=f[:,2].tolist(),color=colour,
            flatshading=needle.shape=="rectangular",name=f"Needle {index+1}",
            lighting=dict(ambient=.45,diffuse=.8,specular=.45,roughness=.35,fresnel=.15),
            lightposition=dict(x=2000,y=-3000,z=4000),
            hovertemplate="Geometric surface<br>x %{x:.4g} µm<br>y %{y:.4g} µm<br>z %{z:.4g} µm<extra>%{fullData.name}</extra>"))
        lines = []
        for ring in (0,n):
            lines.extend([*v[ring:ring+n],v[ring], [None,None,None]])
        for i in range(0,n,1 if wireframe or n==4 else 16):
            lines.extend([v[i],v[n+i],[None,None,None]])
        line = np.array(lines,dtype=object)
        fig.add_trace(go.Scatter3d(x=line[:,0].tolist(),y=line[:,1].tolist(),z=line[:,2].tolist(),
            mode="lines",line=dict(color=edge,width=1 if wireframe else 2),hoverinfo="skip",showlegend=False))
    depth = needle.base_width_um if needle.shape=="circular" else needle.base_depth_um
    if array:
        # Base thickness is a display convention, never an input to the beam model.
        hx,hy = 1.5*pitch+needle.base_width_um*.65,1.5*pitch+depth*.65
        t = min(needle.length_um*.08,100.)
        v = np.array([[-hx,-hy,-t],[hx,-hy,-t],[hx,hy,-t],[-hx,hy,-t],[-hx,-hy,0],[hx,-hy,0],[hx,hy,0],[-hx,hy,0]])
        f = np.array([(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)])
        fig.add_trace(go.Mesh3d(x=v[:,0].tolist(),y=v[:,1].tolist(),z=v[:,2].tolist(),
            i=f[:,0].tolist(),j=f[:,1].tolist(),k=f[:,2].tolist(),color="#64748b",flatshading=True,
            name="Illustrative connected base",hovertemplate=f"Display base · {t:g} µm thick<br>Not structurally modelled<extra></extra>"))
    else:
        offset = -needle.base_width_um*.9
        fig.add_trace(go.Scatter3d(x=[offset,offset],y=[0,0],z=[0,needle.length_um],mode="lines+text",
            text=["",f"Height {needle.length_um:g} µm"],textposition="top center",
            line=dict(color=edge,width=2),textfont=dict(color=edge,size=11),hoverinfo="skip",showlegend=False))
    bg = "#131b27" if dark else "#f5f7fa"
    fg = "#cbd5e1" if dark else "#536276"
    fig.update_layout(height=440,margin=dict(l=0,r=0,t=25,b=0),showlegend=False,
        paper_bgcolor=bg,font=dict(color=fg),uirevision="studio-camera-v1",
        scene=dict(aspectmode="data",bgcolor=bg,dragmode="orbit",
            camera=dict(eye=dict(x=2.1,y=-2.8,z=1.65),up=dict(x=0,y=0,z=1)),
            xaxis=dict(title="x · µm",showbackground=False,gridcolor=bg,zeroline=False),
            yaxis=dict(title="y · µm",showbackground=False,gridcolor=bg,zeroline=False),
            zaxis=dict(title="Height · µm",showbackground=False,gridcolor=bg,zeroline=False)),
        annotations=[dict(text="PARAMETRIC GEOMETRY · NOT AN ABAQUS MESH",xref="paper",yref="paper",x=.02,y=1.04,
                          showarrow=False,font=dict(size=10,color=fg))])
    return fig
