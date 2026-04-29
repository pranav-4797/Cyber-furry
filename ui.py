"""
ui.py — CyberFury AI Forensic Lab
All visual components: theme injection, progress stages, verdict card,
explainability panel, metadata viewer, and forensic tools bar.
"""

import streamlit as st
import urllib.parse

# ─── Colour Palette ───────────────────────────────────────────────────────────
T = {
    "bg":         "#0F1C2E",
    "surface":    "#16263D",
    "border":     "#1E3A5F",
    "accent":     "#2F80ED",
    "cyan":       "#56CCF2",
    "text":       "#E6EDF5",
    "muted":      "#7A8EA8",
    "danger":     "#EB5757",
    "warning":    "#F2994A",
    "success":    "#27AE60",
    "uncertain":  "#F2C94C",
}

# ─── Theme CSS ────────────────────────────────────────────────────────────────

def apply_theme() -> None:
    """Inject global CSS theme into the Streamlit app."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

    /* ── Base ─────────────────────────────────────────────────────────── */
    .stApp {{
        background-color: {T['bg']};
        color: {T['text']};
        font-family: 'Inter', -apple-system, sans-serif;
    }}

    /* ── Headers ──────────────────────────────────────────────────────── */
    h1, h2, h3, h4 {{ color: {T['text']} !important; font-family: 'Rajdhani', sans-serif; font-weight: 700; }}

    /* ── Sidebar ──────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{ background-color: {T['surface']}; border-right: 1px solid {T['border']}; }}

    /* ── File Uploader ────────────────────────────────────────────────── */
    [data-testid="stFileUploader"] {{
        background-color: {T['surface']};
        padding: 20px;
        border-radius: 14px;
        border: 1.5px dashed {T['accent']};
        transition: border-color 0.2s;
    }}
    [data-testid="stFileUploader"]:hover {{ border-color: {T['cyan']}; }}
    [data-testid="stFileUploader"] section button {{
        color: #fff !important;
        background-color: {T['accent']} !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
    }}
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] small {{ color: {T['text']} !important; }}

    /* ── Buttons ──────────────────────────────────────────────────────── */
    .stButton > button {{
        width: 100%;
        background: linear-gradient(135deg, {T['accent']}, #1A6CC9);
        color: #fff;
        border: none;
        border-radius: 10px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 13px 20px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 15px rgba(47,128,237,0.25);
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {T['cyan']}, {T['accent']});
        color: {T['bg']};
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(86,204,242,0.35);
    }}
    .stButton > button:active {{ transform: translateY(0); }}

    /* ── Link Buttons ─────────────────────────────────────────────────── */
    [data-testid="stLinkButton"] a {{
        background: {T['surface']} !important;
        color: {T['cyan']} !important;
        border: 1px solid {T['border']} !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        display: block;
        text-align: center;
    }}
    [data-testid="stLinkButton"] a:hover {{
        border-color: {T['cyan']} !important;
        background: rgba(86,204,242,0.07) !important;
    }}

    /* ── Info / Warning boxes ─────────────────────────────────────────── */
    [data-testid="stAlert"] {{ border-radius: 10px; }}

    /* ── Progress bar ─────────────────────────────────────────────────── */
    [data-testid="stProgress"] > div > div {{
        background: linear-gradient(90deg, {T['accent']}, {T['cyan']});
        border-radius: 6px;
    }}
    [data-testid="stProgress"] > div {{
        background: {T['surface']};
        border-radius: 6px;
    }}

    /* ── Expander ─────────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: {T['surface']};
        border: 1px solid {T['border']};
        border-radius: 12px;
        overflow: hidden;
    }}
    [data-testid="stExpander"] summary {{
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        color: {T['cyan']};
        padding: 12px 16px;
    }}

    /* ── Divider ──────────────────────────────────────────────────────── */
    hr {{ border-color: {T['border']} !important; margin: 20px 0 !important; }}

    /* ── Code blocks ──────────────────────────────────────────────────── */
    code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; }}

    /* ── Scrollbar ────────────────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {T['bg']}; }}
    ::-webkit-scrollbar-thumb {{ background: {T['border']}; border-radius: 3px; }}

    /* ── Card utility ─────────────────────────────────────────────────── */
    .cf-card {{
        background: {T['surface']};
        border: 1px solid {T['border']};
        border-radius: 14px;
        padding: 22px 24px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        margin-bottom: 16px;
    }}
    .cf-mono {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: {T['cyan']}; }}
    .cf-muted {{ color: {T['muted']}; font-size: 0.88rem; }}
    </style>
    """, unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────

