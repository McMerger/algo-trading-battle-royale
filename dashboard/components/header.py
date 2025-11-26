import streamlit as st
from data.api import get_system_health

def render_header(health=None):
    """Renders the dashboard header and system status."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1><i class="ph-duotone ph-lightning" style="color: #38BDF8; vertical-align: middle;"></i> SignalOps Terminal</h1>', unsafe_allow_html=True)
        st.markdown('<span style="color: #94A3B8; margin-left: 4px;">Event-Aware Algorithmic Trading Engine</span>', unsafe_allow_html=True)
    with col2:
        st.markdown("### System Status")
        if health is None:
            health = {"Go Engine": "UNKNOWN", "Database": "UNKNOWN"}
        
        cols = st.columns(3)
        for i, (service, status) in enumerate(health.items()):
            color = "status-ok" if status == "ONLINE" else "status-err"
            cols[i].markdown(f"<div class='status-badge {color}'>{service}</div>", unsafe_allow_html=True)

    st.markdown("---")
