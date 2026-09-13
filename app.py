"""
app.py
======
MINE-X // Underground Mine Safety GCS Telemetry Dashboard

A ground control station (GCS) console for reviewing simulated atmospheric,
kinematic, and mesh-link telemetry from an underground mine safety and
rescue rover. Built with Streamlit. Visual language follows a light,
enterprise industrial-console convention (navy chrome, flat bordered
panels, semantic status color reserved for status only) rather than a
dark developer-tool theme.

Run with:
    streamlit run app.py
"""

from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from mine_analytics import CoExposureState, HazardLevel, MineAtmosphericAnalyzer, OxygenState

# --------------------------------------------------------------------------- #
# Page configuration
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="MINE-X // Underground GCS",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Design tokens & theme
# --------------------------------------------------------------------------- #
# Light, enterprise industrial-console palette: a deep steel-navy is the
# ONLY brand/chrome color (title bar, section rules, sidebar headers).
# Amber / red / green / blue are never used decoratively -- each appears
# exclusively to mean caution / danger / safe / comms-info, the way a real
# mine-safety HMI reserves color for status rather than styling.

BG_PRIMARY = "#F2F4F7"
BG_PANEL = "#FFFFFF"
BG_SIDEBAR = "#EAEDF1"
BORDER_STEEL = "#D8DEE5"
TEXT_PRIMARY = "#182430"
TEXT_SECONDARY = "#5B6572"
BRAND_NAVY = "#1F3A54"
BRAND_NAVY_DARK = "#152838"

ACCENT_AMBER = "#B9740B"      # WARNING
CAUTION_GOLD = "#8A6D00"      # CAUTION
DANGER_RED = "#AE3A3A"        # CRITICAL
SAFE_GREEN = "#1E7A44"        # NOMINAL
INFO_STEEL = "#2E5F86"        # comms / info only

HAZARD_COLOR = {
    HazardLevel.NOMINAL: SAFE_GREEN,
    HazardLevel.CAUTION: CAUTION_GOLD,
    HazardLevel.WARNING: ACCENT_AMBER,
    HazardLevel.CRITICAL: DANGER_RED,
}