def render_header() -> None:
    st.markdown(f"""
    <div style="text-align:center; padding: 10px 0 28px 0;">
        <h1 style="
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.4rem;
            letter-spacing: 0.12em;
            margin: 0;
            background: linear-gradient(90deg, {T['cyan']}, {T['accent']}, {T['text']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        ">🛡️ CYBERFURY</h1>
        <p style="color:{T['muted']}; font-family:'Inter',sans-serif; font-size:0.92rem;
                  letter-spacing:0.25em; margin-top:4px; text-transform:uppercase;">
            AI Forensic Detection Lab
        </p>
        <div style="width:80px; height:2px; background:linear-gradient(90deg,{T['accent']},{T['cyan']});
                    margin:10px auto 0; border-radius:2px;"></div>
    </div>
    """, unsafe_allow_html=True)


# ─── Scan Progress ────────────────────────────────────────────────────────────

SCAN_STAGES = [
    (0.10, "🔄 Initialising engine…"),
    (0.30, "📦 Loading detection model…"),
    (0.55, "🖼️  Pre-processing image…"),
    (0.75, "🧠 Running AI detection…"),
    (0.90, "🔍 Analysing metadata…"),
    (1.00, "📋 Generating report…"),
]


def run_with_progress(image, scan_fn, meta_fn):
    """
    Orchestrate the scan with a live progress bar and stage labels.
    Returns (model_result, metadata_result).
    """
    bar      = st.progress(0.0)
    status   = st.empty()

    def _step(pct: float, label: str):
        bar.progress(pct)
        status.markdown(
            f"<p style='color:{T['cyan']}; font-family:JetBrains Mono,monospace; "
            f"font-size:0.85rem; margin:4px 0;'>{label}</p>",
            unsafe_allow_html=True,
        )

    _step(0.10, SCAN_STAGES[0][1])
    _step(0.30, SCAN_STAGES[1][1])

    model_result = scan_fn(image)   # heavy work — model load + inference

    _step(0.55, SCAN_STAGES[2][1])
    _step(0.75, SCAN_STAGES[3][1])

    meta_result = meta_fn(image)

    _step(0.90, SCAN_STAGES[4][1])
    _step(1.00, SCAN_STAGES[5][1])

    bar.empty()
    status.empty()

    return model_result, meta_result


# ─── Verdict Card ─────────────────────────────────────────────────────────────

