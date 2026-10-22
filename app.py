"""Public analytical design studio; private engineering evidence excluded."""
import streamlit as st
from src.prediction_view import render_prediction_dashboard

st.set_page_config(page_title="Microneedle Design Studio", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {padding: 2.9rem 2rem 1.5rem; max-width: 1600px;}
h1 {font-size: 1.9rem !important; letter-spacing: -.04em; padding: 0 !important;}
h1::before {content: ''; display: inline-block; width: 5px; height: 26px; margin-right: 12px; background: #b52335;}
h3 {font-size: 1.25rem !important;} h4 {font-size: 1rem !important; padding: .25rem 0 !important;}
[data-testid="stVerticalBlock"] {gap: .55rem;}
[data-testid="stCaptionContainer"] p {margin-bottom: 0; font-size: .78rem;}
[data-testid="stWidgetLabel"] p {font-size: .79rem;}
[data-testid="stMetric"] {border-bottom: 1px solid color-mix(in srgb,currentColor 16%,transparent); padding: .35rem 0 .6rem;}
[data-testid="stMetricLabel"] p {font-size: .77rem; white-space: normal; line-height: 1.3;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
.st-key-pred_preview {border: 1px solid color-mix(in srgb,currentColor 12%,transparent); border-radius: 8px; overflow: hidden;}
.st-key-design_explorer [data-testid="stNumberInput"] input {font-size: .85rem;}
@media(max-width: 760px) {
 .block-container {padding: 3rem 1rem 1rem;}
 .st-key-design_explorer > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {flex-direction: column;}
 .st-key-design_explorer > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width: 100%; flex: 1 1 100%; min-width: 0;}
}
</style>""", unsafe_allow_html=True)
st.title("Microneedle Design Studio")
st.caption("UNIVERSITY OF CANTERBURY / ENME408 · User-defined analytical structural estimates; independent validation pending")



def switch_workspace():
    """Keep hidden widget values when Streamlit cleans up the inactive mode."""
    entering_compare = st.session_state.studio_compare
    outgoing = "single" if entering_compare else "comparison"
    incoming = "comparison" if entering_compare else "single"
    def belongs(key, mode):
        if key in ("pred_report","compare_html","compare_csv","compare_json"):
            return False  # Download/button state is read-only in Streamlit.
        return key.startswith("compare_") if mode == "comparison" else (key.startswith("pred_") or key in ("studio_view","studio_wire","studio_dark"))
    st.session_state[f"studio_saved_{outgoing}"] = {k:v for k,v in st.session_state.items() if belongs(k,outgoing)}
    for key,value in st.session_state.get(f"studio_saved_{incoming}",{}).items():
        st.session_state[key] = value


with st.container(key="design_explorer"):
    if st.toggle("Compare Designs", value=False, key="studio_compare", on_change=switch_workspace):
        from src.comparison_view import render_comparison
        render_comparison()
    else:
        render_prediction_dashboard()
notice_slot = st.empty()
if notice := st.session_state.pop("space_transfer_notice",None):
    notice_slot.success(notice)
from src.design_space_view import render_design_space
render_design_space(switch_workspace)
st.divider()
st.markdown("#### Project evidence")
st.info("Recorded Abaqus and MTS evidence is not included in this public deployment. No substitute engineering results are supplied. All displayed responses are unvalidated analytical estimates from user-entered assumptions.")