HAZARD_LABEL = {
    HazardLevel.NOMINAL: "SYSTEM NOMINAL — MINE ATMOSPHERE STABLE, MESH LINK ACTIVE",
    HazardLevel.CAUTION: "CAUTION — TREND DEVIATION DETECTED, CONTINUE MONITORING",
    HazardLevel.WARNING: "WARNING — HAZARD INDICATORS ELEVATED, PREPARE CONTINGENCY",
    HazardLevel.CRITICAL: "CRITICAL — HAZARDOUS CONDITION CONFIRMED, EVACUATE MESH ZONE",
}

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
    }}

    .stApp {{
        background-color: {BG_PRIMARY};
        color: {TEXT_PRIMARY};
        font-size: 17px;
    }}

    [data-testid="stSidebar"] {{
        background-color: {BG_SIDEBAR};
        border-right: 1px solid {BORDER_STEEL};
    }}
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {BRAND_NAVY};
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.4rem;
        border-bottom: 2px solid {BRAND_NAVY};
        padding-bottom: 0.4rem;
    }}
    [data-testid="stSidebar"] label {{
        color: {TEXT_PRIMARY} !important;
        font-size: 1rem;
        font-weight: 500;
    }}
    [data-testid="stSidebar"] input {{
        font-size: 1rem !important;
    }}

    h1, h2, h3 {{ color: {TEXT_PRIMARY} !important; }}
    h3 {{
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 700;
        font-size: 1.32rem;
        padding-bottom: 0.4rem;
        border-bottom: 3px solid {BRAND_NAVY};
        margin-top: 0.6rem;
        display: inline-block;
    }}
    p, li, span, div {{
        font-size: 1.05rem;
    }}

    /* ---- Enterprise chrome header bar ---- */
    .app-header {{
        background: linear-gradient(90deg, {BRAND_NAVY_DARK} 0%, {BRAND_NAVY} 100%);
        color: #FFFFFF;
        border-radius: 5px;
        padding: 1.5rem 1.9rem 1.3rem 1.9rem;
        margin-bottom: 0.4rem;
    }}
    .app-header-title {{
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        letter-spacing: -0.01em;
        line-height: 1.15;
        margin: 0;
    }}
    .app-header-sub {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.08rem;
        color: #C9D6E2;
        margin-top: 0.45rem;
    }}

    .hazard-tape {{
        height: 10px;
        width: 100%;
        margin: 0.7rem 0 1.5rem 0;
        border-radius: 2px;
        background: repeating-linear-gradient(
            135deg,
            {ACCENT_AMBER} 0px, {ACCENT_AMBER} 16px,
            {BRAND_NAVY_DARK} 16px, {BRAND_NAVY_DARK} 32px
        );
    }}

    .hazard-banner {{
        padding: 1.15rem 1.5rem;
        border-radius: 5px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.18rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        color: #FFFFFF;
        margin-bottom: 1.2rem;
        border-left: 7px solid rgba(0,0,0,0.22);
    }}
    .hazard-advisory {{
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.02rem;
        font-weight: 400;
        color: rgba(255,255,255,0.92);
        margin-top: 0.4rem;
    }}

    [data-testid="stMetric"] {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER_STEEL};
        border-top: 4px solid {BRAND_NAVY};
        border-radius: 3px;
        padding: 1rem 1.15rem 0.85rem 1.15rem;
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.15rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_SECONDARY};
        font-weight: 600;
        font-size: 0.95rem;
    }}
    [data-testid="stMetricDelta"] {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.92rem;
    }}

    .panel {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER_STEEL};
        border-radius: 3px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }}
    .panel-safe {{ border-left: 5px solid {SAFE_GREEN}; }}
    .panel-info {{ border-left: 5px solid {INFO_STEEL}; }}
    .panel-warn {{ border-left: 5px solid {ACCENT_AMBER}; }}
    .panel-danger {{ border-left: 5px solid {DANGER_RED}; }}

    .panel-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 1.06rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid {BORDER_STEEL};
    }}
    .panel-row:last-child {{ border-bottom: none; }}
    .panel-row .label {{ color: {TEXT_SECONDARY}; font-weight: 500; }}
    .panel-row .value {{
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        font-size: 1.06rem;
    }}

    .badge {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.86rem;
        font-weight: 700;
        padding: 0.22rem 0.65rem;
        border-radius: 3px;
    }}
    .badge-safe {{ background-color: rgba(30,122,68,0.13); color: {SAFE_GREEN}; }}
    .badge-caution {{ background-color: rgba(138,109,0,0.14); color: {CAUTION_GOLD}; }}
    .badge-warn {{ background-color: rgba(185,116,11,0.14); color: {ACCENT_AMBER}; }}
    .badge-danger {{ background-color: rgba(174,58,58,0.15); color: {DANGER_RED}; }}

    hr {{ border-color: {BORDER_STEEL} !important; }}

    footer, #MainMenu {{ visibility: hidden; }}
    .console-footer {{
        color: {TEXT_SECONDARY};
        font-size: 0.9rem;
        font-family: 'IBM Plex Mono', monospace;
        margin-top: 1.7rem;
        border-top: 1px solid {BORDER_STEEL};
        padding-top: 0.9rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def oxygen_badge_kind(state: OxygenState) -> str:
    return {
        OxygenState.NORMAL: "safe",
        OxygenState.ACCEPTABLE: "caution",
        OxygenState.DEFICIENT: "warn",
        OxygenState.DANGEROUS: "danger",
    }[state]


def co_badge_kind(state: CoExposureState) -> str:
    return {
        CoExposureState.NORMAL: "safe",
        CoExposureState.ELEVATED: "caution",
        CoExposureState.HIGH: "warn",
        CoExposureState.SEVERE: "warn",
        CoExposureState.IDLH: "danger",
    }[state]


def combine_hazard(base: HazardLevel, rssi: float, tilt: float) -> HazardLevel:
    """Escalate the atmospheric hazard level using kinematic / RF cutoffs."""
    order = [HazardLevel.NOMINAL, HazardLevel.CAUTION, HazardLevel.WARNING, HazardLevel.CRITICAL]
    level = base
    if rssi <= -95 or tilt > 45:
        level = HazardLevel.CRITICAL
    elif rssi <= -82 or tilt > 35:
        if order.index(HazardLevel.WARNING) > order.index(level):
            level = HazardLevel.WARNING
    return level


def ratio_row(name: str, value, note: str) -> str:
    display_value = "—" if value is None else f"{value}"
    return (
        f'<div class="panel-row"><span class="label">{name}</span>'
        f'<span class="value">{display_value}<span style="color:{TEXT_SECONDARY};'
        f'font-weight:400;font-size:0.88rem;"> {note}</span></span></div>'
    )


# --------------------------------------------------------------------------- #
# Session state — persistent analyzer + telemetry log across reruns
# --------------------------------------------------------------------------- #

if "analyzer" not in st.session_state:
    st.session_state.analyzer = MineAtmosphericAnalyzer(history_window=40, sample_interval_s=2.0)
if "telemetry_log" not in st.session_state:
    st.session_state.telemetry_log = []

analyzer = st.session_state.analyzer

# --------------------------------------------------------------------------- #
# Sidebar — telemetry control matrix
# --------------------------------------------------------------------------- #

st.sidebar.markdown("## Console")
node_id = st.sidebar.text_input("Rover / Node ID", value="MX-ROVER-01")
simulation_mode = st.sidebar.checkbox("Simulate live telemetry drift", value=False)

st.sidebar.markdown("### Atmospheric Sensors")
ch4_input = st.sidebar.slider("Methane, CH4 (% vol)", 0.0, 15.0, 0.4, 0.1)
o2_input = st.sidebar.slider("Oxygen, O2 (% vol)", 5.0, 21.0, 20.4, 0.1)
co_input = st.sidebar.slider("Carbon Monoxide, CO (PPM)", 0.0, 300.0, 10.0, 5.0)
co2_input = st.sidebar.slider("Carbon Dioxide, CO2 (% vol)", 0.0, 3.0, 0.03, 0.01)
h2_input = st.sidebar.slider("Hydrogen, H2 (PPM)", 0.0, 500.0, 0.0, 5.0)

st.sidebar.markdown("### RF & Kinematics")
rssi_input = st.sidebar.slider("Sub-1GHz mesh RSSI (dBm)", -110, -40, -68, 1)
tilt_input = st.sidebar.slider("Chassis rollover tilt (deg)", 0.0, 60.0, 4.2, 0.5)

st.sidebar.markdown(
    f'<div class="console-footer">Local time: {datetime.now().strftime("%H:%M:%S")}<br>'
    f'Session samples logged: {len(st.session_state.telemetry_log)}</div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #

st.markdown(
    f'<div class="app-header">'
    f'<div class="app-header-title">MINE-X — AI-Powered Mine Safety GCS</div>'
    f'<div class="app-header-sub">Ground Control Station · DGMS-oriented Ex-d Surface Console · '
    f'Sub-1GHz Mesh Telemetry Link · Node: {node_id}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="hazard-tape"></div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Run analysis
# --------------------------------------------------------------------------- #

res = analyzer.analyze(ch4_input, o2_input, co_input, co2_pct=co2_input, h2_ppm=h2_input)
overall_hazard = combine_hazard(res.hazard_level, rssi_input, tilt_input)

# Log this sample for the trend charts (persists across reruns)
st.session_state.telemetry_log.append(
    {
        "sample": len(st.session_state.telemetry_log),
        "CH4": ch4_input,
        "CO": co_input,
        "CO2": co2_input,
    }
)
st.session_state.telemetry_log = st.session_state.telemetry_log[-60:]

# --------------------------------------------------------------------------- #
# Hazard banner
# --------------------------------------------------------------------------- #

banner_color = HAZARD_COLOR[overall_hazard]
st.markdown(
    f'<div class="hazard-banner" style="background-color:{banner_color};">'
    f"{HAZARD_LABEL[overall_hazard]}"
    f'<div class="hazard-advisory">{res.advisory}</div>'
    f"</div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# KPI metric row
# --------------------------------------------------------------------------- #

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Methane (CH4)", f"{ch4_input:.1f}%", f"LEL {analyzer.CH4_LEL:.0f}%")
    st.markdown(badge(res.methane_state.value, "safe" if res.methane_state.name == "BACKGROUND" else "warn"), unsafe_allow_html=True)

with col2:
    st.metric("Oxygen (O2)", f"{o2_input:.1f}%", f"{o2_input - 20.93:+.2f}% vs ambient")
    st.markdown(badge(res.oxygen_state.value, oxygen_badge_kind(res.oxygen_state)), unsafe_allow_html=True)

with col3:
    st.metric("Carbon Monoxide", f"{co_input:.0f} PPM", "Safe < 25")
    st.markdown(badge(res.co_exposure_state.value, co_badge_kind(res.co_exposure_state)), unsafe_allow_html=True)

with col4:
    st.metric("Carbon Dioxide", f"{co2_input:.2f}%", "Background ~0.03%")

with col5:
    st.metric("Graham's Ratio", f"{res.grahams_ratio}", res.grahams_status.replace("_", " ").title())

with col6:
    st.metric("Mesh Signal", f"{rssi_input} dBm", "Node 2 active" if rssi_input > -82 else "Link degraded", delta_color="off")

st.markdown("")

# --------------------------------------------------------------------------- #
# Trend charts + fire-ratio / explosibility panels
# --------------------------------------------------------------------------- #

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Atmospheric Telemetry Trend")

    if simulation_mode:
        jitter = st.session_state.telemetry_log[-1].copy()
        jitter["CH4"] = float(np.clip(jitter["CH4"] + np.random.normal(0, 0.03), 0, 15))
        jitter["CO"] = float(np.clip(jitter["CO"] + np.random.normal(0, 1.5), 0, 300))

    log_df = pd.DataFrame(st.session_state.telemetry_log)

    ch4_chart = (
        alt.Chart(log_df)
        .mark_area(line={"color": ACCENT_AMBER, "strokeWidth": 2.5}, opacity=0.14, color=ACCENT_AMBER)
        .encode(
            x=alt.X("sample:Q", title="Sample #", axis=alt.Axis(grid=False, labelFontSize=12, titleFontSize=13)),
            y=alt.Y("CH4:Q", title="CH4 (% vol)", axis=alt.Axis(grid=True, gridColor=BORDER_STEEL, labelFontSize=12, titleFontSize=13)),
            tooltip=["sample", "CH4"],
        )
        .properties(height=185, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=TEXT_SECONDARY, titleColor=TEXT_PRIMARY, labelFont="IBM Plex Mono", titleFont="IBM Plex Sans")
    )
    st.altair_chart(ch4_chart, use_container_width=True)

    co_chart = (
        alt.Chart(log_df)
        .mark_area(line={"color": DANGER_RED, "strokeWidth": 2.5}, opacity=0.12, color=DANGER_RED)
        .encode(
            x=alt.X("sample:Q", title="Sample #", axis=alt.Axis(grid=False, labelFontSize=12, titleFontSize=13)),
            y=alt.Y("CO:Q", title="CO (PPM)", axis=alt.Axis(grid=True, gridColor=BORDER_STEEL, labelFontSize=12, titleFontSize=13)),
            tooltip=["sample", "CO"],
        )
        .properties(height=185, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=TEXT_SECONDARY, titleColor=TEXT_PRIMARY, labelFont="IBM Plex Mono", titleFont="IBM Plex Sans")
    )
    st.altair_chart(co_chart, use_container_width=True)

with col_right:
    st.subheader("Fire-Risk Index Panel")

    ratios_html = (
        '<div class="panel panel-warn">'
        + ratio_row("Graham's Ratio", res.grahams_ratio, "CO / ΔO2")
        + ratio_row("Young's Ratio", res.youngs_ratio, "CO2 / ΔO2")
        + ratio_row("Jones &amp; Trickett", res.jones_trickett_ratio, "(CO2+.75CO-.25H2)/ΔO2")
        + ratio_row("Oxides of Carbon", res.co_co2_ratio, "CO / CO2")
        + ratio_row("O2 Deficiency", f"{res.o2_deficiency_pct}%", "ΔO2 vs expected")
        + "</div>"
    )
    st.markdown(ratios_html, unsafe_allow_html=True)

    coward_kind = "danger" if "EXPLOSIVE MIXTURE" in res.coward_status else (
        "warn" if "POTENTIALLY EXPLOSIVE" in res.coward_status else "safe"
    )
    st.markdown(
        f'<div class="panel panel-info">'
        f'<div class="panel-row"><span class="label">Coward Triangle</span>'
        f'{badge(res.coward_status.replace("_", " "), coward_kind)}</div>'
        f'<div class="panel-row"><span class="label">N2 (balance)</span>'
        f'<span class="value">{res.n2_pct}%</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# --------------------------------------------------------------------------- #
# Subsystem status row
# --------------------------------------------------------------------------- #

col_b1, col_b2, col_b3 = st.columns(3)

with col_b1:
    st.subheader("Kinematics & IMU")
    tilt_kind = "danger" if tilt_input > 35 else ("warn" if tilt_input > 20 else "safe")
    st.markdown(
        f'<div class="panel panel-{"danger" if tilt_kind == "danger" else "safe"}">'
        f'<div class="panel-row"><span class="label">Roll / pitch tilt</span>'
        f'<span class="value">{tilt_input:.1f}&deg;</span></div>'
        f'<div class="panel-row"><span class="label">Rollover margin</span>'
        f'{badge("Rollover risk" if tilt_input > 35 else "Stable", tilt_kind)}</div>'
        f'<div class="panel-row"><span class="label">Chassis status</span>'
        f'<span class="value">Tracked mobility active</span></div>'
        f'<div class="panel-row"><span class="label">Enclosure</span>'
        f'<span class="value">Ex-d sealing intact</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

with col_b2:
    st.subheader("Mesh Node Topology")
    rssi_kind = "danger" if rssi_input <= -95 else ("warn" if rssi_input <= -82 else "safe")
    st.markdown(
        f'<div class="panel panel-info">'
        f'<div class="panel-row"><span class="label">RSSI</span>'
        f'<span class="value">{rssi_input} dBm</span></div>'
        f'<div class="panel-row"><span class="label">Link state</span>'
        f'{badge("Degraded" if rssi_kind != "safe" else "Stable", rssi_kind)}</div>'
        f'<div class="panel-row"><span class="label">Active repeaters</span>'
        f'<span class="value">3 nodes deployed</span></div>'
        f'<div class="panel-row"><span class="label">Protocol</span>'
        f'<span class="value">ESP-NOW peer-to-peer</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

with col_b3:
    st.subheader("Thermal & Vision Sensor")
    st.markdown(
        f'<div class="panel panel-safe">'
        f'<div class="panel-row"><span class="label">LWIR thermal core</span>'
        f'<span class="value">Active (8&ndash;14 &micro;m)</span></div>'
        f'<div class="panel-row"><span class="label">mmWave radar</span>'
        f'<span class="value">Breathing detection nominal</span></div>'
        f'<div class="panel-row"><span class="label">Dust filtering</span>'
        f'<span class="value">Mie scattering compensated</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #

st.markdown(
    f'<div class="console-footer">'
    f"MINE-X GCS Dashboard · Simulated telemetry for demonstration and jury review · "
    f"Fire-risk indices are indicative, not a substitute for certified gas analysis · "
    f'Last refresh: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    f"</div>",
    unsafe_allow_html=True,
)

if simulation_mode:
    import time as _time

    _time.sleep(2)
    st.rerun()