def render_verdict_card(result: dict) -> None:
    """Render the main verdict card with animated confidence meter."""
    score   = result["ai_score"]
    colour  = result["verdict_colour"]
    verdict = result["verdict"]
    tier    = result["conf_label"]

    st.markdown(f"""
    <div class="cf-card" style="border-color:{colour}40; position:relative; overflow:hidden;">
        <!-- Glow strip -->
        <div style="position:absolute; top:0; left:0; right:0; height:3px;
                    background:linear-gradient(90deg,{colour},{T['cyan']});"></div>

        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
                <p class="cf-muted" style="margin:0; text-transform:uppercase; letter-spacing:.1em;">
                    Verdict
                </p>
                <h2 style="color:{colour} !important; margin:2px 0; font-size:2rem;
                           font-family:'Rajdhani',sans-serif; letter-spacing:.06em;">
                    {verdict}
                </h2>
            </div>
            <span style="background:{colour}22; color:{colour}; padding:5px 12px;
                         border-radius:20px; font-size:0.78rem; font-weight:700;
                         letter-spacing:.1em; font-family:'JetBrains Mono',monospace;">
                {tier}
            </span>
        </div>

        <!-- Confidence meter label -->
        <p class="cf-muted" style="margin:0 0 6px; font-size:0.82rem; text-transform:uppercase; letter-spacing:.08em;">
            Synthetic Probability
        </p>

        <!-- Track -->
        <div style="background:{T['bg']}; height:14px; border-radius:7px; overflow:hidden;">
            <div style="width:{score:.1f}%; height:100%;
                        background:linear-gradient(90deg,{colour}99,{colour});
                        border-radius:7px; transition:width 1s ease;"></div>
        </div>

        <!-- Score row -->
        <div style="display:flex; justify-content:space-between; margin-top:8px;">
            <span class="cf-mono">AI: {score:.2f}%</span>
            <span class="cf-mono">Real: {result['real_score']:.2f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # High-risk banner
    if score > 90:
        st.markdown(
            f"<div style='background:rgba(235,87,87,0.08); border:1px solid {T['danger']}40; "
            f"border-radius:8px; padding:10px 14px; margin-top:-6px; font-size:0.88rem;'>"
            f"🚩 <b style='color:{T['danger']};'>High Risk:</b> Strong synthetic-generation "
            f"signatures detected in pixel distribution.</div>",
            unsafe_allow_html=True,
        )

    # All-class probability breakdown
    with st.expander("📊 Full Probability Breakdown"):
        for label, pct in result["all_scores"].items():
            bar_w   = f"{pct:.1f}%"
            bar_col = T['danger'] if "artif" in label.lower() or "fake" in label.lower() else T['success']
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                    <span class="cf-mono" style="color:{T['text']};">{label}</span>
                    <span class="cf-mono">{pct:.2f}%</span>
                </div>
                <div style="background:{T['bg']}; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:{bar_w}; height:100%; background:{bar_col}; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Ensemble model comparison (if available)
    if result.get("has_secondary"):
        render_ensemble_comparison(result)


# ─── Ensemble Model Comparison ────────────────────────────────────────────────

def render_ensemble_comparison(result: dict) -> None:
    """
    Render side-by-side model predictions and agreement indicator.
    Shows each model's AI/Real scores and agreement status.
    """
    models = result.get("models", [])
    if len(models) < 2:
        return

    st.markdown("---")
    st.markdown(
        f"<h4 style='color:{T['cyan']}; font-family:Rajdhani,sans-serif; "
        f"letter-spacing:.06em; margin:0 0 12px;'>⚖️ Ensemble Model Comparison</h4>",
        unsafe_allow_html=True,
    )

    # Agreement indicator
    agreement = result.get("agreement", True)
    agreement_colour = T['success'] if agreement else T['warning']
    agreement_icon = "✅" if agreement else "⚠️"
    agreement_text = "Models agree" if agreement else "Models disagree"

    st.markdown(f"""
    <div style="background:{agreement_colour}15; border:1px solid {agreement_colour}40;
                border-radius:8px; padding:10px 14px; margin-bottom:14px;">
        <p style="color:{agreement_colour}; font-weight:700; margin:0; font-size:0.88rem;">
            {agreement_icon} {agreement_text} on verdict
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Side-by-side model cards
    cols = st.columns(2, gap="small")

    for idx, model in enumerate(models):
        with cols[idx]:
            model_name = model["name"].split(" (")[0]  # Extract just "Primary" or "Secondary"
            ai_pct = model["ai_score"]
            real_pct = model["real_score"]

            # Determine card border colour based on verdict
            is_fake = ai_pct > 50.0
            card_colour = T['danger'] if is_fake else T['success']

            st.markdown(f"""
            <div class="cf-card" style="border-color:{card_colour}40; border-width:2px;">
                <p class="cf-muted" style="margin:0 0 6px; font-size:0.75rem; text-transform:uppercase; letter-spacing:.08em;">
                    {model_name} Model
                </p>

                <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:10px;">
                    <span style="font-size:1.4rem; font-weight:700; color:{card_colour};
                                 font-family:'Rajdhani',sans-serif;">
                        {ai_pct:.1f}%
                    </span>
                    <span class="cf-mono" style="font-size:0.75rem; color:{T['muted']};">
                        AI / {real_pct:.1f}% Real
                    </span>
                </div>

                <!-- Mini progress bar -->
                <div style="background:{T['bg']}; height:6px; border-radius:3px; overflow:hidden; margin-bottom:8px;">
                    <div style="width:{ai_pct:.1f}%; height:100%; background:{card_colour}; border-radius:3px;"></div>
                </div>

                <p style="margin:0; color:{T['muted']}; font-size:0.80rem; font-family:'JetBrains Mono',monospace;">
                    Verdict: <span style="color:{card_colour}; font-weight:600;">
                        {'DEEPFAKE' if is_fake else 'AUTHENTIC'}
                    </span>
                </p>
            </div>
            """, unsafe_allow_html=True)


# ─── Explainability Panel ─────────────────────────────────────────────────────

def render_explainability(result: dict) -> None:
    """Render the explainability section showing why the model made its prediction."""
    st.markdown(
        f"<h4 style='color:{T['cyan']}; font-family:Rajdhani,sans-serif; "
        f"letter-spacing:.06em; margin:18px 0 10px;'>🧩 Why This Prediction?</h4>",
        unsafe_allow_html=True,
    )

    for item in result.get("explanation", []):
        st.markdown(f"""
        <div style="background:{T['bg']}; border-left:3px solid {T['accent']};
                    padding:12px 16px; margin-bottom:10px; border-radius:0 8px 8px 0;">
            <p style="margin:0 0 4px; font-weight:600; color:{T['text']}; font-size:0.9rem;">
                {item['icon']} {item['heading']}
            </p>
            <p style="margin:0; color:{T['muted']}; font-size:0.84rem; line-height:1.55;">
                {item['body']}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        f"<p style='color:{T['muted']}; font-size:0.78rem; margin-top:4px;'>"
        f"⚠️ <i>AI detection is probabilistic. Always corroborate with metadata and reverse-image analysis.</i>"
        f"</p>",
        unsafe_allow_html=True,
    )


# ─── Metadata Panel ───────────────────────────────────────────────────────────

_SEVERITY_CONFIG = {
    "critical": ("#EB5757", "🚨"),
    "warning":  ("#F2994A", "⚠️"),
    "info":     ("#56CCF2", "ℹ️"),
}


def render_metadata_panel(meta: dict) -> None:
    """Render the structured metadata analysis section."""
    st.markdown(
        f"<h4 style='color:{T['cyan']}; font-family:Rajdhani,sans-serif; "
        f"letter-spacing:.06em; margin:18px 0 10px;'>🛠️ Metadata Forensics</h4>",
        unsafe_allow_html=True,
    )

    # Summary badge
    st.markdown(
        f"<p style='color:{T['muted']}; font-size:0.88rem; margin-bottom:12px;'>"
        f"{meta['summary']}</p>",
        unsafe_allow_html=True,
    )

    # Anomaly list
    anomalies = meta.get("anomalies", [])
    if anomalies:
        for anom in anomalies:
            sev  = anom["severity"]
            col, icon = _SEVERITY_CONFIG.get(sev, (T['muted'], "•"))
            st.markdown(f"""
            <div style="background:{col}10; border:1px solid {col}30;
                        border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                <p style="margin:0 0 3px; font-size:0.88rem; font-weight:700; color:{col};">
                    {icon} {anom['label']}
                </p>
                <p style="margin:0; font-size:0.82rem; color:{T['muted']}; line-height:1.5;">
                    {anom['detail']}
                </p>
            </div>
            """, unsafe_allow_html=True)

    # Camera / Software / Timestamps in a clean grid
    has_structured = any([
        meta.get("camera_info"),
        meta.get("software_info"),
        meta.get("timestamp_info"),
    ])

    if has_structured:
        with st.expander("📋 Structured Metadata Fields"):
            sections = [
                ("📷 Camera", meta.get("camera_info", {})),
                ("💾 Software", meta.get("software_info", {})),
                ("🕐 Timestamps", meta.get("timestamp_info", {})),
            ]
            for title, data in sections:
                if data:
                    st.markdown(
                        f"<p style='color:{T['cyan']}; font-size:0.85rem; "
                        f"font-weight:600; margin:8px 0 4px;'>{title}</p>",
                        unsafe_allow_html=True,
                    )
                    for k, v in data.items():
                        st.markdown(
                            f"<div style='display:flex; gap:8px; margin-bottom:3px;'>"
                            f"<span class='cf-muted' style='min-width:160px;'>{k}</span>"
                            f"<span class='cf-mono' style='color:{T['text']};'>{v}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    # Full raw EXIF dump
    raw = meta.get("raw", {})
    if raw:
        with st.expander(f"🗄️ Raw EXIF Dump ({len(raw)} fields)"):
            for k, v in raw.items():
                st.markdown(
                    f"<div style='display:flex; gap:8px; margin-bottom:2px; "
                    f"border-bottom:1px solid {T['border']}; padding-bottom:2px;'>"
                    f"<span class='cf-muted' style='min-width:180px; flex-shrink:0;'>{k}</span>"
                    f"<span class='cf-mono' style='word-break:break-all; color:{T['text']};'>{v[:120]}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ─── Forensic Tools Bar ───────────────────────────────────────────────────────

def render_forensic_tools(filename: str) -> None:
    """Render external investigation shortcut buttons."""
    st.markdown("---")
    st.markdown(
        f"<h4 style='color:{T['cyan']}; font-family:Rajdhani,sans-serif; "
        f"letter-spacing:.06em; margin:0 0 10px;'>🔗 External Investigation Tools</h4>",
        unsafe_allow_html=True,
    )
    query = urllib.parse.quote(f'"{filename}"')

    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("📂 Filename Search", f"https://www.google.com/search?q={query}", use_container_width=True)
    with c2:
        st.link_button("🔍 Google Lens", "https://lens.google.com/upload", use_container_width=True)
    with c3:
        st.link_button("🌐 TinEye", "https://tineye.com/", use_container_width=True)


# ─── Reset Button ─────────────────────────────────────────────────────────────

def render_reset_button() -> None:
    """Render the 'Scan another image' reset button."""
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔁 Scan Another Image"):
        for key in ["scan_result", "scan_meta", "scan_filename"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# ─── Idle Placeholder ─────────────────────────────────────────────────────────

def render_idle_placeholder() -> None:
    """Render the waiting state on the right column."""
    st.markdown(f"""
    <div style="text-align:center; padding:60px 20px; color:{T['muted']};">
        <div style="font-size:3.5rem; margin-bottom:16px;">🔬</div>
        <h3 style="color:{T['muted']} !important; font-family:'Rajdhani',sans-serif;
                   font-weight:500; letter-spacing:.05em; margin:0 0 8px;">
            System Ready
        </h3>
        <p style="font-size:0.88rem; line-height:1.6; max-width:260px; margin:0 auto;">
            Upload an image on the left, then click
            <span style='color:{T['cyan']};'><b>Run Scan</b></span>
            to begin forensic analysis.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─── Error Card ───────────────────────────────────────────────────────────────

def render_error(message: str) -> None:
    """Display a styled error card."""
    st.markdown(f"""
    <div style="background:rgba(235,87,87,0.08); border:1px solid {T['danger']}60;
                border-radius:12px; padding:20px 24px; margin-top:10px;">
        <p style="color:{T['danger']}; font-weight:700; margin:0 0 6px;">⛔ Analysis Failed</p>
        <p style="color:{T['muted']}; font-size:0.88rem; margin:0;">{message}</p>
    </div>
    """, unsafe_allow_html=True)
