import streamlit as st

def load_css():
    """Injects custom CSS for the dashboard."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
    /* Phosphor Icons (Sleek, modern library) */
    @import url('https://unpkg.com/@phosphor-icons/web@2.0.3/src/regular/style.css');
    @import url('https://unpkg.com/@phosphor-icons/web@2.0.3/src/fill/style.css');
    @import url('https://unpkg.com/@phosphor-icons/web@2.0.3/src/duotone/style.css');

    /* --- GLOBAL RESET & TYPOGRAPHY --- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #E1E7EF;
    }
    
    /* --- BACKGROUND WITH SUBTLE DEPTH --- */
    .stApp {
        background-color: #050505;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(0, 112, 243, 0.15) 0%, transparent 60%),
            radial-gradient(circle at 100% 0%, rgba(16, 185, 129, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 0% 100%, rgba(121, 40, 202, 0.1) 0%, transparent 50%);
        background-attachment: fixed;
    }

    /* --- PREMIUM GLASSMORPHISM CARDS --- */
    div[data-testid="metric-container"], 
    div[data-testid="stDataFrame"],
    .glass-card {
        background: rgba(20, 20, 25, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        position: relative;
        overflow: hidden;
    }
    
    /* Holographic Hover Effect */
    div[data-testid="metric-container"]:hover,
    .glass-card:hover {
        background: rgba(30, 30, 35, 0.6);
        border-color: rgba(255, 255, 255, 0.2);
        transform: translateY(-4px);
        box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.3),
            0 0 0 1px rgba(255, 255, 255, 0.1),
            inset 0 0 20px rgba(255, 255, 255, 0.05);
    }
    
    /* Subtle Chromatic Aberration Glow on Hover - Optimized */
    div[data-testid="metric-container"]:hover::before,
    .glass-card:hover::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(
            90deg, 
            transparent, 
            rgba(255, 255, 255, 0.02), 
            transparent
        );
        transform: skewX(-20deg);
        animation: shine 3s infinite; /* Slower animation for less GPU load */
        pointer-events: none;
    }

    @keyframes shine {
        0% { left: -100%; opacity: 0; }
        50% { opacity: 0.3; }
        100% { left: 200%; opacity: 0; }
    }

    /* --- SIDEBAR GLASS --- */
    section[data-testid="stSidebar"] {
        background: rgba(5, 5, 5, 0.7);
        backdrop-filter: blur(20px) saturate(180%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* --- TYPOGRAPHY & HEADERS --- */
    h1 {
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 2px 20px rgba(255, 255, 255, 0.1);
    }
    
    h2, h3 {
        color: #F8FAFC;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    
    div[data-testid="stMetricValue"], code {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
        color: #38BDF8; /* Cyan accent for numbers */
    }

    /* --- STATUS BADGES (GLOWING GLASS) --- */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        backdrop-filter: blur(8px);
    }
    .status-ok { 
        background: rgba(16, 185, 129, 0.15); 
        color: #34D399; 
        border: 1px solid rgba(16, 185, 129, 0.3);
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.1);
    }
    .status-err { 
        background: rgba(239, 68, 68, 0.15); 
        color: #F87171; 
        border: 1px solid rgba(239, 68, 68, 0.3);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.1);
    }

    /* --- TABS (FLOATING GLASS) --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(255, 255, 255, 0.03);
        padding: 8px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        color: #94A3B8;
        padding: 8px 20px;
        border-radius: 10px;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #F1F5F9;
        background: rgba(255, 255, 255, 0.05);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }

    /* --- INPUTS & BUTTONS (GLASS) --- */
    .stSelectbox > div > div, .stNumberInput > div > div {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: #FAFAFA;
        backdrop-filter: blur(10px);
    }
    .stSelectbox > div > div:hover, .stNumberInput > div > div:hover {
        border-color: rgba(255, 255, 255, 0.2);
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.9);
        color: #000000;
        border: none;
        font-weight: 600;
        border-radius: 10px;
        transition: all 0.2s;
    }
    button[kind="secondary"]:hover {
        background: #FFFFFF;
        transform: translateY(-1px);
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
    }
    
    /* --- TOAST --- */
    .stToast {
        background: rgba(20, 20, 25, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)
